import json
from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory
from django.utils import timezone

from sigab.domain.operations import StockRequest, checkout_basket
from sigab.domain.restrictions import change_restriction, create_restriction
from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    Item,
    Membership,
    Movement,
    Person,
    ServiceBatch,
    StockBalance,
    Unit,
)
from sigab.services import RestrictedCheckout, checkout_item, create_account, return_item
from sigab.tests.legacy_organizations import legacy_organization


def grant_manager(world):
    role = world["account"].grants.get().role
    role.permissions = [*role.permissions, "restriction.manage"]
    role.save()


def restriction(world, **overrides):
    return create_restriction(
        world["ctx"],
        **{
            "person_id": world["person"].pk,
            "category": "administrativa",
            "summary": "SIGILO-TESTE",
            "source": "Comando",
            "reference": "REF-TESTE",
            "starts_at": timezone.now() - timedelta(hours=1),
            "ends_at": None,
            "equipment_type_ids": [],
            "confirmed": True,
            **overrides,
        },
    )


@pytest.mark.django_db
def test_restriction_blocks_api_without_leaking_and_return_stays_possible(world, client):
    grant_manager(world)
    value = restriction(world)
    client.force_login(world["account"])
    payload = {
        "recipient_id": str(world["person"].pk),
        "idempotency_key": str(uuid4()),
        "confirmed": True,
    }
    before = Movement.objects.count()
    # The reserve operator loses management privilege but still has checkout rights.
    role = world["account"].grants.get().role
    role.permissions.remove("restriction.manage")
    role.save()
    for method in ("get", "post"):
        response = getattr(client, method)(
            f"/api/v1/restrictions/{value.id}/",
            data={} if method == "get" else "{}",
            content_type="application/json",
        )
        assert response.status_code == 403
    response = client.post(
        f"/api/v1/items/{world['item'].id}/checkout/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 409
    assert "SIGILO-TESTE" not in response.content.decode()
    assert "REF-TESTE" not in response.content.decode()
    assert Movement.objects.count() == before
    assert AuditEvent.objects.filter(action="restriction.blocked_checkout").exists()
    grant_manager(world)
    change_restriction(
        world["ctx"], restriction_id=value.pk, reason="Correção", confirmed=True, close=True
    )
    checkout_item(
        world["ctx"],
        item_id=world["item"].id,
        recipient_id=world["person"].id,
        idempotency_key=uuid4(),
        confirmed=True,
    )
    restriction(world)
    return_item(
        world["ctx"],
        item_id=world["item"].id,
        condition="fit",
        idempotency_key=uuid4(),
        confirmed=True,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("mode", ["future", "expired", "other_type"])
def test_restriction_window_and_equipment_scope(world, mode):
    grant_manager(world)
    other_type = EquipmentType.objects.create(
        organization=world["org"], name="Outro", classification="individual"
    )
    overrides = {
        "future": {"starts_at": timezone.now() + timedelta(days=1)},
        "expired": {"ends_at": timezone.now() - timedelta(minutes=1)},
        "other_type": {"equipment_type_ids": [other_type.pk]},
    }
    restriction(world, **overrides[mode])
    checkout_item(
        world["ctx"],
        item_id=world["item"].pk,
        recipient_id=world["person"].pk,
        idempotency_key=uuid4(),
        confirmed=True,
    )


@pytest.mark.django_db
def test_quantitative_basket_is_blocked_without_partial_delivery(world):
    grant_manager(world)
    restriction(world)
    kind = EquipmentType.objects.create(
        organization=world["org"], name="Munição", classification="quantitative"
    )
    balance = StockBalance.objects.create(
        organization=world["org"],
        equipment_type=kind,
        unit=world["unit"],
        storage_location=world["location"],
        quantity=10,
    )
    with pytest.raises(RestrictedCheckout):
        checkout_basket(
            world["ctx"],
            recipient_id=world["person"].pk,
            item_ids=[],
            stock=[StockRequest(kind.pk, world["unit"].pk, world["location"].pk, 2)],
            idempotency_key=uuid4(),
            custody_mode="indefinite",
            due_at=None,
            confirmed=True,
        )
    balance.refresh_from_db()
    assert balance.quantity == 10
    assert not ServiceBatch.objects.exists()


@pytest.mark.django_db
def test_restriction_changes_keep_history_and_audit_omits_private_text(world, client):
    grant_manager(world)
    client.force_login(world["account"])
    value = restriction(world)
    change_restriction(
        world["ctx"],
        restriction_id=value.pk,
        reason="MOTIVO-ENCERRAMENTO",
        confirmed=True,
        close=True,
    )
    assert value.history.count() == 2
    response = client.get(f"/api/v1/restrictions/{value.id}/")
    assert response.status_code == 200
    assert len(response.json()["data"]["history"]) == 2
    assert AuditEvent.objects.filter(action="restriction.viewed").exists()
    audit_text = json.dumps(
        list(
            AuditEvent.objects.filter(action__startswith="restriction.").values("changes", "reason")
        )
    )
    assert "SIGILO-TESTE" not in audit_text
    assert "MOTIVO-ENCERRAMENTO" not in audit_text


@pytest.mark.django_db
def test_login_has_no_organization_selector_and_cannot_select_legacy_client(client):
    password = "Senha-forte-123"
    accounts = []
    for index in range(2):
        org = legacy_organization(name=f"Org {index}")
        unit = Unit.objects.create(organization=org, name="Reserva", code="R")
        person = Person.objects.create(organization=org, name=f"Pessoa {index}")
        Membership.objects.create(
            organization=org, person=person, main_unit=unit, registration="MAT-IGUAL"
        )
        accounts.append(
            Account.objects.create_user(
                username=f"interno-{index}", person=person, organization=org, password=password
            )
        )
    response = client.post(
        "/entrar/",
        {
            "organization": str(accounts[1].organization_id),
            "username": "MAT-IGUAL",
            "password": password,
        },
    )
    assert response.status_code == 302
    assert client.session["_auth_user_id"] == str(accounts[0].id)
    assert not Client().login(
        username="MAT-IGUAL", password=password, organization=str(accounts[1].organization_id)
    )
    response = Client().get("/entrar/")
    assert 'name="organization"' not in response.content.decode()
    response = Client().post("/entrar/", {"username": "inexistente", "password": password})
    assert response.status_code == 200
    assert "Org 0" not in response.content.decode()


@pytest.mark.django_db
def test_admin_operational_models_are_readonly_and_platform_sees_no_tenant(world):
    request = RequestFactory().get("/admin/")
    request.user = world["account"]
    for model in (Item, Person, Grant, Account, EquipmentType):
        model_admin = admin.site._registry[model]
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
        with pytest.raises(PermissionDenied):
            model_admin.save_model(request, None, None, False)
    platform = Account.objects.create_superuser(username="platform", password="Senha-forte-123")
    client = Client()
    client.force_login(platform)
    for path in ("/admin/sigab/item/add/", f"/admin/sigab/item/{world['item'].pk}/change/"):
        assert client.post(path, {"serial_number": ""}).status_code == 403
    request.user = platform
    for model_admin in admin.site._registry.values():
        if model_admin.model._meta.app_label == "sigab":
            assert not model_admin.has_view_permission(request)
            assert not model_admin.get_queryset(request).exists()


@pytest.mark.django_db
def test_restriction_api_validates_dates_attachments_and_confirmation(world, client):
    grant_manager(world)
    client.force_login(world["account"])
    now = timezone.now()
    payload = {
        "person_id": str(world["person"].pk),
        "category": "administrativa",
        "summary": "Motivo",
        "source": "Comando",
        "starts_at": now.isoformat(),
        "equipment_type_ids": [],
        "confirmed": True,
    }
    for patch in (
        {"ends_at": (now - timedelta(seconds=1)).isoformat()},
        {"confirmed": False},
        {"category": "invalida"},
        {"equipment_type_ids": [str(uuid4())]},
        {"attachment": "documento"},
        {"starts_at": "2026-11-09T12:00:00"},
    ):
        response = client.post(
            "/api/v1/restrictions/",
            data=json.dumps({**payload, **patch}),
            content_type="application/json",
        )
        assert response.status_code == 400
    response = client.post(
        "/api/v1/restrictions/", data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 201
    pk = response.json()["data"]["id"]
    response = client.post(
        f"/api/v1/restrictions/{pk}/",
        data=json.dumps(
            {
                **payload,
                "action": "change",
                "reason": "Fim definido",
                "ends_at": (now + timedelta(days=1)).isoformat(),
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["history"]) == 2


@pytest.mark.django_db
def test_new_accounts_allow_same_requested_username_across_tenants(world):
    role = world["account"].grants.get().role
    role.permissions = [*role.permissions, "identity.manage"]
    role.save()
    other = legacy_organization(name="Outro cliente")
    Account.objects.create_user(
        username="matricula-repetida", password="Senha-forte-123", organization=other
    )
    account = create_account(
        world["ctx"],
        person_id=world["person"].pk,
        username="matricula-repetida",
        password="Senha-forte-123",
    )
    assert account.person == world["person"]
    assert Client().login(
        organization=str(world["org"].pk), username="MAT-1", password="Senha-forte-123"
    )


@pytest.mark.django_db
def test_person_login_is_throttled(world):
    from sigab.authentication import USERNAME_FAILURE_LIMIT

    world["account"].person = world["person"]
    world["account"].save()
    client = Client()
    credentials = {"organization": str(world["org"].pk), "username": "MAT-1"}
    for _ in range(USERNAME_FAILURE_LIMIT):
        assert client.post("/entrar/", {**credentials, "password": "incorreta"}).status_code == 200
    assert (
        client.post("/entrar/", {**credentials, "password": "Senha-forte-123"}).status_code == 200
    )
    assert "_auth_user_id" not in client.session
