"""Cross-organization isolation suite (SIGAB-025, RF-01, RNF-05).

Every API route must appear in CASES. A request carrying another organization's
identifiers must fail with the same answer as a missing record, change nothing and never
echo the foreign data. `test_every_api_route_has_an_isolation_case` blocks new routes
without a case here.
"""

import json
import uuid

import pytest
from django.test import Client
from django.urls import URLPattern

from sigab.api import urls as api_urls
from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    Item,
    Membership,
    Movement,
    Organization,
    Person,
    Role,
    StorageLocation,
    Unit,
)
from sigab.permissions import AUDIT_EXPORT, TENANT_PERMISSIONS
from sigab.services import CommandContext, checkout_item

PASSWORD = "Senha-forte-123"
NOT_FOUND = {"success": False, "error": "Recurso não encontrado."}


def _tenant(name, code, with_movement=False):
    organization = Organization.objects.create(name=name)
    unit = Unit.objects.create(organization=organization, name=f"Unidade {code}", code=f"U-{code}")
    location = StorageLocation.objects.create(
        organization=organization, unit=unit, name=f"Reserva {code}", code=f"R-{code}"
    )
    equipment_type = EquipmentType.objects.create(
        organization=organization, name=f"Tipo {code}", classification="individual"
    )
    item = Item.objects.create(
        organization=organization,
        equipment_type=equipment_type,
        unit=unit,
        storage_location=location,
        serial_number=f"SER-{code}",
    )
    person = Person.objects.create(organization=organization, name=f"Pessoa {code}")
    membership = Membership.objects.create(
        organization=organization, person=person, registration=f"MAT-{code}", main_unit=unit
    )
    account = Account.objects.create_user(
        username=f"conta-{code}", password=PASSWORD, organization=organization, person=person
    )
    role = Role.objects.create(
        organization=organization,
        name=f"Tudo {code}",
        permissions=sorted(TENANT_PERMISSIONS - {AUDIT_EXPORT}),
    )
    grant = Grant.objects.create(
        organization=organization, account=account, role=role, scope_type="organization"
    )
    movement = None
    if with_movement:
        movement, _ = checkout_item(
            CommandContext(account, organization, f"setup-{code}"),
            item_id=item.id,
            recipient_id=person.id,
            idempotency_key=uuid.uuid4(),
            confirmed=True,
        )
    return {
        "movement": movement,
        "organization": organization,
        "unit": unit,
        "location": location,
        "type": equipment_type,
        "item": item,
        "person": person,
        "membership": membership,
        "account": account,
        "role": role,
        "grant": grant,
    }


@pytest.fixture
def tenants(db):
    own = _tenant("Organização A", "A")
    foreign = _tenant("Organização B", "B", with_movement=True)
    # A second account in A acts, so that "own account" rules never mask isolation.
    actor = Account.objects.create_user(
        username="ator-a", password=PASSWORD, organization=own["organization"]
    )
    Grant.objects.create(
        organization=own["organization"], account=actor, role=own["role"], scope_type="organization"
    )
    client = Client()
    client.force_login(actor)
    return {"own": own, "foreign": foreign, "client": client}


def _snapshot(foreign):
    return {
        "item": Item.objects.filter(pk=foreign["item"].pk).values().get(),
        "person": Person.objects.filter(pk=foreign["person"].pk).values().get(),
        "membership": Membership.objects.filter(pk=foreign["membership"].pk).values().get(),
        "account": Account.objects.filter(pk=foreign["account"].pk).values().get(),
        "grant": Grant.objects.filter(pk=foreign["grant"].pk).values().get(),
        "unit": Unit.objects.filter(pk=foreign["unit"].pk).values().get(),
        "location": StorageLocation.objects.filter(pk=foreign["location"].pk).values().get(),
        "type": EquipmentType.objects.filter(pk=foreign["type"].pk).values().get(),
        "movements": Movement.objects.filter(organization=foreign["organization"]).count(),
        "audit": AuditEvent.objects.filter(organization=foreign["organization"]).count(),
    }


def _key():
    return str(uuid.uuid4())


# (route name, method, path builder, payload builder). Paths use the FOREIGN tenant ids.
OBJECT_CASES = [
    ("item-detail", "get", lambda f: f"items/{f['item'].id}/", None),
    ("item-events", "get", lambda f: f"items/{f['item'].id}/events/", None),
    (
        "movement-reverse",
        "post",
        lambda f: f"movements/{f['movement'].id}/reverse/",
        lambda f: {"idempotency_key": _key(), "confirmed": True, "reason": "x"},
    ),
    ("recipient-list", "get", lambda f: f"items/{f['item'].id}/recipients/", None),
    (
        "item-checkout",
        "post",
        lambda f: f"items/{f['item'].id}/checkout/",
        lambda f: {
            "recipient_id": str(f["person"].id),
            "idempotency_key": _key(),
            "confirmed": True,
        },
    ),
    (
        "item-return",
        "post",
        lambda f: f"items/{f['item'].id}/return/",
        lambda f: {"condition": "fit", "idempotency_key": _key(), "confirmed": True},
    ),
    (
        "item-condition",
        "post",
        lambda f: f"items/{f['item'].id}/condition/",
        lambda f: {
            "condition": "unfit",
            "reason": "x",
            "idempotency_key": _key(),
            "confirmed": True,
        },
    ),
    ("person-detail", "get", lambda f: f"people/{f['person'].id}/", None),
    (
        "person-detail",
        "patch",
        lambda f: f"people/{f['person'].id}/",
        lambda f: {"name": "Alterado"},
    ),
    (
        "person-status",
        "post",
        lambda f: f"people/{f['person'].id}/status/",
        lambda f: {"is_active": False, "confirmed": True},
    ),
    (
        "person-memberships",
        "post",
        lambda f: f"people/{f['person'].id}/memberships/",
        lambda f: {"registration": "MAT-X", "main_unit_id": str(f["unit"].id)},
    ),
    (
        "person-account",
        "post",
        lambda f: f"people/{f['person'].id}/account/",
        lambda f: {"username": "nova-conta", "password": PASSWORD},
    ),
    (
        "membership-status",
        "post",
        lambda f: f"memberships/{f['membership'].id}/status/",
        lambda f: {"is_active": False, "confirmed": True},
    ),
    *[
        (
            f"account-{action}",
            "post",
            lambda f, action=action: f"accounts/{f['account'].id}/{action}/",
            lambda f: {"confirmed": True},
        )
        for action in ("suspend", "reactivate", "revoke", "end-sessions")
    ],
    (
        "account-grants",
        "post",
        lambda f: f"accounts/{f['account'].id}/grants/",
        lambda f: {"role_id": str(f["role"].id), "scope_type": "organization", "reason": "x"},
    ),
    (
        "grant-revoke",
        "post",
        lambda f: f"grants/{f['grant'].id}/revoke/",
        lambda f: {"confirmed": True, "reason": "x"},
    ),
    ("unit-detail", "patch", lambda f: f"units/{f['unit'].id}/", lambda f: {"name": "Alterada"}),
    (
        "unit-status",
        "post",
        lambda f: f"units/{f['unit'].id}/status/",
        lambda f: {"is_active": False, "confirmed": True},
    ),
    (
        "unit-locations",
        "post",
        lambda f: f"units/{f['unit'].id}/locations/",
        lambda f: {"code": "R-X", "name": "X"},
    ),
    (
        "location-status",
        "post",
        lambda f: f"locations/{f['location'].id}/status/",
        lambda f: {"is_active": False, "confirmed": True},
    ),
    (
        "equipment-type-detail",
        "patch",
        lambda f: f"equipment-types/{f['type'].id}/",
        lambda f: {"name": "Alterado"},
    ),
    (
        "equipment-type-status",
        "post",
        lambda f: f"equipment-types/{f['type'].id}/status/",
        lambda f: {"is_active": False, "confirmed": True},
    ),
]

# Collections: listing never shows foreign rows; creation never accepts foreign references.
COLLECTION_CASES = {
    "item-list",
    "search",
    "activity",
    "audit-trail",
    "person-list",
    "unit-list",
    "equipment-type-list",
    "role-list",
}

# Routes without tenant data.
TENANT_FREE = {"session-detail", "session-logout", "not-found"}


def _call(client, method, path, payload):
    url = f"/api/v1/{path}"
    if payload is None:
        return getattr(client, method)(url)
    return getattr(client, method)(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, method, path, payload",
    OBJECT_CASES,
    ids=[f"{case[0]}-{case[1]}" for case in OBJECT_CASES],
)
def test_foreign_object_is_indistinguishable_from_missing(tenants, name, method, path, payload):
    foreign = tenants["foreign"]
    before = _snapshot(foreign)
    response = _call(
        tenants["client"], method, path(foreign), payload(foreign) if payload else None
    )
    assert response.status_code == 404
    body = response.json()
    assert {k: body[k] for k in NOT_FOUND} == NOT_FOUND
    missing = path(foreign)
    for value in (
        foreign["item"].id,
        foreign["person"].id,
        foreign["account"].id,
        foreign["membership"].id,
        foreign["grant"].id,
        foreign["unit"].id,
        foreign["location"].id,
        foreign["type"].id,
        foreign["movement"].id,
    ):
        missing = missing.replace(str(value), str(uuid.uuid4()))
    random = _call(tenants["client"], method, missing, payload(foreign) if payload else None)
    assert random.status_code == 404
    assert {k: random.json()[k] for k in NOT_FOUND} == NOT_FOUND
    assert _snapshot(foreign) == before


@pytest.mark.django_db
def test_listings_and_search_never_return_foreign_rows(tenants):
    client, foreign = tenants["client"], tenants["foreign"]
    foreign_ids = {
        str(foreign[key].id) for key in ("item", "person", "unit", "type", "role", "movement")
    }
    for path in (
        "items/",
        "items/?limit=500",
        f"items/?holder={foreign['person'].id}",
        "people/",
        "people/?q=Pessoa",
        "people/?q=MAT-B",
        "units/",
        "equipment-types/",
        "roles/",
        "search/?q=SER",
        "search/?q=Pessoa",
        "search/?q=MAT",
        "activity/",
        f"activity/?item={foreign['item'].id}",
        f"activity/?person={foreign['person'].id}",
        "audit/",
        f"audit/?object_id={foreign['movement'].id}",
    ):
        body = client.get(f"/api/v1/{path}").content.decode()
        assert not any(foreign_id in body for foreign_id in foreign_ids), path
        assert "SER-B" not in body and "MAT-B" not in body, path


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path, payload, field",
    [
        (
            "items/",
            lambda o, f: {
                "equipment_type_id": str(f["type"].id),
                "unit_id": str(o["unit"].id),
                "storage_location_id": str(o["location"].id),
                "serial_number": "X-1",
                "confirmed": True,
            },
            "equipment_type_id",
        ),
        (
            "items/",
            lambda o, f: {
                "equipment_type_id": str(o["type"].id),
                "unit_id": str(f["unit"].id),
                "storage_location_id": str(f["location"].id),
                "serial_number": "X-2",
                "confirmed": True,
            },
            "unit_id",
        ),
        (
            "items/",
            lambda o, f: {
                "equipment_type_id": str(o["type"].id),
                "unit_id": str(o["unit"].id),
                "storage_location_id": str(f["location"].id),
                "serial_number": "X-3",
                "confirmed": True,
            },
            "storage_location_id",
        ),
        (
            "people/{own_person}/memberships/",
            lambda o, f: {"registration": "MAT-Z", "main_unit_id": str(f["unit"].id)},
            "main_unit_id",
        ),
        (
            "accounts/{own_account}/grants/",
            lambda o, f: {
                "role_id": str(f["role"].id),
                "scope_type": "organization",
                "reason": "x",
            },
            "role_id",
        ),
        (
            "accounts/{own_account}/grants/",
            lambda o, f: {
                "role_id": str(o["role"].id),
                "scope_type": "unit",
                "unit_id": str(f["unit"].id),
                "reason": "x",
            },
            "unit_id",
        ),
    ],
    ids=[
        "item-foreign-type",
        "item-foreign-unit",
        "item-foreign-location",
        "membership-foreign-unit",
        "grant-foreign-role",
        "grant-foreign-unit",
    ],
)
def test_creation_with_foreign_reference_fails(tenants, path, payload, field):
    own, foreign = tenants["own"], tenants["foreign"]
    before = _snapshot(foreign)
    url = path.format(own_person=own["person"].id, own_account=own["account"].id)
    response = _call(tenants["client"], "post", url, payload(own, foreign))
    assert response.status_code == 400
    assert field in response.json()["details"]
    assert str(foreign["unit"].code) not in response.content.decode()
    assert _snapshot(foreign) == before


@pytest.mark.django_db
def test_checkout_to_foreign_person_fails(tenants):
    own, foreign = tenants["own"], tenants["foreign"]
    response = _call(
        tenants["client"],
        "post",
        f"items/{own['item'].id}/checkout/",
        {"recipient_id": str(foreign["person"].id), "idempotency_key": _key(), "confirmed": True},
    )
    assert response.status_code == 400
    assert "Pessoa B" not in response.content.decode()
    assert Item.objects.get(pk=own["item"].pk).availability == "available"


def test_every_api_route_has_an_isolation_case():
    names = {pattern.name for pattern in api_urls.urlpatterns if isinstance(pattern, URLPattern)}
    covered = {case[0] for case in OBJECT_CASES} | COLLECTION_CASES | TENANT_FREE
    assert names - covered == set(), "Nova rota sem caso de isolamento em test_isolation.py"
