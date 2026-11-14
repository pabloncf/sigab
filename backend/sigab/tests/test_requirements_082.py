"""SIGAB-082: counter return by person and movement register."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from sigab.domain.operations import (
    ItemReturnLine,
    StockRequest,
    StockReturnLine,
    checkout_basket,
    return_basket,
)
from sigab.models import (
    AuditEvent,
    Item,
    Movement,
    Person,
    ReturnBatch,
    StockBalance,
    StockLedgerEntry,
    StockLoan,
    StorageLocation,
    Unit,
)
from sigab.services import ConflictError
from sigab.tests.test_requirements_063_070 import _quantitative_stock

pytestmark = pytest.mark.django_db


def _second_item(world, serial="SYN-002"):
    item = Item.objects.create(
        organization=world["org"],
        equipment_type=world["type"],
        unit=world["unit"],
        storage_location=world["location"],
        serial_number=serial,
    )
    return item


def _deliver(world, items, stock_quantity="50"):
    kind, balance = _quantitative_stock(world, "100")
    batch, _ = checkout_basket(
        world["ctx"],
        recipient_id=world["person"].id,
        item_ids=[item.id for item in items],
        stock=[
            StockRequest(kind.id, world["unit"].id, world["location"].id, Decimal(stock_quantity))
        ],
        idempotency_key=uuid4(),
        custody_mode="indefinite",
        due_at=None,
        confirmed=True,
    )
    return batch, StockLoan.objects.get(batch=batch), balance


def test_return_basket_is_atomic_marks_condition_and_replays(world):
    second = _second_item(world)
    _, loan, balance = _deliver(world, [world["item"], second])
    key = uuid4()
    kwargs = dict(
        person_id=world["person"].id,
        items=[
            ItemReturnLine(world["item"].id, "fit"),
            ItemReturnLine(second.id, "unfit", "Cano danificado"),
        ],
        stock=[StockReturnLine(loan.id, Decimal("20"))],
        idempotency_key=key,
        confirmed=True,
    )

    batch, created = return_basket(world["ctx"], **kwargs)
    replay, replayed = return_basket(world["ctx"], **kwargs)

    assert created and not replayed and replay.id == batch.id
    assert batch.receipt_code.startswith("DV-")
    first, unfit = Item.objects.get(pk=world["item"].pk), Item.objects.get(pk=second.pk)
    assert first.availability == "available" and first.current_holder is None
    assert unfit.availability == "unavailable" and unfit.condition_reason == "Cano danificado"
    loan.refresh_from_db()
    balance.refresh_from_db()
    assert loan.open_quantity == 30 and balance.quantity == 70
    assert Movement.objects.filter(movement_type="return").count() == 2
    assert batch.items.count() == 2 and batch.stock_lines.count() == 1
    assert AuditEvent.objects.filter(action="return_batch.confirmed").count() == 1

    changed = {**kwargs, "stock": [StockReturnLine(loan.id, Decimal("10"))]}
    with pytest.raises(ConflictError):
        return_basket(world["ctx"], **changed)


def test_return_basket_rolls_back_when_any_line_is_invalid(world):
    second = _second_item(world)
    _, loan, _ = _deliver(world, [world["item"]])
    with pytest.raises(ConflictError):
        return_basket(
            world["ctx"],
            person_id=world["person"].id,
            items=[ItemReturnLine(world["item"].id, "fit"), ItemReturnLine(second.id, "fit")],
            stock=[StockReturnLine(loan.id, Decimal("5"))],
            idempotency_key=uuid4(),
            confirmed=True,
        )
    assert Item.objects.get(pk=world["item"].pk).availability == "in_custody"
    loan.refresh_from_db()
    assert loan.open_quantity == 50
    assert not ReturnBatch.objects.exists()
    assert not StockLedgerEntry.objects.filter(entry_type="return").exists()


def test_return_basket_validates_confirmation_condition_holder_and_quantity(world):
    _, loan, _ = _deliver(world, [world["item"]])
    other = Person.objects.create(organization=world["org"], name="Outra pessoa")
    base = dict(person_id=world["person"].id, idempotency_key=uuid4(), confirmed=True)
    with pytest.raises(ValidationError):
        return_basket(world["ctx"], **{**base, "confirmed": False}, items=[], stock=[])
    with pytest.raises(ValidationError):
        return_basket(world["ctx"], **base, items=[], stock=[])
    with pytest.raises(ValidationError):
        return_basket(
            world["ctx"], **base, items=[ItemReturnLine(world["item"].id, "broken")], stock=[]
        )
    with pytest.raises(ValidationError, match="motivo|Motivo"):
        return_basket(
            world["ctx"], **base, items=[ItemReturnLine(world["item"].id, "unfit")], stock=[]
        )
    with pytest.raises(ConflictError):
        return_basket(
            world["ctx"],
            **{**base, "person_id": other.id},
            items=[ItemReturnLine(world["item"].id, "fit")],
            stock=[],
        )
    with pytest.raises(ConflictError):
        return_basket(
            world["ctx"], **base, items=[], stock=[StockReturnLine(loan.id, Decimal("51"))]
        )


def test_return_basket_accepts_inactive_person_but_requires_return_permission(world):
    _deliver(world, [world["item"]])
    Person.objects.filter(pk=world["person"].pk).update(is_active=False)
    role = world["account"].grants.get().role
    role.permissions = [code for code in role.permissions if code != "movement.return"]
    role.save()
    line = [ItemReturnLine(world["item"].id, "fit")]
    with pytest.raises(PermissionDenied):
        return_basket(
            world["ctx"],
            person_id=world["person"].id,
            items=line,
            stock=[],
            idempotency_key=uuid4(),
            confirmed=True,
        )
    role.permissions = [*role.permissions, "movement.return"]
    role.save()
    batch, created = return_basket(
        world["ctx"],
        person_id=world["person"].id,
        items=line,
        stock=[],
        idempotency_key=uuid4(),
        confirmed=True,
    )
    assert created and batch.person_id == world["person"].id


def test_return_api_options_and_register_with_filters(client, world):
    _, loan, _ = _deliver(world, [world["item"]])
    client.force_login(world["account"])

    options = client.get("/api/v1/return-batches/options/").json()["data"]
    assert options["people"] == [{"id": str(world["person"].id), "name": str(world["person"])}]
    detail = client.get(f"/api/v1/return-batches/options/?person={world['person'].id}").json()
    assert [row["id"] for row in detail["data"]["items"]] == [str(world["item"].id)]
    assert detail["data"]["stock"][0]["open_quantity"] == "50.000"

    body = {
        "person_id": str(world["person"].id),
        "items": [{"item_id": str(world["item"].id), "condition": "fit"}],
        "stock": [{"loan_id": str(loan.id), "quantity": "50"}],
        "idempotency_key": str(uuid4()),
        "confirmed": True,
    }
    for expected in (201, 200):
        response = client.post("/api/v1/return-batches/", body, content_type="application/json")
        assert response.status_code == expected
    receipt = response.json()["data"]["receipt_code"]
    assert response.json()["data"]["items"][0]["condition"] == "fit"

    register = client.get("/api/v1/movements/").json()
    assert register["meta"]["count"] == 4
    types = sorted((row["kind"], row["type"]) for row in register["data"])
    assert types == [
        ("individual", "checkout"),
        ("individual", "return"),
        ("quantitative", "checkout"),
        ("quantitative", "return"),
    ]
    for row in register["data"]:
        assert row["operator"] == world["account"].username
        assert row["recipient"] == str(world["person"])
        assert row["receipt_code"]
    returns = client.get("/api/v1/movements/?type=return").json()["data"]
    assert {row["receipt_code"] for row in returns} == {receipt}
    assert client.get(f"/api/v1/movements/?operator={uuid4()}").json()["meta"]["count"] == 0
    individual = client.get(
        f"/api/v1/movements/?kind=individual&equipment_type={world['type'].id}"
    ).json()
    assert individual["meta"]["count"] == 2
    assert client.get("/api/v1/movements/?type=invalid").status_code == 400
    paged = client.get("/api/v1/movements/?limit=1&offset=1").json()
    assert len(paged["data"]) == 1 and paged["meta"]["count"] == 4
    filters = client.get("/api/v1/movements/options/").json()["data"]
    assert filters["operators"] == [
        {"id": str(world["account"].id), "username": world["account"].username}
    ]
    assert (
        client.post(
            "/api/v1/return-batches/", body | {"confirmed": False}, content_type="application/json"
        ).status_code
        == 400
    )


def test_return_and_register_apply_unit_scope(client, world):
    _deliver(world, [world["item"]])
    unit = Unit.objects.create(organization=world["org"], name="Unidade B", code="UB")
    location = StorageLocation.objects.create(
        organization=world["org"], unit=unit, name="Reserva B", code="RB"
    )
    foreign = Item.objects.create(
        organization=world["org"],
        equipment_type=world["type"],
        unit=unit,
        storage_location=location,
        serial_number="FORA-001",
    )
    holder = Person.objects.create(organization=world["org"], name="Pessoa da unidade B")
    Item.objects.filter(pk=foreign.pk).update(availability="in_custody", current_holder=holder)
    grant = world["account"].grants.get()
    grant.scope_type, grant.unit = "unit", world["unit"]
    grant.save()
    client.force_login(world["account"])

    options = client.get("/api/v1/return-batches/options/").json()["data"]
    assert [row["id"] for row in options["people"]] == [str(world["person"].id)]
    detail = client.get(f"/api/v1/return-batches/options/?person={holder.id}").json()["data"]
    assert detail["items"] == [] and detail["stock"] == []
    response = client.post(
        "/api/v1/return-batches/",
        {
            "person_id": str(holder.id),
            "items": [{"item_id": str(foreign.id), "condition": "fit"}],
            "stock": [],
            "idempotency_key": str(uuid4()),
            "confirmed": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 403
    assert "FORA-001" not in str(client.get("/api/v1/movements/").json())

    grant.role.permissions = ["movement.checkout"]
    grant.role.save()
    assert client.get("/api/v1/return-batches/options/").status_code == 403
    assert client.get("/api/v1/movements/").status_code == 403
    assert client.get("/api/v1/movements/options/").status_code == 403


def test_home_recent_movements_carry_receipt_codes(client, world):
    _deliver(world, [world["item"]])
    client.force_login(world["account"])
    recent = client.get("/api/v1/overview/").json()["data"]["recent"]
    assert recent and all(row["receipt_code"].startswith("AT-") for row in recent)
    assert StockBalance.objects.get().quantity == 50
