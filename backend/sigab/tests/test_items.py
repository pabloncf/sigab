import json
import uuid

import pytest
from django.test import Client

from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    Item,
    Movement,
    MovementEvent,
    Person,
    Role,
    StorageLocation,
    Unit,
)
from sigab.permissions import ITEM_CREATE, ITEM_VIEW

PASSWORD = "Senha-forte-123"


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def creator(api_world):
    organization = api_world["organization"]
    other_unit = Unit.objects.create(organization=organization, name="Unidade B", code="U-B")
    other_location = StorageLocation.objects.create(
        organization=organization, unit=other_unit, name="Reserva B", code="R-B"
    )
    account = Account.objects.create_user(
        username="operador-unidade", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(
        organization=organization,
        name="Operador",
        permissions=[ITEM_CREATE, ITEM_VIEW],
        allowed_scopes=["unit"],
    )
    Grant.objects.create(
        organization=organization,
        account=account,
        role=role,
        scope_type="unit",
        unit=api_world["unit"],
    )
    client = Client()
    client.force_login(account)
    return {
        **api_world,
        "client": client,
        "creator": account,
        "other_unit": other_unit,
        "other_location": other_location,
        "payload": {
            "equipment_type_id": str(api_world["item"].equipment_type_id),
            "unit_id": str(api_world["unit"].id),
            "storage_location_id": str(api_world["item"].storage_location_id),
            "serial_number": "SER-NOVO",
            "confirmed": True,
        },
    }


# SIGAB-027: individual item


@pytest.mark.django_db
def test_incorporation_creates_item_with_derived_state_and_audit(creator):
    response = _post(creator["client"], "/api/v1/items/", creator["payload"])
    assert response.status_code == 201
    data = response.json()["data"]
    item = Item.objects.get(pk=data["id"])
    assert isinstance(item.pk, uuid.UUID)
    assert (item.availability, item.condition, item.administrative_status) == (
        "available",
        "fit",
        "active",
    )
    assert item.movements.get().movement_type == Movement.Type.INCORPORATION
    assert item.events.get().event_type == "item.incorporated"
    audit = AuditEvent.objects.get(action="item.incorporate", object_id=str(item.pk))
    assert audit.actor == creator["creator"]


@pytest.mark.django_db
def test_unfit_incorporation_requires_reason_and_starts_unavailable(creator):
    payload = {**creator["payload"], "condition": "unfit"}
    assert _post(creator["client"], "/api/v1/items/", payload).status_code == 400
    response = _post(
        creator["client"], "/api/v1/items/", {**payload, "condition_reason": "Sem carregador"}
    )
    assert response.status_code == 201
    assert response.json()["data"]["availability"] == "unavailable"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "change, field",
    [
        ({"serial_number": "API-001"}, "non_field_errors"),
        ({"serial_number": "", "asset_number": ""}, "non_field_errors"),
        ({"confirmed": False}, "confirmed"),
    ],
    ids=["duplicate-serial", "no-identifier", "no-confirmation"],
)
def test_incorporation_validations(creator, change, field):
    response = _post(creator["client"], "/api/v1/items/", {**creator["payload"], **change})
    assert response.status_code == 400
    assert field in response.json()["details"]


@pytest.mark.django_db
def test_incorporation_rejects_quantitative_type_and_foreign_location(creator):
    quantitative = EquipmentType.objects.create(
        organization=creator["organization"], name="Munição", classification="quantitative"
    )
    response = _post(
        creator["client"],
        "/api/v1/items/",
        {**creator["payload"], "equipment_type_id": str(quantitative.id)},
    )
    assert response.status_code == 400
    wrong_location = _post(
        creator["client"],
        "/api/v1/items/",
        {**creator["payload"], "storage_location_id": str(creator["other_location"].id)},
    )
    assert wrong_location.json()["details"] == {
        "storage_location_id": ["Local de guarda inválido para a unidade."]
    }


@pytest.mark.django_db
def test_unit_operator_cannot_incorporate_in_other_unit(creator):
    response = _post(
        creator["client"],
        "/api/v1/items/",
        {
            **creator["payload"],
            "unit_id": str(creator["other_unit"].id),
            "storage_location_id": str(creator["other_location"].id),
        },
    )
    assert response.status_code == 403
    assert not Item.objects.filter(unit=creator["other_unit"]).exists()


# SIGAB-028: detail and history


def _checkout(client, item, person):
    return _post(
        client,
        f"/api/v1/items/{item.id}/checkout/",
        {"recipient_id": str(person.id), "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    )


def _return(client, item, condition="fit", reason=""):
    return _post(
        client,
        f"/api/v1/items/{item.id}/return/",
        {
            "condition": condition,
            "reason": reason,
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": True,
        },
    )


def _replay(events):
    """Derive the item projection from confirmed facts only."""
    state = {"availability": "available", "condition": "fit", "holder": None}
    for event in events:
        movement = event["movement"]
        if event["type"] == "item.checked_out":
            state.update(availability="in_custody", holder=movement["recipient"]["id"])
        elif event["type"] == "item.returned":
            fit = movement["condition"] == "fit"
            state.update(
                availability="available" if fit else "unavailable",
                condition=movement["condition"],
                holder=None,
            )
        elif event["type"] == "item.condition_changed":
            fit = movement["condition"] == "fit"
            state.update(
                availability="available" if fit else "unavailable", condition=movement["condition"]
            )
    return state


@pytest.mark.django_db
def test_history_is_chronological_paginated_and_matches_state(client, api_world):
    client.force_login(api_world["account"])
    item, person = api_world["item"], api_world["person"]
    assert _checkout(client, item, person).status_code == 201
    assert _return(client, item, "unfit", "Cano obstruído").status_code == 201
    # The fixture item was stored directly, so its history starts at the checkout.
    first = client.get(f"/api/v1/items/{item.id}/events/?limit=1").json()
    assert first["meta"] == {"count": 2, "limit": 1, "offset": 0}
    second = client.get(f"/api/v1/items/{item.id}/events/?limit=1&offset=1").json()
    events = first["data"] + second["data"]
    assert [e["type"] for e in events] == ["item.checked_out", "item.returned"]
    assert events == sorted(events, key=lambda e: e["occurred_at"])
    assert events[0]["movement"]["recipient"] == {"id": str(person.id), "name": str(person)}
    assert events[1]["movement"]["reason"] == "Cano obstruído"

    detail = client.get(f"/api/v1/items/{item.id}/").json()["data"]
    replayed = _replay(events)
    assert replayed["availability"] == detail["availability"]
    assert replayed["condition"] == detail["condition"]
    assert replayed["holder"] == (detail["current_holder"] or {}).get("id")


@pytest.mark.django_db
def test_history_has_no_write_route(client, api_world):
    client.force_login(api_world["account"])
    url = f"/api/v1/items/{api_world['item'].id}/events/"
    assert client.post(url, data="{}", content_type="application/json").status_code == 405
    assert client.delete(url).status_code == 405


@pytest.mark.django_db
def test_history_never_exposes_personal_documents(client, api_world):
    Person.objects.filter(pk=api_world["person"].pk).update(cpf="52998224725", phone="85999990000")
    client.force_login(api_world["account"])
    _checkout(client, api_world["item"], api_world["person"])
    body = client.get(f"/api/v1/items/{api_world['item'].id}/events/").content.decode()
    assert "52998224725" not in body and "85999990000" not in body


# SIGAB-030: checkout


@pytest.mark.django_db
def test_checkout_event_has_actor_and_instant(client, api_world):
    client.force_login(api_world["account"])
    response = _checkout(client, api_world["item"], api_world["person"])
    movement = Movement.objects.get(pk=response.json()["data"]["movement_id"])
    event = MovementEvent.objects.get(movement=movement)
    assert event.actor == api_world["account"] == movement.operator
    assert event.occurred_at == movement.confirmed_at
    assert movement.recipient == api_world["person"]


@pytest.mark.django_db
def test_checkout_is_atomic_when_a_later_step_fails(client, api_world, monkeypatch):
    def failing_audit(*args, **kwargs):
        raise RuntimeError("falha sintética na auditoria")

    monkeypatch.setattr("sigab.services.audit", failing_audit)
    client = Client(raise_request_exception=False)
    client.force_login(api_world["account"])
    response = _checkout(client, api_world["item"], api_world["person"])
    assert response.status_code == 500
    item = Item.objects.get(pk=api_world["item"].pk)
    assert item.availability == "available" and item.current_holder is None
    assert not Movement.objects.filter(movement_type="checkout").exists()
    assert not MovementEvent.objects.filter(event_type="item.checked_out").exists()


@pytest.mark.django_db
def test_only_available_item_can_leave(client, api_world):
    client.force_login(api_world["account"])
    item = api_world["item"]
    Item.objects.filter(pk=item.pk).update(
        condition="unfit", condition_reason="x", availability="unavailable"
    )
    assert _checkout(client, item, api_world["person"]).status_code == 409


@pytest.mark.django_db
def test_current_possession_of_a_person(client, api_world):
    client.force_login(api_world["account"])
    _checkout(client, api_world["item"], api_world["person"])
    rows = client.get(f"/api/v1/items/?holder={api_world['person'].id}").json()["data"]
    assert [row["id"] for row in rows] == [str(api_world["item"].id)]
    assert client.get("/api/v1/items/?holder=x").status_code == 400
