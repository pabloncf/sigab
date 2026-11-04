"""SIGAB-046: reconciliation of checkouts and returns recorded on paper (ADR 0004)."""

import json
import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from sigab.models import (
    Account,
    AuditEvent,
    Grant,
    Item,
    Movement,
    MovementEvent,
    Organization,
    Role,
)
from sigab.permissions import ITEM_VIEW, MOVEMENT_CHECKOUT, MOVEMENT_RETURN, MOVEMENT_REVERSE

PASSWORD = "Senha-forte-123"


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def paper(api_world):
    operator = Client()
    operator.force_login(api_world["account"])
    return {**api_world, "operator": operator}


def _ago(**kwargs):
    return timezone.now() - timedelta(**kwargs)


def _checkout(paper, *, occurred_at, reference="F01/L01", key=None, client=None):
    body = {
        "recipient_id": str(paper["person"].id),
        "idempotency_key": key or str(uuid.uuid4()),
        "confirmed": True,
    }
    if occurred_at is not None:
        body["contingency"] = {"occurred_at": occurred_at.isoformat(), "paper_reference": reference}
    return _post(client or paper["operator"], f"/api/v1/items/{paper['item'].id}/checkout/", body)


def _return(paper, *, occurred_at, reference="F01/L02", condition="fit", reason="", key=None):
    body = {
        "condition": condition,
        "reason": reason,
        "idempotency_key": key or str(uuid.uuid4()),
        "confirmed": True,
    }
    if occurred_at is not None:
        body["contingency"] = {"occurred_at": occurred_at.isoformat(), "paper_reference": reference}
    return _post(paper["operator"], f"/api/v1/items/{paper['item'].id}/return/", body)


def _item(paper):
    return Item.objects.get(pk=paper["item"].pk)


@pytest.mark.django_db
def test_contingency_checkout_keeps_fact_instant_apart_from_registration(paper):
    fact = _ago(hours=3)
    response = _checkout(paper, occurred_at=fact, reference=" F03/L07 ")

    assert response.status_code == 201
    movement = Movement.objects.get(pk=response.json()["data"]["movement_id"])
    assert movement.origin == Movement.Origin.CONTINGENCY
    assert movement.declared_occurred_at == fact
    assert movement.confirmed_at > fact + timedelta(hours=2)
    assert movement.paper_reference == "F03/L07"
    assert movement.operator == paper["account"]
    event = movement.events.get()
    assert event.occurred_at == fact
    assert event.metadata == {
        "recipient_id": str(paper["person"].id),
        "schema": "item.checked_out.v1",
    }
    audit = AuditEvent.objects.get(object_id=str(movement.id))
    assert audit.action == "item.checkout.contingency"
    assert audit.actor == paper["account"]
    assert audit.occurred_at >= movement.confirmed_at
    assert audit.changes["occurred_at"] == fact.isoformat()
    assert audit.changes["paper_reference"] == "F03/L07"
    item = _item(paper)
    assert item.availability == Item.Availability.IN_CUSTODY
    assert item.current_holder == paper["person"]


@pytest.mark.django_db
def test_contingency_return_closes_system_checkout_and_history_shows_both_instants(paper):
    assert _checkout(paper, occurred_at=None).status_code == 201
    # The outage starts after the checkout registered in the system.
    returned_at = timezone.now()
    response = _return(paper, occurred_at=returned_at, condition="unfit", reason="Falha")
    assert response.status_code == 201
    item = _item(paper)
    assert item.availability == Item.Availability.UNAVAILABLE
    assert item.condition == Item.Condition.UNFIT
    assert item.current_holder is None

    events = paper["operator"].get(f"/api/v1/items/{paper['item'].id}/events/").json()["data"]
    assert [e["type"] for e in events] == ["item.checked_out", "item.returned"]
    assert [e["movement"]["origin"] for e in events] == ["system", "contingency"]
    assert events[1]["occurred_at"] == returned_at.isoformat()
    assert events[1]["movement"]["paper_reference"] == "F01/L02"
    assert events[1]["movement"]["recorded_at"] >= events[1]["occurred_at"]


@pytest.mark.django_db
def test_future_fact_instant_is_rejected(paper):
    response = _checkout(paper, occurred_at=timezone.now() + timedelta(minutes=5))

    assert response.status_code == 400
    assert "occurred_at" in response.json()["details"]
    assert not Movement.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "contingency",
    [
        {"occurred_at": "2026-11-01T10:00:00", "paper_reference": "F01/L01"},
        {"occurred_at": "2026-11-01T10:00:00-03:00", "paper_reference": "  "},
        {"paper_reference": "F01/L01"},
        "F01/L01",
    ],
)
def test_contingency_requires_aware_instant_and_reference(paper, contingency):
    response = _post(
        paper["operator"],
        f"/api/v1/items/{paper['item'].id}/checkout/",
        {
            "recipient_id": str(paper["person"].id),
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": True,
            "contingency": contingency,
        },
    )

    assert response.status_code == 400
    assert not Movement.objects.exists()


@pytest.mark.django_db
def test_state_conflict_is_a_divergence_and_is_not_forced(paper):
    assert _checkout(paper, occurred_at=_ago(hours=2), reference="F01/L01").status_code == 201

    response = _checkout(paper, occurred_at=_ago(hours=1), reference="F01/L02")

    assert response.status_code == 409
    assert response.json()["error"].startswith("Divergência")
    assert Movement.objects.count() == 1
    refusal = AuditEvent.objects.get(result="divergence")
    assert refusal.action == "api.item-checkout"
    assert refusal.actor == paper["account"]


@pytest.mark.django_db
def test_fact_before_the_last_record_of_the_item_is_a_divergence(paper):
    assert _checkout(paper, occurred_at=None).status_code == 201

    response = _return(paper, occurred_at=_ago(hours=1))

    assert response.status_code == 409
    assert "Consulte o histórico" in response.json()["error"]
    assert _item(paper).availability == Item.Availability.IN_CUSTODY


@pytest.mark.django_db
def test_sheet_line_is_reconciled_only_once_per_reserve(paper):
    assert _checkout(paper, occurred_at=_ago(hours=3), reference="F02/L05").status_code == 201

    response = _return(paper, occurred_at=_ago(hours=2), reference="F02/L05")

    assert response.status_code == 409
    assert "folha/linha" in response.json()["error"]


@pytest.mark.django_db
def test_replay_is_idempotent_and_key_reuse_with_other_paper_data_conflicts(paper):
    key = str(uuid.uuid4())
    fact = _ago(hours=1)
    first = _checkout(paper, occurred_at=fact, key=key)
    replay = _checkout(paper, occurred_at=fact, key=key)
    other_line = _checkout(paper, occurred_at=fact, reference="F09/L09", key=key)
    live = _checkout(paper, occurred_at=None, key=key)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["data"]["created"] is False
    assert replay.json()["data"]["movement_id"] == first.json()["data"]["movement_id"]
    assert other_line.status_code == 409
    assert live.status_code == 409
    assert Movement.objects.count() == 1


@pytest.mark.django_db
def test_wrong_reconciliation_can_be_reversed_and_entered_again(paper):
    organization = paper["organization"]
    manager = Account.objects.create_user(
        username="gestor-contingencia", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(
        organization=organization, name="Estorno", permissions=[ITEM_VIEW, MOVEMENT_REVERSE]
    )
    Grant.objects.create(
        organization=organization, account=manager, role=role, scope_type="organization"
    )
    supervisor = Client()
    supervisor.force_login(manager)
    fact = _ago(hours=2)
    wrong = _checkout(paper, occurred_at=fact, reference="F04/L01")

    reversal = _post(
        supervisor,
        f"/api/v1/movements/{wrong.json()['data']['movement_id']}/reverse/",
        {"idempotency_key": str(uuid.uuid4()), "confirmed": True, "reason": "Destinatário errado"},
    )
    again = _checkout(paper, occurred_at=fact, reference="F04/L01")

    assert reversal.status_code == 201
    assert again.status_code == 201
    assert _item(paper).availability == Item.Availability.IN_CUSTODY


@pytest.mark.django_db
def test_contingency_requires_the_same_permission_as_live_checkout(paper):
    organization = paper["organization"]
    viewer = Account.objects.create_user(
        username="consulta", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(organization=organization, name="Consulta", permissions=[ITEM_VIEW])
    Grant.objects.create(
        organization=organization, account=viewer, role=role, scope_type="organization"
    )
    client = Client()
    client.force_login(viewer)

    response = _checkout(paper, occurred_at=_ago(hours=1), client=client)

    assert response.status_code == 404
    assert not Movement.objects.exists()


@pytest.mark.django_db
def test_contingency_cannot_reach_an_item_of_another_organization(paper):
    other = Organization.objects.create(name="Outra organização")
    stranger = Account.objects.create_user(
        username="operador-externo", password=PASSWORD, organization=other
    )
    role = Role.objects.create(
        organization=other,
        name="Operador",
        permissions=[ITEM_VIEW, MOVEMENT_CHECKOUT, MOVEMENT_RETURN],
    )
    Grant.objects.create(organization=other, account=stranger, role=role, scope_type="organization")
    client = Client()
    client.force_login(stranger)

    response = _checkout(paper, occurred_at=_ago(hours=1), client=client)

    assert response.status_code == 404
    assert response.json()["error"] == "Recurso não encontrado."
    assert not Movement.objects.exists()
    assert not MovementEvent.objects.exists()


@pytest.mark.django_db
def test_database_rejects_contingency_without_fact_instant_or_reference(paper):
    base = {
        "organization": paper["organization"],
        "movement_type": Movement.Type.CHECKOUT,
        "item": paper["item"],
        "operator": paper["account"],
        "recipient": paper["person"],
        "confirmed_at": timezone.now(),
        "origin": Movement.Origin.CONTINGENCY,
    }
    invalid = [
        {"paper_reference": "F01/L01"},
        {"declared_occurred_at": _ago(hours=1)},
        {"declared_occurred_at": timezone.now() + timedelta(hours=1), "paper_reference": "F"},
    ]
    for extra in invalid:
        with pytest.raises(IntegrityError), transaction.atomic():
            Movement.objects.create(**base, **extra, idempotency_key=uuid.uuid4())
