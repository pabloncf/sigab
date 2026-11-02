import json

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import Client

from sigab.authentication import USERNAME_FAILURE_LIMIT, username_digest
from sigab.models import Account, AuditEvent, AuthenticationFailure, Organization

PASSWORD = "Senha-forte-123"


def _login(client, username, password, ip="10.0.0.1"):
    return client.post("/entrar/", {"username": username, "password": password}, REMOTE_ADDR=ip)


def _logged_in(client):
    return client.get("/api/v1/session/").status_code == 200


@pytest.mark.django_db
def test_password_is_stored_only_as_hash(api_world):
    account = api_world["account"]
    assert PASSWORD not in account.password
    assert account.password.startswith("pbkdf2_sha256$")
    assert account.check_password(PASSWORD)


@pytest.mark.django_db
def test_login_success_is_audited_and_sets_session(client, api_world):
    response = _login(client, "operador-api", PASSWORD)
    assert response.status_code == 302
    assert _logged_in(client)
    event = AuditEvent.objects.get(action="auth.login", result="success")
    assert event.actor == api_world["account"]
    assert event.organization == api_world["organization"]


@pytest.mark.django_db
def test_login_failure_is_audited_without_secrets(client, api_world):
    response = _login(client, "operador-api", "Senha-errada-999")
    assert response.status_code == 200
    assert not _logged_in(client)
    _login(client, "usuario-inexistente", "Senha-errada-999")
    failures = AuditEvent.objects.filter(action="auth.login", result="failure")
    assert failures.count() == 2
    rendered = json.dumps([[f.object_id, f.changes, f.reason] for f in failures])
    assert "Senha-errada-999" not in rendered
    assert "usuario-inexistente" not in rendered
    stored = AuthenticationFailure.objects.values_list("username_digest", flat=True)
    assert "usuario-inexistente" not in "".join(stored)


@pytest.mark.django_db
def test_login_is_throttled_after_repeated_failures(client, api_world):
    for _ in range(USERNAME_FAILURE_LIMIT):
        _login(client, "operador-api", "Senha-errada-999")
    # Even the right password is refused while throttled, with the generic message.
    response = _login(client, "operador-api", PASSWORD)
    assert response.status_code == 200
    assert not _logged_in(client)
    assert Client().login(username="operador-api", password=PASSWORD) is False


@pytest.mark.django_db
def test_throttle_by_ip_covers_many_usernames(client, api_world):
    for index in range(20):
        _login(client, f"tentativa-{index}", "x", ip="10.9.9.9")
    assert not _logged_in(client)
    response = _login(client, "operador-api", PASSWORD, ip="10.9.9.9")
    assert response.status_code == 200
    assert not _logged_in(client)
    other_ip = Client()
    _login(other_ip, "operador-api", PASSWORD, ip="10.1.1.1")
    assert _logged_in(other_ip)


@pytest.mark.django_db
def test_success_clears_username_failures(client, api_world):
    for _ in range(USERNAME_FAILURE_LIMIT - 1):
        _login(client, "operador-api", "Senha-errada-999")
    _login(client, "operador-api", PASSWORD)
    assert not AuthenticationFailure.objects.filter(
        username_digest=username_digest("operador-api")
    ).exists()


def test_session_expires_and_cookies_are_protected():
    assert settings.SESSION_COOKIE_AGE == 8 * 60 * 60
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"


@pytest.mark.django_db
def test_end_sessions_revokes_open_sessions(client, api_world):
    from sigab.models import Grant, Role
    from sigab.permissions import MANAGE_IDENTITY

    organization = api_world["organization"]
    manager = Account.objects.create_user(
        username="gestor", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(
        organization=organization,
        name="Acesso",
        permissions=[MANAGE_IDENTITY],
        allowed_scopes=["organization"],
    )
    Grant.objects.create(
        organization=organization, account=manager, role=role, scope_type="organization"
    )
    _login(client, "operador-api", PASSWORD)
    assert _logged_in(client)
    admin = Client()
    admin.force_login(manager)
    response = admin.post(
        f"/api/v1/accounts/{api_world['account'].id}/end-sessions/",
        data=json.dumps({"confirmed": True, "reason": "Sessão em equipamento perdido"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert not _logged_in(client)
    api_world["account"].refresh_from_db()
    assert api_world["account"].is_active is True
    assert AuditEvent.objects.filter(action="account.end_sessions").count() == 1


@pytest.mark.django_db
def test_session_without_version_is_ended(client, api_world):
    client.force_login(api_world["account"])
    session = client.session
    del session["sigab_session_version"]
    session.save()
    assert not _logged_in(client)


@pytest.mark.django_db
def test_suspended_organization_cannot_log_in_and_loses_sessions(client, api_world):
    client.force_login(api_world["account"])
    assert _logged_in(client)
    organization = api_world["organization"]
    call_command(
        "set_organization_status",
        organization_id=str(organization.id),
        status=Organization.Status.INACTIVE,
        reason="Contrato encerrado (sintético)",
        verbosity=0,
    )
    assert not _logged_in(client)
    assert Client().login(username="operador-api", password=PASSWORD) is False
    event = AuditEvent.objects.get(action="organization.status_change")
    assert event.changes == {"status": {"from": "active", "to": "inactive"}}
    assert event.reason
