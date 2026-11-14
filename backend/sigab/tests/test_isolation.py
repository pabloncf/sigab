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
from django.utils import timezone

from sigab.api import urls as api_urls
from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    InventoryCount,
    InventoryDivergence,
    InventorySession,
    Item,
    Membership,
    Movement,
    Person,
    PersonRestriction,
    Role,
    ServiceBatch,
    StockBalance,
    StockLedgerEntry,
    StockLoan,
    StorageLocation,
    Unit,
)
from sigab.permissions import AUDIT_EXPORT, TENANT_PERMISSIONS
from sigab.services import CommandContext, checkout_item
from sigab.tests.legacy_organizations import legacy_organization

PASSWORD = "Senha-forte-123"
NOT_FOUND = {"success": False, "error": "Recurso não encontrado."}


def _tenant(name, code, with_movement=False):
    organization = legacy_organization(name=name)
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
        # The counter never serves its own operator: another account registers the checkout.
        operator = Account.objects.create_user(
            username=f"operador-{code}", password=PASSWORD, organization=organization
        )
        Grant.objects.create(
            organization=organization, account=operator, role=role, scope_type="organization"
        )
        movement, _ = checkout_item(
            CommandContext(operator, organization, f"setup-{code}"),
            item_id=item.id,
            recipient_id=person.id,
            idempotency_key=uuid.uuid4(),
            confirmed=True,
        )
    quantitative_type = EquipmentType.objects.create(
        organization=organization, name=f"Munição {code}", classification="quantitative"
    )
    balance = StockBalance.objects.create(
        organization=organization,
        equipment_type=quantitative_type,
        unit=unit,
        storage_location=location,
        quantity=10,
    )
    batch = ServiceBatch.objects.create(
        organization=organization,
        recipient=person,
        operator=account,
        custody_mode=ServiceBatch.CustodyMode.INDEFINITE,
        idempotency_key=uuid.uuid4(),
        request_hash="0" * 64,
        confirmed_at=timezone.now(),
        receipt_code=f"AT-{code}",
    )
    loan = StockLoan.objects.create(
        organization=organization,
        batch=batch,
        balance=balance,
        recipient=person,
        original_quantity=2,
        open_quantity=2,
    )
    stock_entry = StockLedgerEntry.objects.create(
        organization=organization,
        balance=balance,
        loan=loan,
        entry_type=StockLedgerEntry.Type.CHECKOUT,
        quantity=2,
        balance_delta=-2,
        operator=account,
        recipient=person,
        idempotency_key=uuid.uuid4(),
        occurred_at=timezone.now(),
    )
    inventory = InventorySession.objects.create(
        organization=organization,
        unit=unit,
        opened_by=account,
        opened_at=timezone.now(),
        reference_at=timezone.now(),
    )
    count = InventoryCount.objects.create(
        session=inventory,
        item=item,
        expected_state=item.availability,
        counted_state="missing",
        counted_at=timezone.now(),
        counted_by=account,
    )
    divergence = InventoryDivergence.objects.create(
        session=inventory,
        count=count,
        expected_state=item.availability,
        counted_state="missing",
    )
    restriction = PersonRestriction.objects.create(
        organization=organization,
        person=person,
        category="administrativa",
        summary=f"Privado {code}",
        source="Comando",
        starts_at=timezone.now(),
        created_by=account,
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
        "batch": batch,
        "balance": balance,
        "loan": loan,
        "stock_entry": stock_entry,
        "inventory": inventory,
        "divergence": divergence,
        "restriction": restriction,
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
        "loan": StockLoan.objects.filter(pk=foreign["loan"].pk).values().get(),
        "inventory": InventorySession.objects.filter(pk=foreign["inventory"].pk).values().get(),
        "divergence": InventoryDivergence.objects.filter(pk=foreign["divergence"].pk)
        .values()
        .get(),
        "stock_entries": StockLedgerEntry.objects.filter(
            organization=foreign["organization"]
        ).count(),
    }


def _key():
    return str(uuid.uuid4())


# (route name, method, path builder, payload builder). Paths use the FOREIGN tenant ids.
OBJECT_CASES = [
    ("restriction-detail", "get", lambda f: f"restrictions/{f['restriction'].id}/", None),
    (
        "restriction-detail",
        "post",
        lambda f: f"restrictions/{f['restriction'].id}/",
        lambda f: {"action": "close", "reason": "x", "confirmed": True},
    ),
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
    (
        "stock-loan-settle",
        "post",
        lambda f: f"stock/loans/{f['loan'].id}/settle/",
        lambda f: {
            "quantity": "1",
            "disposition": "return",
            "idempotency_key": _key(),
            "confirmed": True,
        },
    ),
    (
        "stock-entry-reverse",
        "post",
        lambda f: f"stock/entries/{f['stock_entry'].id}/reverse/",
        lambda f: {"idempotency_key": _key(), "confirmed": True, "reason": "x"},
    ),
    ("inventory-detail", "get", lambda f: f"inventory/sessions/{f['inventory'].id}/", None),
    (
        "inventory-count",
        "post",
        lambda f: f"inventory/sessions/{f['inventory'].id}/count/",
        lambda f: {"item_id": str(f["item"].id), "counted_state": "missing"},
    ),
    (
        "inventory-close",
        "post",
        lambda f: f"inventory/sessions/{f['inventory'].id}/close/",
        lambda f: {},
    ),
    (
        "divergence-update",
        "post",
        lambda f: f"inventory/divergences/{f['divergence'].id}/",
        lambda f: {"status": "investigating"},
    ),
    ("my-receipt", "get", lambda f: f"me/receipts/{f['batch'].id}/", None),
]

# Collections: listing never shows foreign rows; creation never accepts foreign references.
COLLECTION_CASES = {
    "restriction-list",
    "item-list",
    "search",
    "activity",
    "audit-trail",
    "person-list",
    "unit-list",
    "equipment-type-list",
    "role-list",
    "service-batch-create",
    "service-batch-options",
    "stock-position-list",
    "stock-options",
    "stock-loans",
    "stock-summary",
    "stock-history",
    "overview",
    "return-batch-create",
    "return-options",
    "counter-identify",
    "movement-register",
    "movement-register-options",
    "person-biometric",
    "biometric-list",
    "person-biometric-delete",
    "face-verification-create",
    "face-verification-cancel",
    "identity-exception-list",
    "identity-exception-detail",
    "identity-exception-signed",
    "identity-exception-cancel",
    "identity-exception-decision",
    "inventory-open",
    "possession-list",
    "possession-export",
}

# Routes without tenant data.
TENANT_FREE = {
    "session-detail",
    "session-logout",
    "my-possessions",
    "my-history",
    "not-found",
}


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
        foreign["batch"].id,
        foreign["loan"].id,
        foreign["stock_entry"].id,
        foreign["inventory"].id,
        foreign["divergence"].id,
        foreign["restriction"].id,
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
        "restrictions/",
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
        "service-batches/options/",
        "stock/positions/",
        "stock/options/",
        "stock/loans/",
        "possessions/",
        "possessions/export/",
        "me/possessions/",
        "me/history/",
        f"audit/?object_id={foreign['movement'].id}",
    ):
        body = client.get(f"/api/v1/{path}").content.decode()
        assert not any(foreign_id in body for foreign_id in foreign_ids), path
        assert "SER-B" not in body and "MAT-B" not in body, path


@pytest.mark.django_db
def test_home_and_unregistered_collection_never_return_foreign_rows(tenants):
    """SIGAB-079/081: aggregates, stock positions and ledger history stay in the installation."""
    client, foreign = tenants["client"], tenants["foreign"]
    loan = foreign["loan"]
    foreign_type = loan.balance.equipment_type_id
    foreign_ids = {
        str(value)
        for value in (
            foreign["item"].id,
            foreign["person"].id,
            foreign["unit"].id,
            foreign["movement"].id,
            foreign["stock_entry"].id,
            loan.id,
            loan.balance_id,
            foreign_type,
        )
    }
    for path in (
        "overview/",
        "stock/summary/",
        f"stock/summary/?type={foreign_type}",
        f"stock/summary/?unit={foreign['unit'].id}",
        "stock/entries/",
        f"stock/entries/?type={foreign_type}",
        "movements/",
        f"movements/?person={foreign['person'].id}",
        f"movements/?equipment_type={foreign_type}",
        "movements/options/",
        "return-batches/options/",
        f"return-batches/options/?person={foreign['person'].id}",
    ):
        response = client.get(f"/api/v1/{path}")
        assert response.status_code == 200, path
        body = response.content.decode()
        assert not any(foreign_id in body for foreign_id in foreign_ids), path
        assert "SER-B" not in body and str(foreign["person"]) not in body, path


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
def test_counter_identify_never_finds_foreign_registration(tenants):
    foreign = tenants["foreign"]
    response = tenants["client"].get(
        f"/api/v1/counter/identify/?registration={foreign['membership'].registration}"
    )
    assert response.status_code == 404
    assert str(foreign["person"]) not in response.content.decode()


@pytest.mark.django_db
def test_foreign_face_verification_cannot_be_cancelled(tenants):
    from datetime import timedelta

    from django.utils import timezone

    from sigab.models import FaceVerification

    foreign = tenants["foreign"]
    now = timezone.now()
    verification = FaceVerification.objects.create(
        organization=foreign["organization"],
        person=foreign["person"],
        operator=foreign["account"],
        operation="checkout",
        result="approved",
        operator_confirmed=True,
        engine_version="synthetic",
        verified_at=now,
        expires_at=now + timedelta(minutes=10),
    )
    response = _call(
        tenants["client"],
        "post",
        f"face-verifications/{verification.id}/cancel/",
        {"confirmed": True},
    )
    assert response.status_code == 404
    verification.refresh_from_db()
    assert verification.expires_at > timezone.now()


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
