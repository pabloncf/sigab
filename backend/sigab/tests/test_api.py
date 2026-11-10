import json
import uuid

import pytest
from django.test import Client

from sigab.models import (
    EquipmentType,
    Item,
    StorageLocation,
    Unit,
)
from sigab.tests.legacy_organizations import legacy_organization


def _post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
def test_api_requires_authentication(client):
    response = client.get("/api/v1/items/")
    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "error": "Autenticação necessária.",
        "correlation_id": response["X-Request-ID"],
    }


@pytest.mark.django_db
def test_api_lists_only_authorized_tenant_items(client, api_world):
    other = legacy_organization(name="Outra organização")
    other_unit = Unit.objects.create(organization=other, name="Outra unidade", code="OUT")
    other_location = StorageLocation.objects.create(
        organization=other, unit=other_unit, name="Outra reserva", code="OUT-R"
    )
    other_type = EquipmentType.objects.create(
        organization=other,
        name="Outro equipamento",
        classification=EquipmentType.Classification.INDIVIDUAL,
    )
    other_item = Item.objects.create(
        organization=other,
        equipment_type=other_type,
        unit=other_unit,
        storage_location=other_location,
        serial_number="OTHER-001",
    )
    client.force_login(api_world["account"])

    response = client.get("/api/v1/items/")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(api_world["item"].id)]
    assert client.get(f"/api/v1/items/{other_item.id}/").status_code == 404


@pytest.mark.django_db
def test_api_checkout_is_validated_and_idempotent(client, api_world):
    client.force_login(api_world["account"])
    url = f"/api/v1/items/{api_world['item'].id}/checkout/"
    idempotency_key = str(uuid.uuid4())
    payload = {
        "recipient_id": str(api_world["person"].id),
        "idempotency_key": idempotency_key,
        "confirmed": True,
    }

    first = _post_json(client, url, payload)
    repeated = _post_json(client, url, payload)

    assert first.status_code == 201
    assert repeated.status_code == 200
    assert first.json()["data"]["created"] is True
    assert repeated.json()["data"]["created"] is False
    assert first.json()["data"]["movement_id"] == repeated.json()["data"]["movement_id"]


@pytest.mark.django_db
def test_api_rejects_missing_explicit_confirmation(client, api_world):
    client.force_login(api_world["account"])
    response = _post_json(
        client,
        f"/api/v1/items/{api_world['item'].id}/checkout/",
        {
            "recipient_id": str(api_world["person"].id),
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": False,
        },
    )
    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.django_db
def test_api_state_change_requires_csrf(api_world):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(api_world["account"])
    response = _post_json(
        csrf_client,
        f"/api/v1/items/{api_world['item'].id}/checkout/",
        {
            "recipient_id": str(api_world["person"].id),
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": True,
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_session_endpoint_sets_csrf_cookie(client, api_world):
    client.force_login(api_world["account"])
    response = client.get("/api/v1/session/")
    assert response.status_code == 200
    assert response.json()["data"]["organization"]["id"] == str(api_world["organization"].id)
    assert "csrftoken" in response.cookies
