from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from sigab.models import Organization

pytestmark = pytest.mark.django_db


def test_database_rejects_second_customer_and_bypassing_the_singleton_key(world):
    with pytest.raises(IntegrityError), transaction.atomic():
        Organization.objects.create(name="Segundo cliente")
    with pytest.raises(IntegrityError), transaction.atomic():
        Organization.objects.bulk_create([Organization(name="Outro", installation_key=2)])
    assert Organization.objects.get().id == world["org"].id


def test_bootstrap_and_demo_cannot_add_a_customer_to_initialized_installation(world, settings):
    with pytest.raises(CommandError, match="já possui uma organização"):
        call_command(
            "bootstrap_sigab",
            organization="Outra",
            username="outro",
            email="outro@example.invalid",
            password="Senha-forte-123",
        )
    settings.DEBUG = True
    with pytest.raises(CommandError, match="já possui organização"):
        call_command("seed_demo")
    assert Organization.objects.count() == 1


def test_login_uses_local_registration_without_organization_and_keeps_throttling(world, client):
    from sigab.authentication import USERNAME_FAILURE_LIMIT

    world["account"].person = world["person"]
    world["account"].save()
    page = client.get("/entrar/").content.decode()
    assert 'name="organization"' not in page
    assert (
        client.post("/entrar/", {"username": "MAT-1", "password": "Senha-forte-123"}).status_code
        == 302
    )
    assert client.session["_auth_user_id"] == str(world["account"].id)
    anonymous = Client()
    for index in range(USERNAME_FAILURE_LIMIT):
        anonymous.post(
            "/entrar/", {"username": "MAT-1", "password": "errada", "organization": f"fake-{index}"}
        )
    assert (
        anonymous.post("/entrar/", {"username": "MAT-1", "password": "Senha-forte-123"}).status_code
        == 200
    )
    assert "_auth_user_id" not in anonymous.session


def test_status_command_defaults_to_local_organization(world):
    call_command(
        "set_organization_status", status="inactive", reason="Manutenção", stdout=StringIO()
    )
    world["org"].refresh_from_db()
    assert world["org"].status == "inactive"


@pytest.mark.django_db(transaction=True)
def test_single_tenant_migration_refuses_legacy_database_without_removing_data():
    previous = [("sigab", "0011_unique_open_inventory")]
    current = [("sigab", "0012_single_tenant_installation")]
    executor = MigrationExecutor(connection)
    executor.migrate(previous)
    historical_org = executor.loader.project_state(previous).apps.get_model("sigab", "Organization")
    first = historical_org.objects.create(name="Cliente A")
    second = historical_org.objects.create(name="Cliente B")
    try:
        with pytest.raises(RuntimeError, match="Separe os clientes"):
            MigrationExecutor(connection).migrate(current)
        assert historical_org.objects.count() == 2
        assert historical_org.objects.get(pk=first.id).name == "Cliente A"
    finally:
        # Only this synthetic, unreferenced row is removed to restore the test schema.
        historical_org.objects.filter(pk=second.id).delete()
        MigrationExecutor(connection).migrate(current)
    assert Organization.objects.get().id == first.id
    assert Organization.objects.get().installation_key == 1
