import json
import uuid

import pytest
from django.test import Client

from sigab.models import Grant, Item, Role, StorageLocation, Unit
from sigab.permissions import VIEW_ITEM


def _post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _second_item(world, unit=None, serial="API-002"):
    unit = unit or world["item"].unit
    location = (
        world["item"].storage_location
        if unit == world["item"].unit
        else StorageLocation.objects.create(
            organization=world["organization"], unit=unit, name="Reserva B", code=f"R-{serial}"
        )
    )
    return Item.objects.create(
        organization=world["organization"],
        equipment_type=world["item"].equipment_type,
        unit=unit,
        storage_location=location,
        serial_number=serial,
    )


@pytest.mark.django_db
def test_validation_error_keeps_field_name(client, api_world):
    client.force_login(api_world["account"])
    response = _post_json(
        client,
        f"/api/v1/items/{api_world['item'].id}/checkout/",
        {"recipient_id": "x", "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "Dados inválidos."
    assert body["details"] == {"recipient_id": ["Informe um UUID válido."]}
    assert body["correlation_id"] == response["X-Request-ID"]


@pytest.mark.django_db
def test_idempotency_key_reused_for_another_item_is_a_conflict(client, api_world):
    client.force_login(api_world["account"])
    other_item = _second_item(api_world)
    key = str(uuid.uuid4())
    payload = {
        "recipient_id": str(api_world["person"].id),
        "idempotency_key": key,
        "confirmed": True,
    }
    first = _post_json(client, f"/api/v1/items/{api_world['item'].id}/checkout/", payload)
    assert first.status_code == 201
    replay = _post_json(client, f"/api/v1/items/{api_world['item'].id}/checkout/", payload)
    assert replay.status_code == 200
    assert replay.json()["data"]["created"] is False

    reused = _post_json(client, f"/api/v1/items/{other_item.id}/checkout/", payload)
    assert reused.status_code == 409
    other_item.refresh_from_db()
    assert other_item.availability == Item.Availability.AVAILABLE


@pytest.mark.django_db
def test_item_list_is_paginated(client, api_world):
    client.force_login(api_world["account"])
    _second_item(api_world)
    response = client.get("/api/v1/items/?limit=1&offset=1")
    body = response.json()
    assert response.status_code == 200
    assert body["meta"] == {"count": 2, "limit": 1, "offset": 1}
    assert len(body["data"]) == 1
    assert client.get("/api/v1/items/?limit=0").status_code == 400
    assert client.get("/api/v1/items/?limit=abc").status_code == 400


@pytest.mark.django_db
def test_unit_grant_does_not_reach_other_unit(client, api_world):
    organization = api_world["organization"]
    other_unit = Unit.objects.create(organization=organization, name="Unidade B", code="U-B")
    hidden = _second_item(api_world, unit=other_unit, serial="API-B")
    account = api_world["account"]
    account.grants.update(is_active=False)
    role = Role.objects.create(organization=organization, name="Leitor", permissions=[VIEW_ITEM])
    Grant.objects.create(
        organization=organization,
        account=account,
        role=role,
        scope_type=Grant.Scope.UNIT,
        unit=api_world["item"].unit,
    )
    client.force_login(account)
    ids = [row["id"] for row in client.get("/api/v1/items/").json()["data"]]
    assert ids == [str(api_world["item"].id)]
    assert client.get(f"/api/v1/items/{hidden.id}/").status_code == 404


@pytest.mark.django_db
def test_unknown_api_route_returns_json_404(client, api_world):
    client.force_login(api_world["account"])
    response = client.get("/api/v1/nao-existe/")
    assert response.status_code == 404
    assert response.json()["error"] == "Recurso não encontrado."


@pytest.mark.django_db
def test_csrf_failure_on_api_returns_json(api_world):
    client = Client(enforce_csrf_checks=True)
    client.force_login(api_world["account"])
    response = _post_json(client, "/api/v1/session/logout/", {})
    assert response.status_code == 403
    assert response.json()["success"] is False


@pytest.mark.django_db
def test_unexpected_error_returns_json_with_correlation(monkeypatch, api_world):
    def explode(*args, **kwargs):
        raise RuntimeError("falha sintética")

    monkeypatch.setattr("sigab.api.views._item_summary", explode)
    client = Client(raise_request_exception=False)
    client.force_login(api_world["account"])
    response = client.get("/api/v1/items/", headers={"X-Request-ID": "req-500"})
    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "error": "Erro interno. Informe o código de correlação ao suporte.",
        "correlation_id": "req-500",
    }
    assert "falha sintética" not in response.content.decode()
