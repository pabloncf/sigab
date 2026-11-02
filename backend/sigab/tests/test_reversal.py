import json
import uuid

import pytest
from django.test import Client

from sigab.models import Account, AuditEvent, Grant, Item, Movement, MovementEvent, Role
from sigab.permissions import ITEM_VIEW, MOVEMENT_REVERSE
from sigab.services import ConflictError, reverse_movement

PASSWORD = "Senha-forte-123"


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def flows(api_world):
    operator = Client()
    operator.force_login(api_world["account"])
    organization = api_world["organization"]
    manager = Account.objects.create_user(
        username="gestor-estorno", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(
        organization=organization, name="Estorno", permissions=[ITEM_VIEW, MOVEMENT_REVERSE]
    )
    Grant.objects.create(
        organization=organization, account=manager, role=role, scope_type="organization"
    )
    supervisor = Client()
    supervisor.force_login(manager)
    return {**api_world, "operator": operator, "supervisor": supervisor}


def _checkout(flows, key=None):
    return _post(
        flows["operator"],
        f"/api/v1/items/{flows['item'].id}/checkout/",
        {
            "recipient_id": str(flows["person"].id),
            "idempotency_key": key or str(uuid.uuid4()),
            "confirmed": True,
        },
    )


def _return(flows, condition="fit", reason="", key=None):
    return _post(
        flows["operator"],
        f"/api/v1/items/{flows['item'].id}/return/",
        {
            "condition": condition,
            "reason": reason,
            "idempotency_key": key or str(uuid.uuid4()),
            "confirmed": True,
        },
    )


def _reverse(flows, movement_id, reason="Registro feito no item errado", key=None):
    return _post(
        flows["supervisor"],
        f"/api/v1/movements/{movement_id}/reverse/",
        {"idempotency_key": key or str(uuid.uuid4()), "confirmed": True, "reason": reason},
    )


def _item(flows):
    return Item.objects.get(pk=flows["item"].pk)


# SIGAB-033: return


@pytest.mark.django_db
def test_return_closes_the_right_checkout_and_audits(flows):
    checkout_id = _checkout(flows).json()["data"]["movement_id"]
    response = _return(flows)
    assert response.status_code == 201
    movement = Movement.objects.get(pk=response.json()["data"]["movement_id"])
    assert str(movement.related_movement_id) == checkout_id
    assert movement.recipient == flows["person"]
    assert MovementEvent.objects.filter(movement=movement, event_type="item.returned").exists()
    assert AuditEvent.objects.filter(action="item.return", object_id=str(movement.id)).exists()
    item = _item(flows)
    assert (item.availability, item.current_holder) == ("available", None)


@pytest.mark.django_db
def test_repeated_return_does_not_duplicate_effects(flows):
    _checkout(flows)
    key = str(uuid.uuid4())
    first = _return(flows, key=key)
    replay = _return(flows, key=key)
    assert (first.status_code, replay.status_code) == (201, 200)
    assert replay.json()["data"]["created"] is False
    assert _return(flows).status_code == 409
    assert Movement.objects.filter(movement_type="return").count() == 1
    assert AuditEvent.objects.filter(action="item.return", result="success").count() == 1


# SIGAB-034: reversal


@pytest.mark.django_db
def test_checkout_reversal_restores_reserve_and_keeps_original(flows):
    checkout_id = _checkout(flows).json()["data"]["movement_id"]
    response = _reverse(flows, checkout_id)
    assert response.status_code == 201
    item = _item(flows)
    assert (item.availability, item.current_holder) == ("available", None)
    original = Movement.objects.get(pk=checkout_id)
    reversal = Movement.objects.get(reverses=original)
    assert reversal.reason == "Registro feito no item errado"
    event = MovementEvent.objects.get(movement=reversal)
    assert event.event_type == "item.movement_reversed"
    assert event.compensates == original.events.get()
    audit = AuditEvent.objects.get(action="movement.reverse")
    assert audit.reason == reversal.reason
    assert audit.changes["availability"] == {"from": "in_custody", "to": "available"}

    history = flows["operator"].get(f"/api/v1/items/{item.id}/events/").json()["data"]
    assert [e["type"] for e in history] == ["item.checked_out", "item.movement_reversed"]
    assert history[0]["movement"]["reversed"] is True
    assert history[1]["movement"]["reverses"] == checkout_id


@pytest.mark.django_db
def test_return_reversal_reopens_the_same_checkout(flows):
    checkout_id = _checkout(flows).json()["data"]["movement_id"]
    return_id = _return(flows, "unfit", "Conferência equivocada").json()["data"]["movement_id"]
    assert _reverse(flows, return_id).status_code == 201
    item = _item(flows)
    assert item.availability == "in_custody" and item.current_holder == flows["person"]
    assert (item.condition, item.condition_reason) == ("fit", "")
    # The reopened checkout can be returned again.
    again = _return(flows)
    assert again.status_code == 201
    assert again.json()["data"]["item"]["availability"] == "available"
    assert str(
        Movement.objects.get(pk=again.json()["data"]["movement_id"]).related_movement_id
    ) == (checkout_id)


@pytest.mark.django_db
def test_condition_change_reversal_restores_previous_condition(flows):
    _checkout(flows)
    _return(flows, "unfit", "Cano obstruído")
    release = _post(
        flows["operator"],
        f"/api/v1/items/{flows['item'].id}/condition/",
        {
            "condition": "fit",
            "reason": "Laudo sintético",
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": True,
        },
    )
    assert release.status_code == 201
    assert _reverse(flows, release.json()["data"]["movement_id"]).status_code == 201
    item = _item(flows)
    assert (item.condition, item.condition_reason, item.availability) == (
        "unfit",
        "Cano obstruído",
        "unavailable",
    )


@pytest.mark.django_db
def test_reversal_rules(flows):
    checkout_id = _checkout(flows).json()["data"]["movement_id"]
    return_id = _return(flows).json()["data"]["movement_id"]
    # Only the most recent fact in force can be reversed.
    assert _reverse(flows, checkout_id).status_code == 409
    no_reason = _reverse(flows, return_id, reason="")
    assert no_reason.status_code == 400
    key = str(uuid.uuid4())
    assert _reverse(flows, return_id, key=key).status_code == 201
    assert _reverse(flows, return_id, key=key).status_code == 200
    assert _reverse(flows, return_id).status_code == 409
    reversal = Movement.objects.get(reverses_id=return_id)
    assert _reverse(flows, reversal.id).status_code == 409
    assert Movement.objects.filter(movement_type="reversal").count() == 1


@pytest.mark.django_db
def test_reversal_requires_permission(flows):
    checkout_id = _checkout(flows).json()["data"]["movement_id"]
    response = _post(
        flows["operator"],
        f"/api/v1/movements/{checkout_id}/reverse/",
        {"idempotency_key": str(uuid.uuid4()), "confirmed": True, "reason": "x"},
    )
    assert response.status_code == 403
    assert _item(flows).availability == "in_custody"
    refusal = AuditEvent.objects.get(action="api.movement-reverse")
    assert refusal.result == "denied" and refusal.actor == flows["account"]


@pytest.mark.django_db
def test_incorporation_cannot_be_reversed(world):
    Grant.objects.create(
        organization=world["org"],
        account=world["account"],
        role=Role.objects.create(
            organization=world["org"], name="Gestor W", permissions=[MOVEMENT_REVERSE]
        ),
        scope_type="organization",
    )
    incorporation = world["item"].movements.get(movement_type="incorporation")
    with pytest.raises(ConflictError):
        reverse_movement(
            world["ctx"],
            movement_id=incorporation.id,
            idempotency_key=uuid.uuid4(),
            confirmed=True,
            reason="Duplicidade",
        )
