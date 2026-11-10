import json
import uuid

import pytest
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import Client

from sigab.management.commands.verify_audit_chain import verify_chain
from sigab.models import Account, AuditEvent, Grant, Role
from sigab.permissions import AUDIT_VIEW, TENANT_PERMISSIONS
from sigab.tests.legacy_organizations import legacy_organization

PASSWORD = "Senha-forte-123"


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def admin(api_world):
    """Second account with every tenant permission except audit.export, at organization scope."""
    organization = api_world["organization"]
    account = Account.objects.create_user(
        username="admin-total", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(
        organization=organization,
        name="Total",
        permissions=sorted(TENANT_PERMISSIONS - {"audit.export"}),
    )
    Grant.objects.create(
        organization=organization, account=account, role=role, scope_type="organization"
    )
    client = Client()
    client.force_login(account)
    return {**api_world, "client": client, "admin": account}


def _audited(organization, action):
    return AuditEvent.objects.filter(organization=organization, action=action, result="success")


@pytest.mark.django_db
def test_chain_is_sequential_and_verifiable(admin):
    for code in ("U-1", "U-2", "U-3"):
        _post(admin["client"], "/api/v1/units/", {"code": code, "name": code})
    events = list(
        AuditEvent.objects.filter(organization=admin["organization"]).order_by("sequence")
    )
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    assert all(e.previous_hash == p.record_hash for p, e in zip(events, events[1:], strict=False))
    assert verify_chain(admin["organization"]) is None
    call_command("verify_audit_chain", verbosity=0)


@pytest.mark.django_db
def test_chain_detects_direct_sql_changes_and_deletions(admin):
    for code in ("U-1", "U-2", "U-3"):
        _post(admin["client"], "/api/v1/units/", {"code": code, "name": code})
    middle = AuditEvent.objects.get(organization=admin["organization"], sequence=2)
    table = AuditEvent._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} SET reason = %s WHERE id = %s", ["adulterado", middle.id.hex]
        )
    assert "sequência 2: conteúdo alterado" in verify_chain(admin["organization"])
    with pytest.raises(CommandError):
        call_command("verify_audit_chain", organization_id=str(admin["organization"].id))
    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE id = %s", [middle.id.hex])
    assert "sequência 2 ausente" in verify_chain(admin["organization"])


@pytest.mark.django_db
def test_every_p0_operation_is_audited(admin, client):
    c, org = admin["client"], admin["organization"]
    unit = _post(c, "/api/v1/units/", {"code": "U-P0", "name": "P0"}).json()["data"]
    unit = _post(
        c, f"/api/v1/units/{unit['id']}/locations/", {"code": "R-P0", "name": "Reserva"}
    ).json()["data"]
    equipment_type = _post(
        c, "/api/v1/equipment-types/", {"name": "Tipo P0", "classification": "individual"}
    ).json()["data"]
    item = _post(
        c,
        "/api/v1/items/",
        {
            "equipment_type_id": equipment_type["id"],
            "unit_id": unit["id"],
            "storage_location_id": unit["locations"][0]["id"],
            "serial_number": "P0-1",
            "confirmed": True,
        },
    ).json()["data"]
    person = _post(c, "/api/v1/people/", {"name": "Pessoa P0"}).json()["data"]
    _post(
        c,
        f"/api/v1/people/{person['id']}/memberships/",
        {"registration": "P0-MAT", "main_unit_id": unit["id"]},
    )
    person = _post(
        c, f"/api/v1/people/{person['id']}/account/", {"username": "p0", "password": PASSWORD}
    ).json()["data"]
    account_id = person["accounts"][0]["id"]
    role = Role.objects.get(organization=org, name="Total")
    _post(
        c,
        f"/api/v1/accounts/{account_id}/grants/",
        {"role_id": str(role.id), "scope_type": "organization", "reason": "P0"},
    )
    checkout = _post(
        c,
        f"/api/v1/items/{item['id']}/checkout/",
        {"recipient_id": person["id"], "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    ).json()["data"]
    _post(
        c,
        f"/api/v1/items/{item['id']}/return/",
        {"condition": "fit", "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    )
    _post(
        c,
        f"/api/v1/items/{item['id']}/condition/",
        {
            "condition": "unfit",
            "reason": "x",
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": True,
        },
    )
    _post(c, f"/api/v1/accounts/{account_id}/suspend/", {"confirmed": True})
    client.post("/entrar/", {"username": "operador-api", "password": PASSWORD})
    expected = {
        "unit.create",
        "storagelocation.create",
        "equipmenttype.create",
        "item.incorporate",
        "person.create",
        "membership.create",
        "account.create",
        "grant.create",
        "item.checkout",
        "item.return",
        "item.condition_change",
        "account.suspend",
        "auth.login",
    }
    recorded = set(AuditEvent.objects.filter(organization=org).values_list("action", flat=True))
    assert expected <= recorded, expected - recorded
    event = _audited(org, "item.checkout").get()
    assert event.actor == admin["admin"]
    assert event.object_id == checkout["movement_id"]
    assert event.correlation_id and event.occurred_at
    assert verify_chain(org) is None


@pytest.mark.django_db
def test_audit_trail_requires_permission_and_stays_in_tenant(admin, client, api_world):
    other = legacy_organization(name="Outra")
    AuditEvent.objects.create(
        organization=other,
        action="segredo.externo",
        object_type="x",
        object_id="x",
        occurred_at=api_world["item"].created_at,
        correlation_id="x",
    )
    client.force_login(api_world["account"])
    assert client.get("/api/v1/audit/").status_code == 403
    response = admin["client"].get("/api/v1/audit/?limit=500")
    assert response.status_code == 200
    assert "segredo.externo" not in response.content.decode()
    assert AUDIT_VIEW in Role.objects.get(name="Total").permissions


@pytest.mark.django_db
def test_audit_trail_has_no_write_route(admin):
    response = admin["client"].post("/api/v1/audit/", data="{}", content_type="application/json")
    assert response.status_code == 405
    assert admin["client"].delete("/api/v1/audit/").status_code == 405
