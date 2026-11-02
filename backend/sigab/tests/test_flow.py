import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connection, connections, transaction

from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    Item,
    Movement,
    MovementEvent,
    Organization,
    Person,
    Role,
    Unit,
)
from sigab.permissions import MOVEMENT_CHECKOUT, MOVEMENT_RETURN, VIEW_ITEM
from sigab.services import (
    CommandContext,
    ConflictError,
    checkout_item,
    return_item,
    set_item_condition,
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
    assert AuditEvent.objects.filter(organization=account.organization).count() == 4


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
    reason = "Cano danificado" if condition == Item.Condition.UNFIT else ""
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
        reason=reason,
        idempotency_key=key,
        confirmed=True,
    )
    repeated, repeated_created = return_item(
        world["ctx"],
        item_id=world["item"].id,
        condition=condition,
        reason=reason,
        idempotency_key=key,
        confirmed=True,
    )
    world["item"].refresh_from_db()
    assert created and not repeated_created and first.id == repeated.id
    assert world["item"].availability == expected and world["item"].current_holder is None
    assert world["item"].condition_reason == reason and first.condition_reason == reason
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
@pytest.mark.parametrize("model", [Movement, MovementEvent, AuditEvent])
def test_bulk_update_and_delete_are_blocked(world, model):
    with pytest.raises(ValidationError):
        model.objects.filter(organization=world["org"]).update(organization=world["org"])
    with pytest.raises(ValidationError):
        model.objects.filter(organization=world["org"]).delete()
    assert model.objects.filter(organization=world["org"]).exists()


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


def _checkout(world, item=None):
    return checkout_item(
        world["ctx"],
        item_id=(item or world["item"]).id,
        recipient_id=world["person"].id,
        idempotency_key=uuid.uuid4(),
        confirmed=True,
    )


def _set_condition(world, condition, reason="Conferência sintética", ctx=None, key=None):
    return set_item_condition(
        ctx or world["ctx"],
        item_id=world["item"].id,
        condition=condition,
        reason=reason,
        idempotency_key=key or uuid.uuid4(),
        confirmed=True,
    )


@pytest.mark.django_db
def test_checkout_rejects_inactive_item(world):
    Item.objects.filter(pk=world["item"].pk).update(
        administrative_status=Item.AdministrativeStatus.INACTIVE
    )
    with pytest.raises(ConflictError):
        _checkout(world)
    assert not Movement.objects.filter(movement_type=Movement.Type.CHECKOUT).exists()


@pytest.mark.django_db
def test_unfit_return_requires_reason(world):
    _checkout(world)
    with pytest.raises(ValidationError):
        return_item(
            world["ctx"],
            item_id=world["item"].id,
            condition=Item.Condition.UNFIT,
            reason="  ",
            idempotency_key=uuid.uuid4(),
            confirmed=True,
        )
    world["item"].refresh_from_db()
    assert world["item"].availability == Item.Availability.IN_CUSTODY


@pytest.mark.django_db
def test_unfit_item_without_reason_is_rejected_by_database(world):
    with pytest.raises(IntegrityError), transaction.atomic():
        Item.objects.filter(pk=world["item"].pk).update(condition=Item.Condition.UNFIT)


@pytest.mark.django_db
def test_unfit_item_can_be_released_and_checked_out_again(world):
    unfit, created = _set_condition(world, Item.Condition.UNFIT, "Aguardando manutenção")
    world["item"].refresh_from_db()
    assert created and unfit.movement_type == Movement.Type.CONDITION_CHANGE
    assert world["item"].availability == Item.Availability.UNAVAILABLE
    assert world["item"].condition_reason == "Aguardando manutenção"
    with pytest.raises(ConflictError):
        _checkout(world)

    key = uuid.uuid4()
    released, created = _set_condition(world, Item.Condition.FIT, "Inspeção 42", key=key)
    repeated, repeated_created = _set_condition(world, Item.Condition.FIT, "Inspeção 42", key=key)
    world["item"].refresh_from_db()
    assert created and not repeated_created and released.id == repeated.id
    assert world["item"].condition == Item.Condition.FIT
    assert world["item"].condition_reason == ""
    assert world["item"].availability == Item.Availability.AVAILABLE
    _checkout(world)

    events = list(world["item"].events.values_list("event_type", "metadata"))
    assert events[1:3] == [
        (
            "item.condition_changed",
            {
                "previous_condition": "fit",
                "condition": "unfit",
                "schema": "item.condition_changed.v1",
            },
        ),
        (
            "item.condition_changed",
            {
                "previous_condition": "unfit",
                "condition": "fit",
                "schema": "item.condition_changed.v1",
            },
        ),
    ]
    audit = AuditEvent.objects.get(action="item.condition_change", object_id=str(released.id))
    assert audit.reason == "Inspeção 42"
    assert audit.changes["condition"] == {"from": "unfit", "to": "fit"}


@pytest.mark.django_db
def test_returned_unfit_item_can_be_released(world):
    _checkout(world)
    return_item(
        world["ctx"],
        item_id=world["item"].id,
        condition=Item.Condition.UNFIT,
        reason="Gatilho travando",
        idempotency_key=uuid.uuid4(),
        confirmed=True,
    )
    _set_condition(world, Item.Condition.FIT, "Reparo concluído")
    world["item"].refresh_from_db()
    assert world["item"].availability == Item.Availability.AVAILABLE


@pytest.mark.django_db
@pytest.mark.parametrize(
    "condition,reason",
    [(Item.Condition.UNFIT, ""), (Item.Condition.FIT, " "), ("broken", "Motivo")],
)
def test_condition_change_validates_input(world, condition, reason):
    if condition == Item.Condition.FIT:
        _set_condition(world, Item.Condition.UNFIT)
    with pytest.raises(ValidationError):
        _set_condition(world, condition, reason)


@pytest.mark.django_db
def test_condition_change_requires_confirmation(world):
    with pytest.raises(ValidationError):
        set_item_condition(
            world["ctx"],
            item_id=world["item"].id,
            condition=Item.Condition.UNFIT,
            reason="Motivo",
            idempotency_key=uuid.uuid4(),
            confirmed=False,
        )


@pytest.mark.django_db
def test_condition_change_requires_permission(world):
    account = Account.objects.create_user(
        username="so-saida", password="Senha-forte-123", organization=world["org"]
    )
    role = Role.objects.create(
        organization=world["org"],
        name="Só saída",
        permissions=[MOVEMENT_CHECKOUT, MOVEMENT_RETURN, VIEW_ITEM],
    )
    Grant.objects.create(
        organization=world["org"],
        account=account,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
        granted_by=world["account"],
    )
    ctx = CommandContext(account, world["org"], "denied")
    with pytest.raises(PermissionDenied):
        _set_condition(world, Item.Condition.UNFIT, ctx=ctx)


@pytest.mark.django_db
def test_condition_change_hides_cross_tenant_item(world):
    other = Organization.objects.create(name="B")
    other_account = Account.objects.create_user(
        username="outro", password="Senha-forte-123", organization=other
    )
    ctx = CommandContext(other_account, other, "cross")
    with pytest.raises(ValidationError, match="Item inválido"):
        _set_condition(world, Item.Condition.UNFIT, ctx=ctx)


@pytest.mark.django_db
def test_condition_change_rejects_item_in_custody_inactive_or_same_condition(world):
    with pytest.raises(ConflictError):
        _set_condition(world, Item.Condition.FIT)
    _checkout(world)
    with pytest.raises(ConflictError):
        _set_condition(world, Item.Condition.UNFIT)
    Item.objects.filter(pk=world["item"].pk).update(
        availability=Item.Availability.AVAILABLE,
        current_holder=None,
        administrative_status=Item.AdministrativeStatus.INACTIVE,
    )
    with pytest.raises(ConflictError):
        _set_condition(world, Item.Condition.UNFIT)


@pytest.mark.django_db
def test_condition_change_http_flow(client, world):
    client.force_login(world["account"])
    url = f"/itens/{world['item'].id}/condicao/"
    assert b"Declarar item inapto" in client.get(url).content
    response = client.post(
        url,
        {"reason": "Mira desalinhada", "confirmed": "on", "idempotency_key": str(uuid.uuid4())},
    )
    assert response.status_code == 302
    world["item"].refresh_from_db()
    assert world["item"].condition == Item.Condition.UNFIT
    assert b"Mira desalinhada" in client.get(f"/itens/{world['item'].id}/").content
