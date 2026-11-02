"""SIGAB-043: one HTTP journey through real views, permissions and persistence."""

import json
import uuid

import pytest
from django.test import Client

from sigab.models import Account, AuditEvent, Grant, Item, Movement, Organization, Role
from sigab.permissions import (
    CATALOG_MANAGE,
    ITEM_CREATE,
    ITEM_VIEW,
    MANAGE_IDENTITY,
    MOVEMENT_CHECKOUT,
    MOVEMENT_RETURN,
)


@pytest.mark.django_db
def test_vertical_flow_from_registration_to_return():
    organization = Organization.objects.create(name="Guarda sintética")
    password = "Synthetic-test-only-123!"

    def session(username, permissions, tenant=organization):
        account = Account.objects.create_user(
            username=username, password=password, organization=tenant
        )
        role = Role.objects.create(organization=tenant, name=username, permissions=permissions)
        Grant.objects.create(
            organization=tenant, account=account, role=role, scope_type="organization"
        )
        client = Client(enforce_csrf_checks=True)
        assert client.login(username=username, password=password)
        assert client.get("/api/v1/session/").status_code == 200
        return client

    manager = session("manager", [CATALOG_MANAGE, ITEM_CREATE, ITEM_VIEW, MANAGE_IDENTITY])
    operator = session("operator", [ITEM_VIEW, MOVEMENT_CHECKOUT, MOVEMENT_RETURN])

    def post(client, path, payload, expected=201):
        response = client.post(
            f"/api/v1/{path}",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        assert response.status_code == expected, response.content
        return response.json().get("data")

    unit = post(manager, "units/", {"name": "Unidade sintética", "code": "DEMO"})
    locations = post(manager, f"units/{unit['id']}/locations/", {"name": "Reserva", "code": "R"})
    equipment = post(
        manager, "equipment-types/", {"name": "Item sintético", "classification": "individual"}
    )
    person = post(manager, "people/", {"name": "Pessoa sintética"})
    post(
        manager,
        f"people/{person['id']}/memberships/",
        {"registration": "SYN-001", "main_unit_id": unit["id"]},
    )
    item = post(
        manager,
        "items/",
        {
            "equipment_type_id": equipment["id"],
            "unit_id": unit["id"],
            "storage_location_id": locations["locations"][0]["id"],
            "serial_number": "SYN-VERTICAL-001",
            "confirmed": True,
        },
    )
    path = f"items/{item['id']}/"
    checkout = {
        "recipient_id": person["id"],
        "confirmed": True,
        "idempotency_key": str(uuid.uuid4()),
    }
    post(manager, path + "checkout/", checkout, expected=404)
    assert Movement.objects.filter(item_id=item["id"]).count() == 1
    post(operator, path + "checkout/", checkout)
    post(operator, path + "checkout/", checkout, expected=200)
    post(
        operator,
        path + "checkout/",
        {**checkout, "idempotency_key": str(uuid.uuid4())},
        expected=409,
    )
    assert operator.get(f"/api/v1/{path}").json()["data"]["availability"] == "in_custody"

    other = session(
        "other",
        [ITEM_VIEW, MOVEMENT_CHECKOUT, MOVEMENT_RETURN],
        Organization.objects.create(name="Outra guarda sintética"),
    )
    assert other.get(f"/api/v1/{path}").status_code == 404
    assert other.get(f"/api/v1/{path}events/").status_code == 404
    post(
        other,
        path + "return/",
        {"condition": "fit", "confirmed": True, "idempotency_key": str(uuid.uuid4())},
        expected=404,
    )
    post(
        operator,
        path + "return/",
        {"condition": "fit", "confirmed": True, "idempotency_key": str(uuid.uuid4())},
    )
    restored = Item.objects.get(pk=item["id"])
    assert restored.availability == "available" and restored.current_holder is None
    events = operator.get(f"/api/v1/{path}events/").json()["data"]
    assert [event["type"] for event in events] == [
        "item.incorporated",
        "item.checked_out",
        "item.returned",
    ]
    assert Movement.objects.filter(item=restored).count() == 3
    assert AuditEvent.objects.filter(organization=organization, action="item.checkout").count() == 1
    assert AuditEvent.objects.filter(organization=organization, action="item.return").count() == 1
