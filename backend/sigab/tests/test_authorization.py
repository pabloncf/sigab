import json
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone

from sigab.models import Account, AuditEvent, Grant, Organization, Role, Unit
from sigab.permissions import (
    AUDIT_EXPORT,
    CATALOG_MANAGE,
    IDENTITY_MANAGE,
    ITEM_VIEW,
    MOVEMENT_CHECKOUT,
    MOVEMENT_RETURN,
    has_permission,
)
from sigab.roles import ROLE_TEMPLATES
from sigab.tests.legacy_organizations import legacy_organization

MATRIX = Path(__file__).resolve().parents[3] / "docs/decisoes/0002-papeis-e-escopos.json"
PASSWORD = "Senha-forte-123"


def _role(organization, permissions, name=None, scopes=("organization", "unit")):
    return Role.objects.create(
        organization=organization,
        name=name or f"Papel {uuid.uuid4().hex[:6]}",
        permissions=list(permissions),
        allowed_scopes=list(scopes),
    )


def _grant(account, role, unit=None, **extra):
    return Grant.objects.create(
        organization=account.organization,
        account=account,
        role=role,
        scope_type="unit" if unit else "organization",
        unit=unit,
        **extra,
    )


@pytest.fixture
def scoped(api_world):
    organization = api_world["organization"]
    other_unit = Unit.objects.create(organization=organization, name="Unidade B", code="U-B")
    account = Account.objects.create_user(
        username="sem-concessao", password=PASSWORD, organization=organization
    )
    return {**api_world, "other_unit": other_unit, "subject": account}


def test_role_templates_match_approved_matrix():
    matrix = json.loads(MATRIX.read_text())
    tenant_roles = {
        role["key"]: role
        for role in matrix["roles"]
        if set(role["allowed_scopes"]) <= {"organization", "unit"}
    }
    assert {t["key"] for t in ROLE_TEMPLATES} == set(tenant_roles)
    for template in ROLE_TEMPLATES:
        expected = tenant_roles[template["key"]]
        assert template["name"] == expected["name"]
        assert sorted(template["permissions"]) == sorted(expected["permissions"])
        assert sorted(template["allowed_scopes"]) == sorted(expected["allowed_scopes"])


@pytest.mark.django_db
def test_default_is_deny(scoped):
    subject = scoped["subject"]
    assert not has_permission(subject, ITEM_VIEW, scoped["organization"], scoped["unit"])


@pytest.mark.django_db
def test_unit_scope_reaches_only_its_unit(scoped):
    subject = scoped["subject"]
    _grant(subject, _role(scoped["organization"], [ITEM_VIEW]), unit=scoped["unit"])
    assert has_permission(subject, ITEM_VIEW, scoped["organization"], scoped["unit"])
    assert not has_permission(subject, ITEM_VIEW, scoped["organization"], scoped["other_unit"])
    assert not has_permission(subject, ITEM_VIEW, scoped["organization"])


@pytest.mark.django_db
def test_wider_scope_does_not_add_missing_permission(scoped):
    subject = scoped["subject"]
    _grant(subject, _role(scoped["organization"], [MOVEMENT_CHECKOUT]))
    assert has_permission(subject, MOVEMENT_CHECKOUT, scoped["organization"], scoped["unit"])
    assert not has_permission(subject, MOVEMENT_RETURN, scoped["organization"], scoped["unit"])


@pytest.mark.django_db
def test_checkout_and_return_are_separate_permissions(client, scoped):
    subject = scoped["subject"]
    _grant(subject, _role(scoped["organization"], [ITEM_VIEW, MOVEMENT_CHECKOUT]))
    client.force_login(subject)
    item_id = scoped["item"].id
    checkout = client.post(
        f"/api/v1/items/{item_id}/checkout/",
        data=json.dumps(
            {
                "recipient_id": str(scoped["person"].id),
                "idempotency_key": str(uuid.uuid4()),
                "confirmed": True,
            }
        ),
        content_type="application/json",
    )
    assert checkout.status_code == 201
    returned = client.post(
        f"/api/v1/items/{item_id}/return/",
        data=json.dumps(
            {"condition": "fit", "idempotency_key": str(uuid.uuid4()), "confirmed": True}
        ),
        content_type="application/json",
    )
    assert returned.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "extra",
    [
        {"is_active": False},
        {"revoked_at": timezone.now()},
        {"valid_from": timezone.now() + timedelta(days=1)},
        {"valid_until": timezone.now() - timedelta(minutes=1)},
    ],
    ids=["inactive", "revoked", "not-yet-valid", "expired"],
)
def test_ineffective_grants_are_ignored(scoped, extra):
    subject = scoped["subject"]
    _grant(subject, _role(scoped["organization"], [ITEM_VIEW]), **extra)
    assert not has_permission(subject, ITEM_VIEW, scoped["organization"], scoped["unit"])


@pytest.mark.django_db
def test_superuser_has_no_operational_permission_in_tenant(scoped):
    superuser = Account.objects.create_superuser(
        username="plataforma", password=PASSWORD, organization=scoped["organization"]
    )
    assert not has_permission(superuser, ITEM_VIEW, scoped["organization"], scoped["unit"])
    client = Client()
    client.force_login(superuser)
    assert client.get("/api/v1/items/").json()["data"] == []
    assert client.get(f"/api/v1/items/{scoped['item'].id}/").status_code == 404


@pytest.mark.django_db
def test_role_of_one_organization_grants_nothing_in_another(scoped):
    other = legacy_organization(name="Outra")
    foreign_role = _role(other, [ITEM_VIEW])
    with pytest.raises(ValidationError):
        Grant(
            organization=scoped["organization"],
            account=scoped["subject"],
            role=foreign_role,
            scope_type="organization",
        ).full_clean()
    outsider = Account.objects.create_user(
        username="externo", password=PASSWORD, organization=other
    )
    _grant(outsider, foreign_role)
    assert not has_permission(outsider, ITEM_VIEW, scoped["organization"], scoped["unit"])


@pytest.mark.django_db
def test_suspended_organization_denies_every_permission(scoped):
    _grant(scoped["subject"], _role(scoped["organization"], [ITEM_VIEW]))
    Organization.objects.filter(pk=scoped["organization"].pk).update(status="inactive")
    scoped["organization"].refresh_from_db()
    assert not has_permission(scoped["subject"], ITEM_VIEW, scoped["organization"])


@pytest.mark.django_db
def test_role_cannot_be_granted_outside_allowed_scope(scoped):
    role = _role(scoped["organization"], [ITEM_VIEW], scopes=["unit"])
    with pytest.raises(ValidationError):
        Grant(
            organization=scoped["organization"],
            account=scoped["subject"],
            role=role,
            scope_type="organization",
        ).full_clean()


@pytest.mark.django_db
def test_role_rejects_codes_outside_matrix(scoped):
    with pytest.raises(ValidationError):
        Role(
            organization=scoped["organization"], name="X", permissions=["movement.execute"]
        ).full_clean()


# Grant management through the API (identity.manage).


@pytest.fixture
def access_admin(scoped):
    admin = Account.objects.create_user(
        username="admin-acesso", password=PASSWORD, organization=scoped["organization"]
    )
    _grant(admin, _role(scoped["organization"], [IDENTITY_MANAGE], name="Admin acesso"))
    client = Client()
    client.force_login(admin)
    return {**scoped, "admin": admin, "client": client}


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
def test_grant_requires_reason_and_is_audited(access_admin):
    role = _role(access_admin["organization"], [ITEM_VIEW], scopes=["unit"])
    url = f"/api/v1/accounts/{access_admin['subject'].id}/grants/"
    payload = {
        "role_id": str(role.id),
        "scope_type": "unit",
        "unit_id": str(access_admin["unit"].id),
    }
    assert _post(access_admin["client"], url, payload).status_code == 400
    response = _post(access_admin["client"], url, {**payload, "reason": "Lotação na unidade A"})
    assert response.status_code == 201
    grant = Grant.objects.get(account=access_admin["subject"])
    assert grant.granted_by == access_admin["admin"]
    event = AuditEvent.objects.get(action="grant.create")
    assert event.reason == "Lotação na unidade A"

    revoke = _post(
        access_admin["client"],
        f"/api/v1/grants/{grant.id}/revoke/",
        {"confirmed": True, "reason": "Mudança de lotação"},
    )
    assert revoke.status_code == 200
    grant.refresh_from_db()
    assert grant.revoked_at is not None
    assert AuditEvent.objects.filter(action="grant.revoke").count() == 1


@pytest.mark.django_db
def test_no_self_grant(access_admin):
    role = _role(access_admin["organization"], [CATALOG_MANAGE])
    response = _post(
        access_admin["client"],
        f"/api/v1/accounts/{access_admin['admin'].id}/grants/",
        {"role_id": str(role.id), "scope_type": "organization", "reason": "Autoconcessão"},
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_independent_auditor_conflict(access_admin):
    organization = access_admin["organization"]
    auditor = _role(organization, [ITEM_VIEW, AUDIT_EXPORT], name="Auditor")
    operator = _role(organization, [MOVEMENT_CHECKOUT], name="Operador", scopes=["unit"])
    url = f"/api/v1/accounts/{access_admin['subject'].id}/grants/"
    first = _post(
        access_admin["client"],
        url,
        {
            "role_id": str(auditor.id),
            "scope_type": "unit",
            "unit_id": str(access_admin["unit"].id),
            "reason": "Auditoria",
        },
    )
    assert first.status_code == 201
    same_unit = {
        "role_id": str(operator.id),
        "scope_type": "unit",
        "unit_id": str(access_admin["unit"].id),
        "reason": "Operação",
    }
    assert _post(access_admin["client"], url, same_unit).status_code == 409
    other_unit = {**same_unit, "unit_id": str(access_admin["other_unit"].id)}
    assert _post(access_admin["client"], url, other_unit).status_code == 201


@pytest.mark.django_db
def test_grant_endpoints_hide_other_organization(access_admin):
    other = legacy_organization(name="Outra")
    outsider = Account.objects.create_user(
        username="externo", password=PASSWORD, organization=other
    )
    foreign_grant = _grant(outsider, _role(other, [ITEM_VIEW]))
    own_role = _role(access_admin["organization"], [ITEM_VIEW])
    created = _post(
        access_admin["client"],
        f"/api/v1/accounts/{outsider.id}/grants/",
        {"role_id": str(own_role.id), "scope_type": "organization", "reason": "x"},
    )
    assert created.status_code == 404
    revoked = _post(
        access_admin["client"],
        f"/api/v1/grants/{foreign_grant.id}/revoke/",
        {"confirmed": True, "reason": "x"},
    )
    assert revoked.status_code == 404
    ids = {r["id"] for r in access_admin["client"].get("/api/v1/roles/").json()["data"]}
    assert str(foreign_grant.role_id) not in ids
    assert ids == {
        str(pk)
        for pk in Role.objects.filter(organization=access_admin["organization"]).values_list(
            "pk", flat=True
        )
    }


@pytest.mark.django_db
def test_bootstrap_creates_matrix_roles_and_initial_admin():
    from django.core.management import call_command

    call_command(
        "bootstrap_sigab",
        organization="Organização Nova",
        username="admin-nova",
        email="admin@example.invalid",
        password=PASSWORD,
        verbosity=0,
    )
    account = Account.objects.get(username="admin-nova")
    organization = account.organization
    assert {r.name for r in Role.objects.filter(organization=organization)} == {
        t["name"] for t in ROLE_TEMPLATES
    }
    assert has_permission(account, IDENTITY_MANAGE, organization)
    assert has_permission(account, CATALOG_MANAGE, organization)
    # Matrix 1.5.0: the initial administrator also registers checkout and return.
    assert has_permission(account, MOVEMENT_CHECKOUT, organization)
    assert has_permission(account, MOVEMENT_RETURN, organization)
