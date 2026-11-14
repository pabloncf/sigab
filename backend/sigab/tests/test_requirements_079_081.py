"""SIGAB-079 (home page), SIGAB-080 (equipment module) and SIGAB-081 (split collection)."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.utils import timezone

from sigab.domain.operations import StockRequest, checkout_basket
from sigab.models import (
    EquipmentType,
    Item,
    StockBalance,
    StockLedgerEntry,
    StorageLocation,
    Unit,
)
from sigab.tests.test_requirements_063_070 import _enable_inventory_approval, _quantitative_stock

pytestmark = pytest.mark.django_db


def _basket(world, kind, quantity="30", *, items=True, due_at=None):
    return checkout_basket(
        world["ctx"],
        recipient_id=world["person"].id,
        item_ids=[world["item"].id] if items else [],
        stock=[StockRequest(kind.id, world["unit"].id, world["location"].id, Decimal(quantity))],
        idempotency_key=uuid4(),
        custody_mode="fixed_term" if due_at else "indefinite",
        due_at=due_at,
        confirmed=True,
    )


def _foreign_unit(world):
    """Another unit of the same installation, with its own item and stock position."""
    unit = Unit.objects.create(organization=world["org"], name="Unidade B", code="UB")
    location = StorageLocation.objects.create(
        organization=world["org"], unit=unit, name="Reserva B", code="RB"
    )
    item = Item.objects.create(
        organization=world["org"],
        equipment_type=world["type"],
        unit=unit,
        storage_location=location,
        serial_number="FORA-001",
    )
    return unit, location, item


def _restrict_to_unit(world, permissions=None):
    grant = world["account"].grants.get()
    grant.scope_type = "unit"
    grant.unit = world["unit"]
    grant.save()
    if permissions is not None:
        grant.role.permissions = permissions
        grant.role.save()


# SIGAB-079 — home page


def test_overview_aggregates_scope_pending_and_recent_counter_movements(client, world):
    kind, _ = _quantitative_stock(world, "100")
    _basket(world, kind, due_at=timezone.now() + timedelta(hours=1))
    client.force_login(world["account"])

    data = client.get("/api/v1/overview/").json()["data"]

    assert data["individual"]["totals"] == {
        "available": 0,
        "in_custody": 1,
        "unavailable": 0,
        "total": 1,
    }
    assert data["individual"]["by_type"][0]["equipment_type"] == world["type"].name
    assert data["quantitative"] == [
        {
            "equipment_type_id": str(kind.id),
            "equipment_type": kind.name,
            "reserve": "70.000",
            "in_custody": "30.000",
            "total": "100.000",
        }
    ]
    assert data["pending"] == {
        "individual_in_custody": 1,
        "quantitative_open": 1,
        "quantitative_overdue": 0,
    }
    kinds = {row["kind"] for row in data["recent"]}
    assert kinds == {"individual", "quantitative"}
    for row in data["recent"]:
        assert row["type"] == "checkout"
        assert row["operator"] == world["account"].username
        assert row["recipient"] == str(world["person"])


def test_overview_respects_unit_scope_and_denies_without_item_view(client, world):
    kind, _ = _quantitative_stock(world, "10")
    unit, location, foreign_item = _foreign_unit(world)
    StockBalance.objects.create(
        organization=world["org"],
        equipment_type=kind,
        unit=unit,
        storage_location=location,
        quantity=Decimal("999"),
    )
    _restrict_to_unit(world)
    client.force_login(world["account"])

    data = client.get("/api/v1/overview/").json()["data"]

    assert data["individual"]["totals"]["total"] == 1
    assert data["quantitative"][0]["total"] == "10.000"
    assert "999" not in str(data) and foreign_item.serial_number not in str(data)

    _restrict_to_unit(world, permissions=["movement.checkout"])
    assert client.get("/api/v1/overview/").status_code == 403


def test_overview_does_not_count_inactive_items(client, world):
    Item.objects.filter(pk=world["item"].pk).update(
        administrative_status=Item.AdministrativeStatus.INACTIVE
    )
    client.force_login(world["account"])
    assert client.get("/api/v1/overview/").json()["data"]["individual"]["totals"]["total"] == 0


# SIGAB-080 — equipment module


def test_type_list_reports_scoped_counts_by_classification(client, world):
    kind, _ = _quantitative_stock(world, "40")
    _foreign_unit(world)
    _restrict_to_unit(world, permissions=["item.view", "item.create"])
    client.force_login(world["account"])

    rows = {row["name"]: row for row in client.get("/api/v1/equipment-types/").json()["data"]}

    assert rows[world["type"].name]["item_count"] == 1
    assert rows[world["type"].name]["stock_quantity"] is None
    assert rows[kind.name]["item_count"] is None
    assert rows[kind.name]["stock_quantity"] == "40.000"
    # The API keeps the internal classification values; only the interface relabels them.
    assert rows[kind.name]["classification"] == "quantitative"


def test_type_list_hides_counts_without_item_view_and_allows_stock_receivers(client, world):
    _quantitative_stock(world, "40")
    _restrict_to_unit(world, permissions=["inventory.adjust.approve"])
    client.force_login(world["account"])

    session = client.get("/api/v1/session/").json()["data"]["permissions"]
    assert session["can_receive_stock"] is True
    assert session["can_create_item"] is False
    rows = client.get("/api/v1/equipment-types/").json()["data"]
    assert rows and all(row["item_count"] is None for row in rows)
    assert all(row["stock_quantity"] is None for row in rows)

    _restrict_to_unit(world, permissions=["movement.checkout"])
    assert (
        client.get("/api/v1/session/").json()["data"]["permissions"]["can_receive_stock"] is False
    )
    assert client.get("/api/v1/equipment-types/").status_code == 403


def test_item_and_stock_entry_refuse_wrong_classification_and_inactive_type(client, world):
    _enable_inventory_approval(world)
    role = world["account"].grants.get().role
    role.permissions = [*role.permissions, "item.create"]
    role.save()
    kind, _ = _quantitative_stock(world, "0")
    client.force_login(world["account"])
    place = {"unit_id": str(world["unit"].id), "storage_location_id": str(world["location"].id)}

    def incorporate(type_id, serial):
        return client.post(
            "/api/v1/items/",
            {"equipment_type_id": str(type_id), "serial_number": serial, "confirmed": True} | place,
            content_type="application/json",
        )

    def receive(type_id):
        return client.post(
            "/api/v1/stock/positions/",
            {
                "equipment_type_id": str(type_id),
                "quantity": "5",
                "reason": "Aquisição",
                "confirmed": True,
                "idempotency_key": str(uuid4()),
            }
            | place,
            content_type="application/json",
        )

    items_before = Item.objects.count()
    entries_before = StockLedgerEntry.objects.count()
    assert incorporate(kind.id, "SEM-REGISTRO").status_code in (400, 404)
    assert receive(world["type"].id).status_code in (400, 404)
    EquipmentType.objects.filter(pk=world["type"].pk).update(is_active=False)
    EquipmentType.objects.filter(pk=kind.pk).update(is_active=False)
    assert incorporate(world["type"].id, "TIPO-INATIVO").status_code in (400, 404)
    assert receive(kind.id).status_code in (400, 404)
    assert Item.objects.count() == items_before
    assert StockLedgerEntry.objects.count() == entries_before


# SIGAB-081 — collection split into with and without registration


def test_stock_summary_shows_reserve_custody_and_total_per_position(client, world):
    kind, _ = _quantitative_stock(world, "1500")
    _basket(world, kind, "300", items=False)
    client.force_login(world["account"])

    rows = client.get("/api/v1/stock/summary/").json()["data"]

    assert rows == [
        {
            "id": rows[0]["id"],
            "equipment_type": {"id": str(kind.id), "name": kind.name},
            "unit": {"id": str(world["unit"].id), "name": world["unit"].name},
            "storage_location": {"id": str(world["location"].id), "name": "Reserva"},
            "reserve": "1200.000",
            "in_custody": "300.000",
            "total": "1500.000",
        }
    ]
    assert client.get("/api/v1/stock/summary/?q=inexistente").json()["data"] == []
    # Individual items never appear as quantity.
    assert world["type"].name not in str(rows)
    # Totals reconcile with the home page.
    overview = client.get("/api/v1/overview/").json()["data"]["quantitative"][0]
    assert (overview["reserve"], overview["in_custody"]) == ("1200.000", "300.000")


def test_stock_summary_and_history_apply_unit_scope(client, world):
    kind, _ = _quantitative_stock(world, "10")
    _basket(world, kind, "4", items=False)
    unit, location, _ = _foreign_unit(world)
    foreign = StockBalance.objects.create(
        organization=world["org"],
        equipment_type=kind,
        unit=unit,
        storage_location=location,
        quantity=Decimal("999"),
    )
    _restrict_to_unit(world)
    client.force_login(world["account"])

    summary = client.get("/api/v1/stock/summary/").json()["data"]
    assert [row["id"] for row in summary] != [] and str(foreign.id) not in str(summary)
    assert client.get(f"/api/v1/stock/summary/?unit={unit.id}").json()["data"] == []

    history = client.get(f"/api/v1/stock/entries/?type={kind.id}").json()
    assert history["meta"]["count"] == 1
    entry = history["data"][0]
    assert entry["type"] == "checkout" and entry["quantity"] == "4.000"
    assert entry["operator"] == world["account"].username
    assert entry["recipient"] == str(world["person"])

    _restrict_to_unit(world, permissions=["movement.checkout"])
    assert client.get("/api/v1/stock/summary/").status_code == 403
    assert client.get("/api/v1/stock/entries/").status_code == 403


def test_individual_list_never_contains_material_without_registration(client, world):
    _quantitative_stock(world, "10")
    client.force_login(world["account"])
    rows = client.get("/api/v1/items/").json()["data"]
    assert [row["identifier"] for row in rows] == [world["item"].serial_number]
