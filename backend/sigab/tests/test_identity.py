import json
import uuid

import pytest
from django.test import Client

from sigab.models import (
    Account,
    AuditEvent,
    Grant,
    Membership,
    Movement,
    Person,
    Role,
    Unit,
)
from sigab.permissions import MANAGE_IDENTITY, MOVEMENT_CHECKOUT, VIEW_ITEM
from sigab.tests.legacy_organizations import legacy_organization

PASSWORD = "Senha-forte-123"


def synthetic_cpf(base):
    """Build a valid CPF from nine synthetic digits."""
    digits = [int(d) for d in base]
    for size in (9, 10):
        total = sum(d * (size + 1 - i) for i, d in enumerate(digits[:size]))
        digits.append(total * 10 % 11 % 10)
    return "".join(map(str, digits))


CPF_A = synthetic_cpf("123456789")
CPF_B = synthetic_cpf("987654321")


def _json(client, method, url, payload=None):
    return getattr(client, method)(
        url, data=json.dumps(payload or {}), content_type="application/json"
    )


@pytest.fixture
def identity(api_world):
    organization = api_world["organization"]
    manager = Account.objects.create_user(
        username="gestor-acesso", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(
        organization=organization, name="Gestor de acesso", permissions=[MANAGE_IDENTITY]
    )
    Grant.objects.create(
        organization=organization,
        account=manager,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
    )
    client = Client()
    client.force_login(manager)
    return {**api_world, "manager": manager, "client": client}


def _create_person(client, **fields):
    response = _json(client, "post", "/api/v1/people/", {"name": "Pessoa Sintética", **fields})
    assert response.status_code == 201, response.json()
    return response.json()["data"]


def _add_membership(identity, person_id, registration="MAT-100"):
    return _json(
        identity["client"],
        "post",
        f"/api/v1/people/{person_id}/memberships/",
        {"registration": registration, "main_unit_id": str(identity["unit"].id)},
    )


def _create_account(identity, person_id, username="pessoa.sintetica"):
    return _json(
        identity["client"],
        "post",
        f"/api/v1/people/{person_id}/account/",
        {"username": username, "password": PASSWORD},
    )


# SIGAB-019: person and membership


@pytest.mark.django_db
def test_person_is_created_without_account(identity):
    data = _create_person(identity["client"], cpf="123.456.789-09")
    assert data["accounts"] == []
    assert not Account.objects.filter(person_id=data["id"]).exists()
    assert data["cpf_masked"] == "***.***.***-09"
    assert "cpf" not in data
    audit = AuditEvent.objects.get(action="person.create", object_id=data["id"])
    assert CPF_A not in json.dumps(audit.changes)
    assert audit.changes == {"fields": ["name", "cpf"]}


@pytest.mark.django_db
def test_invalid_cpf_is_rejected_without_echo(identity):
    response = _json(
        identity["client"], "post", "/api/v1/people/", {"name": "X", "cpf": "12345678900"}
    )
    assert response.status_code == 400
    assert response.json()["details"] == {"cpf": ["CPF inválido."]}
    assert "12345678900" not in response.content.decode()


@pytest.mark.django_db
def test_cpf_is_unique_per_organization(identity):
    _create_person(identity["client"], cpf=CPF_B)
    duplicate = _json(
        identity["client"], "post", "/api/v1/people/", {"name": "Outra", "cpf": CPF_B}
    )
    assert duplicate.status_code == 400
    other = legacy_organization(name="Outra organização")
    Person(organization=other, name="Mesma pessoa em outro órgão", cpf=CPF_B).full_clean()


@pytest.mark.django_db
def test_registration_is_unique_per_organization(identity):
    person = _create_person(identity["client"])
    assert _add_membership(identity, person["id"], "MAT-1").status_code == 201
    second = _create_person(identity["client"], name="Segunda")
    duplicate = _add_membership(identity, second["id"], "MAT-1")
    assert duplicate.status_code == 400
    assert duplicate.json()["details"] == {
        "non_field_errors": ["Matrícula já cadastrada nesta organização."]
    }
    other = legacy_organization(name="Outra organização")
    other_unit = Unit.objects.create(organization=other, name="U", code="U")
    other_person = Person.objects.create(organization=other, name="P")
    Membership(
        organization=other, person=other_person, registration="MAT-1", main_unit=other_unit
    ).full_clean()


@pytest.mark.django_db
def test_membership_rejects_unit_from_other_organization(identity):
    person = _create_person(identity["client"])
    other = legacy_organization(name="Outra organização")
    foreign_unit = Unit.objects.create(organization=other, name="U", code="U-X")
    response = _json(
        identity["client"],
        "post",
        f"/api/v1/people/{person['id']}/memberships/",
        {"registration": "MAT-9", "main_unit_id": str(foreign_unit.id)},
    )
    assert response.status_code == 400
    assert response.json()["details"] == {"main_unit_id": ["Unidade inválida."]}


@pytest.mark.django_db
def test_deactivation_preserves_history_and_blocks_new_checkout(identity, client):
    holder = identity["person"]
    client.force_login(identity["account"])
    checkout = _json(
        client,
        "post",
        f"/api/v1/items/{identity['item'].id}/checkout/",
        {
            "recipient_id": str(holder.id),
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": True,
        },
    )
    assert checkout.status_code == 201
    movements_before = Movement.objects.filter(recipient=holder).count()

    response = _json(
        identity["client"],
        "post",
        f"/api/v1/people/{holder.id}/status/",
        {"is_active": False, "confirmed": True, "reason": "Desligamento sintético"},
    )
    assert response.status_code == 200
    holder.refresh_from_db()
    assert holder.is_active is False
    assert holder.memberships.filter(is_active=True).count() == 1
    assert Movement.objects.filter(recipient=holder).count() == movements_before

    returned = _json(
        client,
        "post",
        f"/api/v1/items/{identity['item'].id}/return/",
        {"condition": "fit", "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    )
    assert returned.status_code == 201
    again = _json(
        client,
        "post",
        f"/api/v1/items/{identity['item'].id}/checkout/",
        {
            "recipient_id": str(holder.id),
            "idempotency_key": str(uuid.uuid4()),
            "confirmed": True,
        },
    )
    assert again.status_code == 400


@pytest.mark.django_db
def test_status_change_requires_confirmation(identity):
    person = _create_person(identity["client"])
    response = _json(
        identity["client"], "post", f"/api/v1/people/{person['id']}/status/", {"is_active": False}
    )
    assert response.status_code == 400
    assert Person.objects.get(pk=person["id"]).is_active is True


@pytest.mark.django_db
def test_person_update_audits_field_names_only(identity):
    person = _create_person(identity["client"])
    response = _json(
        identity["client"],
        "patch",
        f"/api/v1/people/{person['id']}/",
        {"functional_name": "Sintético", "cpf": CPF_A},
    )
    assert response.status_code == 200
    audit = AuditEvent.objects.get(action="person.update", object_id=person["id"])
    assert audit.changes == {"fields": ["cpf", "functional_name"]}
    rejected = _json(
        identity["client"], "patch", f"/api/v1/people/{person['id']}/", {"is_active": False}
    )
    assert rejected.status_code == 400


@pytest.mark.django_db
def test_identity_requires_manage_permission(client, api_world):
    client.force_login(api_world["account"])
    assert client.get("/api/v1/people/").status_code == 403
    assert _json(client, "post", "/api/v1/people/", {"name": "X"}).status_code == 403
    assert client.get(f"/api/v1/people/{api_world['person'].id}/").status_code == 403


@pytest.mark.django_db
def test_identity_endpoints_hide_other_organization(identity):
    other = legacy_organization(name="Outra organização")
    unit = Unit.objects.create(organization=other, name="U", code="U-O")
    person = Person.objects.create(organization=other, name="Pessoa externa")
    membership = Membership.objects.create(
        organization=other, person=person, registration="EXT-1", main_unit=unit
    )
    account = Account.objects.create_user(
        username="externa", password=PASSWORD, organization=other, person=person
    )
    client = identity["client"]
    confirm = {"is_active": False, "confirmed": True}
    responses = [
        client.get(f"/api/v1/people/{person.id}/"),
        _json(client, "patch", f"/api/v1/people/{person.id}/", {"name": "Alterado"}),
        _json(client, "post", f"/api/v1/people/{person.id}/status/", confirm),
        _add_membership(identity, person.id),
        _create_account(identity, person.id),
        _json(client, "post", f"/api/v1/memberships/{membership.id}/status/", confirm),
        _json(client, "post", f"/api/v1/accounts/{account.id}/suspend/", {"confirmed": True}),
    ]
    assert [r.status_code for r in responses] == [404] * len(responses)
    assert [r.json()["error"] for r in responses] == ["Recurso não encontrado."] * len(responses)
    ids = [row["id"] for row in client.get("/api/v1/people/").json()["data"]]
    assert str(person.id) not in ids
    account.refresh_from_db()
    assert account.is_active is True


# SIGAB-020: account


@pytest.mark.django_db
def test_account_is_created_for_person_and_can_log_in(identity):
    person = _create_person(identity["client"])
    _add_membership(identity, person["id"])
    response = _create_account(identity, person["id"])
    assert response.status_code == 201
    account = response.json()["data"]["accounts"][0]
    assert account["status"] == "active"
    assert PASSWORD not in response.content.decode()
    assert Client().login(
        username="MAT-100", organization=str(identity["organization"].id), password=PASSWORD
    )
    audit = AuditEvent.objects.get(action="account.create")
    assert PASSWORD not in json.dumps(audit.changes)


@pytest.mark.django_db
def test_account_creation_validates_password_and_duplicates(identity):
    person = _create_person(identity["client"])
    weak = _json(
        identity["client"],
        "post",
        f"/api/v1/people/{person['id']}/account/",
        {"username": "fraca", "password": "123"},
    )
    assert weak.status_code == 400
    assert "password" in weak.json()["details"]
    assert _create_account(identity, person["id"]).status_code == 201
    assert _create_account(identity, person["id"], "outro").status_code == 409
    other_person = _create_person(identity["client"], name="Outra")
    taken = _create_account(identity, other_person["id"], "pessoa.sintetica")
    assert taken.status_code == 400
    assert taken.json()["details"] == {"username": ["Identificador de login indisponível."]}


@pytest.mark.django_db
def test_suspension_blocks_login_without_touching_person_or_history(identity):
    person = _create_person(identity["client"])
    _add_membership(identity, person["id"])
    account_id = _create_account(identity, person["id"]).json()["data"]["accounts"][0]["id"]
    session = Client()
    assert session.login(
        username="MAT-100", organization=str(identity["organization"].id), password=PASSWORD
    )
    person_before = Person.objects.filter(pk=person["id"]).values().get()
    memberships_before = list(Membership.objects.filter(person_id=person["id"]).values())

    response = _json(
        identity["client"],
        "post",
        f"/api/v1/accounts/{account_id}/suspend/",
        {"confirmed": True, "reason": "Afastamento sintético"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["accounts"][0]["status"] == "suspended"
    assert session.get("/api/v1/session/").status_code == 401
    assert not Client().login(username="pessoa.sintetica", password=PASSWORD)
    assert Person.objects.filter(pk=person["id"]).values().get() == person_before
    assert list(Membership.objects.filter(person_id=person["id"]).values()) == memberships_before
    suspension = AuditEvent.objects.get(action="account.suspend")
    assert suspension.changes == {"status": {"from": "active", "to": "suspended"}}
    assert (
        AuditEvent.objects.filter(occurred_at__gte=suspension.occurred_at)
        .exclude(action__in=["account.suspend", "auth.login"])
        .count()
        == 0
    )

    reactivated = _json(
        identity["client"],
        "post",
        f"/api/v1/accounts/{account_id}/reactivate/",
        {"confirmed": True},
    )
    assert reactivated.status_code == 200
    assert Client().login(
        username="MAT-100", organization=str(identity["organization"].id), password=PASSWORD
    )


@pytest.mark.django_db
def test_revocation_is_final_and_allows_new_account(identity):
    person = _create_person(identity["client"])
    account_id = _create_account(identity, person["id"]).json()["data"]["accounts"][0]["id"]
    account = Account.objects.get(pk=account_id)
    role = Role.objects.create(
        organization=identity["organization"], name="Operador 2", permissions=[MOVEMENT_CHECKOUT]
    )
    grant = Grant.objects.create(
        organization=identity["organization"],
        account=account,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
    )
    response = _json(
        identity["client"],
        "post",
        f"/api/v1/accounts/{account_id}/revoke/",
        {"confirmed": True, "reason": "Desligamento sintético"},
    )
    assert response.status_code == 200
    account.refresh_from_db()
    grant.refresh_from_db()
    assert account.status == "revoked"
    assert not account.has_usable_password()
    assert grant.is_active is False and grant.revoked_at is not None
    reactivate = _json(
        identity["client"],
        "post",
        f"/api/v1/accounts/{account_id}/reactivate/",
        {"confirmed": True},
    )
    assert reactivate.status_code == 409
    assert _create_account(identity, person["id"], "pessoa.nova").status_code == 201
    assert Account.objects.filter(person_id=person["id"]).count() == 2


@pytest.mark.django_db
def test_manager_cannot_change_own_account_or_platform_accounts(identity):
    own = _json(
        identity["client"],
        "post",
        f"/api/v1/accounts/{identity['manager'].id}/suspend/",
        {"confirmed": True},
    )
    assert own.status_code == 409
    superuser = Account.objects.create_superuser(
        username="plataforma",
        password=PASSWORD,
        organization=identity["organization"],
    )
    platform = _json(
        identity["client"], "post", f"/api/v1/accounts/{superuser.id}/revoke/", {"confirmed": True}
    )
    assert platform.status_code == 404


@pytest.mark.django_db
def test_session_reports_identity_permission(identity, client, api_world):
    assert (
        identity["client"]
        .get("/api/v1/session/")
        .json()["data"]["permissions"]["can_manage_identity"]
        is True
    )
    client.force_login(api_world["account"])
    assert (
        client.get("/api/v1/session/").json()["data"]["permissions"]["can_manage_identity"] is False
    )


@pytest.mark.django_db
def test_session_names_item_scope(client, api_world):
    """The UI names the consulted units instead of a vague "your scope"."""
    client.force_login(api_world["account"])
    scope = client.get("/api/v1/session/").json()["data"]["item_scope"]
    assert scope == {"all_units": True, "units": []}

    organization = api_world["organization"]
    other = Unit.objects.create(organization=organization, name="Unidade Fora", code="U-FORA")
    account = Account.objects.create_user(
        username="leitor-unidade", password="Senha-forte-123", organization=organization
    )
    role = Role.objects.create(organization=organization, name="Leitor", permissions=[VIEW_ITEM])
    Grant.objects.create(
        organization=organization,
        account=account,
        role=role,
        scope_type=Grant.Scope.UNIT,
        unit=api_world["unit"],
        granted_by=api_world["account"],
    )
    client.force_login(account)
    scope = client.get("/api/v1/session/").json()["data"]["item_scope"]
    assert scope["all_units"] is False
    assert [unit["code"] for unit in scope["units"]] == ["U-API"]
    assert str(other.id) not in {unit["id"] for unit in scope["units"]}


@pytest.mark.django_db
def test_unit_list_requires_identity_permission(identity, client, api_world):
    assert identity["client"].get("/api/v1/units/").status_code == 200
    client.force_login(api_world["account"])
    assert client.get("/api/v1/units/").status_code == 403
