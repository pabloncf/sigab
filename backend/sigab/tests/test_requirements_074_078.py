from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from sigab.domain.inventory import (
    close_inventory_session,
    open_inventory_session,
    record_inventory_count,
    update_divergence,
)
from sigab.domain.operations import StockRequest, checkout_basket, positive_quantity
from sigab.models import AuditEvent, InventoryDivergence, InventorySession, StockLedgerEntry
from sigab.services import ConflictError
from sigab.tests.test_requirements_063_070 import _enable_inventory_approval, _quantitative_stock

pytestmark = pytest.mark.django_db


def _divergence(world):
    _enable_inventory_approval(world)
    session = open_inventory_session(world["ctx"], unit_id=world["unit"].id)
    record_inventory_count(
        world["ctx"], session_id=session.id, item_id=world["item"].id, counted_state="missing"
    )
    return session, InventoryDivergence.objects.get(session=session)


@pytest.mark.parametrize("status", ["resolved", "dismissed"])
def test_recount_reopens_changed_finding_and_keeps_resolution_in_audit(world, status):
    session, divergence = _divergence(world)
    update_divergence(
        world["ctx"],
        divergence_id=divergence.id,
        status=status,
        assignee_id=world["account"].id,
        resolution="Primeira investigação",
    )
    record_inventory_count(
        world["ctx"], session_id=session.id, item_id=world["item"].id, counted_state="missing"
    )
    divergence.refresh_from_db()
    assert divergence.status == status
    record_inventory_count(
        world["ctx"], session_id=session.id, item_id=world["item"].id, counted_state="unavailable"
    )
    divergence.refresh_from_db()
    assert divergence.status == "open"
    assert divergence.resolution == "" and divergence.resolved_at is None
    before = AuditEvent.objects.get(action="inventory.divergence.reopened").changes["before"]
    assert before["resolution"] == "Primeira investigação"
    assert before["resolved_by"] == str(world["account"].id)
    with pytest.raises(ConflictError):
        close_inventory_session(world["ctx"], session_id=session.id)


def test_matching_recount_preserves_occurrence_and_records_justification(world):
    session, divergence = _divergence(world)
    record_inventory_count(
        world["ctx"], session_id=session.id, item_id=world["item"].id, counted_state="available"
    )
    divergence.refresh_from_db()
    assert divergence.status == "dismissed"
    assert divergence.assignee == world["account"]
    assert AuditEvent.objects.filter(action="inventory.divergence.recount_matched").exists()
    assert close_inventory_session(world["ctx"], session_id=session.id).status == "closed"


@pytest.mark.parametrize("status", ["investigating", "resolved", "dismissed"])
def test_investigation_and_resolution_require_assignee(world, status):
    _, divergence = _divergence(world)
    with pytest.raises(ValidationError, match="responsável"):
        update_divergence(
            world["ctx"], divergence_id=divergence.id, status=status, resolution="Conferido"
        )


def test_open_inventory_is_unique_even_outside_service(world):
    session = open_inventory_session(world["ctx"], unit_id=world["unit"].id)
    with pytest.raises(ConflictError):
        open_inventory_session(world["ctx"], unit_id=world["unit"].id)
    with pytest.raises(IntegrityError), transaction.atomic():
        InventorySession.objects.create(
            organization=world["org"],
            unit=world["unit"],
            opened_by=world["account"],
            opened_at=timezone.now(),
            reference_at=timezone.now(),
        )
    assert InventorySession.objects.get().id == session.id


def test_basket_replays_after_due_date_and_checks_permission(world):
    kind, balance = _quantitative_stock(world, "100")
    due_at = timezone.now() + timedelta(hours=1)
    kwargs = dict(
        recipient_id=world["person"].id,
        item_ids=[],
        stock=[StockRequest(kind.id, world["unit"].id, world["location"].id, Decimal("50"))],
        idempotency_key=uuid4(),
        custody_mode="fixed_term",
        due_at=due_at,
        confirmed=True,
    )
    batch, _ = checkout_basket(world["ctx"], **kwargs)
    with patch("sigab.domain.operations.timezone.now", return_value=due_at + timedelta(hours=1)):
        replay, created = checkout_basket(world["ctx"], **kwargs)
    assert not created and replay.id == batch.id
    balance.refresh_from_db()
    assert balance.quantity == 50
    assert StockLedgerEntry.objects.filter(loan__batch=batch).count() == 1
    world["account"].grants.update(is_active=False)
    with pytest.raises(PermissionDenied):
        checkout_basket(world["ctx"], **kwargs)


def test_quantitative_api_journey_and_scope(client, world):
    _enable_inventory_approval(world)
    kind, balance = _quantitative_stock(world, "0")
    client.force_login(world["account"])
    assert client.get("/api/v1/session/").json()["data"]["permissions"]["can_use_stock"]
    options = client.get("/api/v1/stock/options/").json()["data"]
    assert options["units"][0]["locations"][0]["id"] == str(world["location"].id)
    assert options["units"][0]["can_receive"]
    entry = dict(
        equipment_type_id=str(kind.id),
        unit_id=str(world["unit"].id),
        storage_location_id=str(world["location"].id),
        quantity="100",
        reason="Aquisição",
        confirmed=True,
        idempotency_key=str(uuid4()),
    )
    for expected in [201, 200]:
        assert (
            client.post(
                "/api/v1/stock/positions/", entry, content_type="application/json"
            ).status_code
            == expected
        )
    basket = dict(
        recipient_id=str(world["person"].id),
        item_ids=[],
        stock=[
            {k: entry[k] for k in ("equipment_type_id", "unit_id", "storage_location_id")}
            | {"quantity": "50"}
        ],
        custody_mode="indefinite",
        confirmed=True,
        idempotency_key=str(uuid4()),
    )
    for expected in [201, 200]:
        assert (
            client.post(
                "/api/v1/service-batches/", basket, content_type="application/json"
            ).status_code
            == expected
        )
    loan = client.get("/api/v1/stock/loans/").json()["data"][0]
    assert loan["can_settle"] and loan["quantity"] == "50.000"
    path = f"/api/v1/stock/loans/{loan['id']}/settle/"
    for disposition, quantity, reason in [("return", "20", ""), ("consume", "10", "Treinamento")]:
        payload = dict(
            quantity=quantity,
            disposition=disposition,
            reason=reason,
            confirmed=True,
            idempotency_key=str(uuid4()),
        )
        for expected in [201, 200]:
            assert (
                client.post(path, payload, content_type="application/json").status_code == expected
            )
    assert client.get("/api/v1/stock/loans/").json()["data"][0]["quantity"] == "20.000"
    balance.refresh_from_db()
    assert balance.quantity == 70
    assert (
        client.post(
            path,
            dict(quantity="1", disposition="consume", confirmed=True, idempotency_key=str(uuid4())),
            content_type="application/json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            path,
            dict(quantity="21", disposition="return", confirmed=True, idempotency_key=str(uuid4())),
            content_type="application/json",
        ).status_code
        == 409
    )
    world["account"].grants.update(is_active=False)
    assert client.get("/api/v1/stock/options/").status_code == 403
    assert client.get("/api/v1/stock/loans/").status_code == 403
    assert client.post(path, payload, content_type="application/json").status_code == 403
    assert (
        client.post("/api/v1/stock/positions/", entry, content_type="application/json").status_code
        == 403
    )


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "0", "-1", "0.0001"])
def test_quantity_validation_rejects_nonfinite_and_invalid_values(value):
    with pytest.raises(ValidationError):
        positive_quantity(value)


def test_stock_workspace_filters_units_and_hides_mutations_from_readers(client, world):
    from sigab.models import StockBalance, StorageLocation, Unit

    _, balance = _quantitative_stock(world)
    other = Unit.objects.create(organization=world["org"], name="Fora do escopo", code="OUT")
    location = StorageLocation.objects.create(
        organization=world["org"], unit=other, name="Reserva fora", code="OUT"
    )
    foreign_balance = StockBalance.objects.create(
        organization=world["org"],
        equipment_type=balance.equipment_type,
        unit=other,
        storage_location=location,
        quantity=999,
    )
    grant = world["account"].grants.get()
    grant.scope_type = "unit"
    grant.unit = world["unit"]
    grant.save()
    grant.role.permissions = ["item.view"]
    grant.role.save()
    client.force_login(world["account"])
    options = client.get("/api/v1/stock/options/").json()["data"]
    assert [row["id"] for row in options["units"]] == [str(world["unit"].id)]
    assert options["units"][0]["can_receive"] is False
    positions = client.get("/api/v1/stock/positions/").json()["data"]
    assert [row["id"] for row in positions] == [str(balance.id)]
    assert str(foreign_balance.id) not in str(positions)
    assert (
        client.post(
            "/api/v1/stock/positions/",
            {
                "equipment_type_id": str(balance.equipment_type_id),
                "unit_id": str(world["unit"].id),
                "storage_location_id": str(world["location"].id),
                "quantity": "1",
                "reason": "Teste",
                "confirmed": True,
                "idempotency_key": str(uuid4()),
            },
            content_type="application/json",
        ).status_code
        == 403
    )


@pytest.mark.django_db(transaction=True)
def test_inventory_migration_refuses_duplicates_without_deleting_history(world):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    previous = [("sigab", "0010_personrestriction_restrictionevent_and_more")]
    current = [("sigab", "0012_single_tenant_installation")]
    duplicate = None
    try:
        session = open_inventory_session(world["ctx"], unit_id=world["unit"].id)
        executor.migrate(previous)
        duplicate = InventorySession.objects.create(
            organization=world["org"],
            unit=world["unit"],
            opened_by=world["account"],
            opened_at=timezone.now(),
            reference_at=timezone.now(),
        )
        with pytest.raises(RuntimeError, match="Reconcilie as sessões"):
            MigrationExecutor(connection).migrate(current)
        assert InventorySession.objects.filter(status="open").count() == 2
        assert session.counts.count() == 1
    finally:
        # Reconcile only this synthetic fixture and leave the test schema at the latest migration.
        if duplicate is not None:
            duplicate.status = "closed"
            duplicate.save()
        MigrationExecutor(connection).migrate(current)
