from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from sigab.domain.inventory import (
    close_inventory_session,
    open_inventory_session,
    record_inventory_count,
    update_divergence,
)
from sigab.domain.operations import (
    StockRequest,
    checkout_basket,
    reverse_stock_entry,
    settle_stock_loan,
)
from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    InventoryDivergence,
    Item,
    Membership,
    Person,
    ServiceBatch,
    StockBalance,
    StockLedgerEntry,
)


def _enable_inventory_approval(world):
    role = world["account"].grants.get().role
    role.permissions = [*role.permissions, "inventory.adjust.approve"]
    role.full_clean()
    role.save(update_fields=["permissions", "updated_at"])


def _quantitative_stock(world, quantity="50"):
    equipment_type = EquipmentType.objects.create(
        organization=world["org"],
        name="Munição de teste",
        classification=EquipmentType.Classification.QUANTITATIVE,
    )
    balance = StockBalance.objects.create(
        organization=world["org"],
        equipment_type=equipment_type,
        unit=world["unit"],
        storage_location=world["location"],
        quantity=Decimal(quantity),
    )
    return equipment_type, balance


@pytest.mark.django_db
def test_mixed_basket_is_atomic_idempotent_and_supports_partial_settlement(world):
    role = world["account"].grants.get().role
    role.permissions = [*role.permissions, "movement.reverse"]
    role.save(update_fields=["permissions", "updated_at"])
    equipment_type, balance = _quantitative_stock(world)
    key = uuid4()
    batch, created = checkout_basket(
        world["ctx"],
        recipient_id=world["person"].id,
        item_ids=[world["item"].id],
        stock=[
            StockRequest(
                equipment_type_id=equipment_type.id,
                unit_id=world["unit"].id,
                storage_location_id=world["location"].id,
                quantity=Decimal("12"),
            )
        ],
        idempotency_key=key,
        custody_mode=ServiceBatch.CustodyMode.INDEFINITE,
        due_at=None,
        confirmed=True,
    )
    assert created is True
    world["item"].refresh_from_db()
    balance.refresh_from_db()
    assert world["item"].current_holder == world["person"]
    assert balance.quantity == Decimal("38")
    loan = batch.stock_loans.get()
    assert loan.open_quantity == Decimal("12")

    replay, created = checkout_basket(
        world["ctx"],
        recipient_id=world["person"].id,
        item_ids=[world["item"].id],
        stock=[
            StockRequest(
                equipment_type_id=equipment_type.id,
                unit_id=world["unit"].id,
                storage_location_id=world["location"].id,
                quantity=Decimal("12"),
            )
        ],
        idempotency_key=key,
        custody_mode=ServiceBatch.CustodyMode.INDEFINITE,
        due_at=None,
        confirmed=True,
    )
    assert replay == batch
    assert created is False
    assert StockLedgerEntry.objects.filter(loan=loan).count() == 1

    entry, _ = settle_stock_loan(
        world["ctx"],
        loan_id=loan.id,
        quantity="5",
        disposition=StockLedgerEntry.Type.RETURN,
        idempotency_key=uuid4(),
        confirmed=True,
    )
    loan.refresh_from_db()
    balance.refresh_from_db()
    assert entry.quantity == Decimal("5")
    assert loan.open_quantity == Decimal("7")
    assert balance.quantity == Decimal("43")

    reversal, _ = reverse_stock_entry(
        world["ctx"],
        entry_id=entry.id,
        idempotency_key=uuid4(),
        reason="Devolução registrada por engano",
        confirmed=True,
    )
    loan.refresh_from_db()
    balance.refresh_from_db()
    assert reversal.balance_delta == Decimal("-5")
    assert loan.open_quantity == Decimal("12")
    assert balance.quantity == Decimal("38")

    with pytest.raises(ValidationError):
        settle_stock_loan(
            world["ctx"],
            loan_id=loan.id,
            quantity="13",
            disposition=StockLedgerEntry.Type.CONSUME,
            idempotency_key=uuid4(),
            confirmed=True,
            reason="Treinamento",
        )


@pytest.mark.django_db
def test_inventory_divergence_must_be_resolved_and_every_change_is_audited(world):
    _enable_inventory_approval(world)
    session = open_inventory_session(world["ctx"], unit_id=world["unit"].id)
    record_inventory_count(
        world["ctx"],
        session_id=session.id,
        item_id=world["item"].id,
        counted_state="missing",
    )
    divergence = InventoryDivergence.objects.get(session=session)
    assert divergence.expected_state == Item.Availability.AVAILABLE
    assert divergence.counted_state == "missing"

    with pytest.raises(ValidationError):
        update_divergence(
            world["ctx"],
            divergence_id=divergence.id,
            status=InventoryDivergence.Status.RESOLVED,
        )
    with pytest.raises(ValidationError):
        close_inventory_session(world["ctx"], session_id=session.id)

    update_divergence(
        world["ctx"],
        divergence_id=divergence.id,
        status=InventoryDivergence.Status.DISMISSED,
        assignee_id=world["account"].id,
        reason="Investigação concluída",
        resolution="Item confirmado em manutenção com ordem autorizada.",
    )
    closed = close_inventory_session(world["ctx"], session_id=session.id)
    assert closed.status == closed.Status.CLOSED
    assert AuditEvent.objects.filter(
        organization=world["org"], action="inventory.divergence.update"
    ).exists()


@pytest.mark.django_db
def test_self_service_never_accepts_another_person_identifier(client, world):
    world["account"].person = world["person"]
    world["account"].save(update_fields=["person"])
    other = Person.objects.create(organization=world["org"], name="Outra pessoa")
    Membership.objects.create(
        organization=world["org"],
        person=other,
        registration="MAT-2",
        main_unit=world["unit"],
    )
    second_item = Item.objects.create(
        organization=world["org"],
        equipment_type=world["type"],
        unit=world["unit"],
        storage_location=world["location"],
        serial_number="SYN-002",
        availability=Item.Availability.IN_CUSTODY,
        current_holder=other,
    )
    world["item"].availability = Item.Availability.IN_CUSTODY
    world["item"].current_holder = world["person"]
    world["item"].save(update_fields=["availability", "current_holder", "updated_at"])

    client.force_login(world["account"])
    response = client.get("/api/v1/me/possessions/")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["person"]["id"] == str(world["person"].id)
    identifiers = {entry.get("identifier") for entry in body["possessions"]}
    assert world["item"].display_identifier in identifiers
    assert second_item.display_identifier not in identifiers


@pytest.mark.django_db
def test_domain_import_surfaces_keep_public_contracts():
    from sigab.domain.catalog import incorporate_item
    from sigab.domain.identity import create_person
    from sigab.domain.movements import checkout_item

    assert callable(incorporate_item)
    assert callable(create_person)
    assert callable(checkout_item)


@pytest.mark.django_db
def test_operational_collections_require_explicit_scope(client, world):
    session = open_inventory_session(world["ctx"], unit_id=world["unit"].id)
    unprivileged = Account.objects.create_user(
        username="sem-escopo",
        password="Senha-forte-123",
        organization=world["org"],
    )
    client.force_login(unprivileged)
    assert client.get("/api/v1/stock/positions/").status_code == 403
    assert client.get(f"/api/v1/inventory/sessions/{session.id}/").status_code == 404
