import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connection, connections

from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    Item,
    Membership,
    Movement,
    Organization,
    Person,
    Role,
    StorageLocation,
    Unit,
)
from sigab.permissions import MOVE_ITEM, VIEW_ITEM
from sigab.services import (
    CommandContext,
    ConflictError,
    checkout_item,
    record_incorporation,
    return_item,
)


@pytest.mark.django_db
def test_controlled_bootstrap_creates_admin_grant_and_audit():
    call_command(
        "bootstrap_sigab",
        organization="Organização Bootstrap",
        username="admin-bootstrap",
        email="admin@example.invalid",
        password="Senha-forte-123",
        verbosity=0,
    )
    account = Account.objects.get(username="admin-bootstrap")
    assert account.is_staff and not account.is_superuser
    assert account.grants.filter(scope_type=Grant.Scope.ORGANIZATION).exists()
    assert AuditEvent.objects.filter(organization=account.organization).count() == 3


@pytest.mark.django_db
def test_controlled_account_creation_keeps_person_separate():
    org = Organization.objects.create(name="A")
    person = Person.objects.create(organization=org, name="Pessoa")
    call_command(
        "create_sigab_account",
        organization_id=str(org.id),
        person_id=str(person.id),
        username="pessoa-conta",
        email="pessoa@example.invalid",
        password="Senha-forte-123",
        verbosity=0,
    )
    account = Account.objects.get(username="pessoa-conta")
    assert account.person == person and account.organization == org
    assert AuditEvent.objects.filter(action="account.create.controlled_command").exists()


@pytest.fixture
def world(db):
    org = Organization.objects.create(name="Organização A")
    unit = Unit.objects.create(organization=org, name="Unidade A", code="UA")
    location = StorageLocation.objects.create(
        organization=org, unit=unit, name="Reserva", code="R1"
    )
    person = Person.objects.create(organization=org, name="Pessoa Sintética")
    Membership.objects.create(organization=org, person=person, registration="MAT-1", main_unit=unit)
    account = Account.objects.create_user(
        username="operador", password="Senha-forte-123", organization=org
    )
    role = Role.objects.create(
        organization=org, name="Operador", permissions=[MOVE_ITEM, VIEW_ITEM]
    )
    Grant.objects.create(
        organization=org,
        account=account,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
        granted_by=account,
    )
    equipment_type = EquipmentType.objects.create(
        organization=org,
        name="Equipamento sintético",
        classification=EquipmentType.Classification.INDIVIDUAL,
    )
    item = Item.objects.create(
        organization=org,
        equipment_type=equipment_type,
        unit=unit,
        storage_location=location,
        serial_number="SYN-001",
    )
    ctx = CommandContext(account, org, "test-correlation")
    record_incorporation(ctx, item)
    return {
        "org": org,
        "unit": unit,
        "location": location,
        "person": person,
        "account": account,
        "type": equipment_type,
        "item": item,
        "ctx": ctx,
    }


@pytest.mark.django_db
def test_person_can_exist_without_account():
    org = Organization.objects.create(name="A")
    person = Person.objects.create(organization=org, name="Sem conta")
    assert not Account.objects.filter(person=person).exists()


@pytest.mark.django_db
def test_suspended_account_cannot_login(client):
    account = Account.objects.create_user(username="suspenso", password="Senha-forte-123")
    account.is_active = False
    account.save()
    assert not client.login(username="suspenso", password="Senha-forte-123")


@pytest.mark.django_db
def test_cross_tenant_references_are_rejected(world):
    other = Organization.objects.create(name="B")
    other_unit = Unit.objects.create(organization=other, name="Outra", code="B")
    world["item"].unit = other_unit
    with pytest.raises(ValidationError):
        world["item"].full_clean()


@pytest.mark.django_db
def test_quantitative_type_is_rejected_for_individual_item(world):
    quantitative = EquipmentType.objects.create(
        organization=world["org"],
        name="Munição",
        classification=EquipmentType.Classification.QUANTITATIVE,
    )
    item = Item(
        organization=world["org"],
        equipment_type=quantitative,
        unit=world["unit"],
        storage_location=world["location"],
    )
    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.mark.django_db
def test_item_id_is_independent_from_serial(world):
    assert str(world["item"].id) != world["item"].serial_number


@pytest.mark.django_db
def test_checkout_requires_permission(world):
    unauthorized = Account.objects.create_user(
        username="sem-permissao", password="Senha-forte-123", organization=world["org"]
    )
    ctx = CommandContext(unauthorized, world["org"], "denied")
    with pytest.raises(PermissionDenied):
        checkout_item(
            ctx,
            item_id=world["item"].id,
            recipient_id=world["person"].id,
            idempotency_key=uuid.uuid4(),
            confirmed=True,
        )


@pytest.mark.django_db
def test_checkout_requires_confirmation(world):
    with pytest.raises(ValidationError):
        checkout_item(
            world["ctx"],
            item_id=world["item"].id,
            recipient_id=world["person"].id,
            idempotency_key=uuid.uuid4(),
            confirmed=False,
        )


@pytest.mark.django_db
def test_checkout_is_idempotent_and_prevents_second_checkout(world):
    key = uuid.uuid4()
    first, created = checkout_item(
        world["ctx"],
        item_id=world["item"].id,
        recipient_id=world["person"].id,
        idempotency_key=key,
        confirmed=True,
    )
    repeated, repeated_created = checkout_item(
        world["ctx"],
        item_id=world["item"].id,
        recipient_id=world["person"].id,
        idempotency_key=key,
        confirmed=True,
    )
    assert created is True and repeated_created is False and first.id == repeated.id
    with pytest.raises(ConflictError):
        checkout_item(
            world["ctx"],
            item_id=world["item"].id,
            recipient_id=world["person"].id,
            idempotency_key=uuid.uuid4(),
            confirmed=True,
        )
    assert (
        Movement.objects.filter(item=world["item"], movement_type=Movement.Type.CHECKOUT).count()
        == 1
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "condition,expected",
    [
        (Item.Condition.FIT, Item.Availability.AVAILABLE),
        (Item.Condition.UNFIT, Item.Availability.UNAVAILABLE),
    ],
)
def test_return_closes_custody_and_derives_availability(world, condition, expected):
    checkout_item(
        world["ctx"],
        item_id=world["item"].id,
        recipient_id=world["person"].id,
        idempotency_key=uuid.uuid4(),
        confirmed=True,
    )
    key = uuid.uuid4()
    first, created = return_item(
        world["ctx"],
        item_id=world["item"].id,
        condition=condition,
        idempotency_key=key,
        confirmed=True,
    )
    repeated, repeated_created = return_item(
        world["ctx"],
        item_id=world["item"].id,
        condition=condition,
        idempotency_key=key,
        confirmed=True,
    )
    world["item"].refresh_from_db()
    assert created and not repeated_created and first.id == repeated.id
    assert world["item"].availability == expected and world["item"].current_holder is None
    assert list(world["item"].events.values_list("event_type", flat=True)) == [
        "item.incorporated",
        "item.checked_out",
        "item.returned",
    ]


@pytest.mark.django_db
def test_events_are_immutable(world):
    event = world["item"].events.first()
    event.event_type = "tampered"
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    audit = AuditEvent.objects.first()
    with pytest.raises(ValidationError):
        audit.delete()
    movement = Movement.objects.first()
    with pytest.raises(ValidationError):
        movement.delete()


@pytest.mark.django_db
def test_tenant_dashboard_does_not_leak_items(client, world):
    other = Organization.objects.create(name="B")
    other_account = Account.objects.create_user(
        username="other", password="Senha-forte-123", organization=other
    )
    client.force_login(other_account)
    response = client.get("/")
    assert response.status_code == 200
    assert b"SYN-001" not in response.content


@pytest.mark.django_db
def test_direct_item_route_hides_cross_tenant_item(client, world):
    other = Organization.objects.create(name="B")
    other_account = Account.objects.create_user(
        username="other2", password="Senha-forte-123", organization=other
    )
    client.force_login(other_account)
    assert client.get(f"/itens/{world['item'].id}/").status_code == 404


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkout_accepts_exactly_one(world):
    if connection.vendor != "postgresql":
        pytest.skip("Concorrência transacional é validada no PostgreSQL do CI.")

    def attempt(key):
        close_old_connections()
        account = Account.objects.get(pk=world["account"].pk)
        org = Organization.objects.get(pk=world["org"].pk)
        ctx = CommandContext(account, org, f"concurrent-{key}")
        try:
            checkout_item(
                ctx,
                item_id=world["item"].id,
                recipient_id=world["person"].id,
                idempotency_key=key,
                confirmed=True,
            )
            return "accepted"
        except ConflictError:
            return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, [uuid.uuid4(), uuid.uuid4()]))
    assert sorted(outcomes) == ["accepted", "conflict"]
