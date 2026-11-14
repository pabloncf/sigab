"""SIGAB-085/086: facial enrollment, verification and the signed-term exception (ADR 0008).

All captures are synthetic byte strings handled by a deterministic test engine; no real
image or biometric data is used.
"""

import json
import logging
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from sigab.domain.operations import StockRequest, checkout_basket
from sigab.models import (
    Account,
    AuditEvent,
    BiometricTemplate,
    FaceVerification,
    Grant,
    IdentityException,
    Item,
    Membership,
    Person,
    ReturnBatch,
    Role,
    ServiceBatch,
    StockLoan,
    Unit,
)
from sigab.tests.test_requirements_063_070 import _quantitative_stock

pytestmark = [pytest.mark.django_db, pytest.mark.identity_check]


class SyntheticEngine:
    """Deterministic stand-in: a capture b"face:<who>" yields the template <who>."""

    version = "synthetic-test-1"
    threshold = 0.5

    def template(self, image):
        if not image.startswith(b"face:"):
            raise ValidationError({"image": "Nenhum rosto encontrado."})
        return image[5:]

    def similarity(self, first, second):
        return 1.0 if first == second else 0.0


@pytest.fixture(autouse=True)
def engine(settings):
    settings.SIGAB_FACE_ENGINE = "sigab.tests.test_requirements_085_086.SyntheticEngine"
    settings.SIGAB_BIOMETRIC_KEY = Fernet.generate_key().decode()


@pytest.fixture
def gestor(world):
    """Inventory administrator: approves terms and manages biometrics, never operates."""
    account = Account.objects.create_user(
        username="gestor", password="Senha-forte-123", organization=world["org"]
    )
    role = Role.objects.create(
        organization=world["org"],
        name="Gestor de acervo",
        permissions=["item.view", "biometric.manage", "movement.exception.approve"],
    )
    Grant.objects.create(
        organization=world["org"],
        account=account,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
        granted_by=world["account"],
    )
    return account


def _capture(who="pessoa"):
    return SimpleUploadedFile("captura.png", f"face:{who}".encode(), content_type="image/png")


def _enroll(client, gestor, person, who="pessoa"):
    client.force_login(gestor)
    return client.post(
        f"/api/v1/people/{person.id}/biometric/", {"image": _capture(who), "confirmed": "true"}
    )


def _verify(client, account, person, operation="checkout", who="pessoa", confirmed="true"):
    client.force_login(account)
    return client.post(
        "/api/v1/face-verifications/",
        {
            "person_id": str(person.id),
            "operation": operation,
            "operator_confirmed": confirmed,
            "image": _capture(who),
        },
    )


def _post(client, path, body):
    return client.post(f"/api/v1/{path}", json.dumps(body), content_type="application/json")


def _basket(world, verification_id=None, **extra):
    body = {
        "recipient_id": str(world["person"].id),
        "item_ids": [str(world["item"].id)],
        "stock": [],
        "custody_mode": "indefinite",
        "confirmed": True,
        "idempotency_key": str(uuid4()),
        **extra,
    }
    if verification_id:
        body["face_verification_id"] = verification_id
    return body


# SIGAB-085 — enrollment


def test_enrollment_is_encrypted_audited_without_data_and_reenrollable(
    client, world, gestor, caplog
):
    caplog.set_level(logging.DEBUG)
    response = _enroll(client, gestor, world["person"])
    assert response.status_code == 201
    assert response.json()["data"]["enrolled"] is True
    record = BiometricTemplate.objects.get(person=world["person"])
    assert b"pessoa" not in bytes(record.encrypted_template)
    assert record.legal_basis == "lgpd-art-11-ii-g"
    assert _enroll(client, gestor, world["person"], "pessoa").status_code == 201
    assert BiometricTemplate.objects.count() == 1
    actions = list(
        AuditEvent.objects.filter(action__startswith="biometric.").values_list("action", "changes")
    )
    assert [action for action, _ in actions] == ["biometric.enrolled", "biometric.reenrolled"]
    assert all(
        set(changes) == {"person_id", "engine_version", "legal_basis"} for _, changes in actions
    )
    status = client.get(f"/api/v1/people/{world['person'].id}/biometric/").json()["data"]
    assert status["enrolled"] and status["enrolled_at"]
    assert "face:" not in caplog.text and "pessoa" not in json.dumps(status)


def test_biometric_list_shows_minimal_status_for_managers_only(client, world, gestor):
    _enroll(client, gestor, world["person"])
    rows = client.get("/api/v1/biometrics/?q=MAT-1").json()["data"]
    assert rows == [
        {
            "id": str(world["person"].id),
            "name": str(world["person"]),
            "registrations": ["MAT-1"],
            "enrolled": True,
            "enrolled_at": rows[0]["enrolled_at"],
            "engine_version": "synthetic-test-1",
        }
    ]
    client.force_login(world["account"])
    assert client.get("/api/v1/biometrics/").status_code == 403


def test_enrollment_requires_permission_active_membership_and_a_face(client, world, gestor):
    client.force_login(world["account"])
    assert (
        client.post(
            f"/api/v1/people/{world['person'].id}/biometric/",
            {"image": _capture(), "confirmed": "true"},
        ).status_code
        == 403
    )
    client.force_login(gestor)
    no_face = SimpleUploadedFile("x.png", b"paisagem", content_type="image/png")
    response = client.post(
        f"/api/v1/people/{world['person'].id}/biometric/", {"image": no_face, "confirmed": "true"}
    )
    assert response.status_code == 400
    wrong_type = SimpleUploadedFile("x.gif", b"face:pessoa", content_type="image/gif")
    assert (
        client.post(
            f"/api/v1/people/{world['person'].id}/biometric/",
            {"image": wrong_type, "confirmed": "true"},
        ).status_code
        == 400
    )
    Membership.objects.filter(person=world["person"]).update(is_active=False)
    assert _enroll(client, gestor, world["person"]).status_code == 409
    assert not BiometricTemplate.objects.exists()


def test_engine_or_key_missing_is_reported_as_unavailable(client, world, gestor, settings):
    settings.SIGAB_FACE_ENGINE = ""
    assert _enroll(client, gestor, world["person"]).status_code == 503
    settings.SIGAB_FACE_ENGINE = "sigab.tests.test_requirements_085_086.SyntheticEngine"
    settings.SIGAB_BIOMETRIC_KEY = ""
    assert _enroll(client, gestor, world["person"]).status_code == 503
    assert not BiometricTemplate.objects.exists()


def test_deletion_is_physical_audited_and_follows_last_membership(client, world, gestor):
    _enroll(client, gestor, world["person"])
    response = _post(
        client,
        f"people/{world['person'].id}/biometric/delete/",
        {"reason": "Pedido do titular", "confirmed": True},
    )
    assert response.status_code == 200 and not BiometricTemplate.objects.exists()
    deleted = AuditEvent.objects.get(action="biometric.deleted")
    assert deleted.reason == "Pedido do titular" and "template" not in json.dumps(deleted.changes)

    _enroll(client, gestor, world["person"])
    from sigab.services import set_membership_active

    role = world["account"].grants.get().role
    role.permissions = [*role.permissions, "identity.manage"]
    role.save()
    membership = Membership.objects.get(person=world["person"])
    set_membership_active(
        world["ctx"], membership_id=membership.id, is_active=False, confirmed=True, reason="Saída"
    )
    assert not BiometricTemplate.objects.exists()
    assert AuditEvent.objects.filter(action="biometric.deleted").count() == 2


# SIGAB-086 — verification required on checkout and return


def test_checkout_requires_an_approved_single_use_verification(client, world, gestor):
    _enroll(client, gestor, world["person"])
    client.force_login(world["account"])
    assert _post(client, "service-batches/", _basket(world)).status_code == 400
    single = _post(
        client,
        f"items/{world['item'].id}/checkout/",
        {
            "recipient_id": str(world["person"].id),
            "idempotency_key": str(uuid4()),
            "confirmed": True,
        },
    )
    assert single.status_code == 400

    rejected = _verify(client, world["account"], world["person"], who="outra")
    assert rejected.json()["data"]["result"] == "rejected"
    assert (
        _post(client, "service-batches/", _basket(world, rejected.json()["data"]["id"])).status_code
        == 409
    )
    assert "score" not in json.dumps(rejected.json())

    approved = _verify(client, world["account"], world["person"]).json()["data"]
    assert approved["result"] == "approved"
    body = _basket(world, approved["id"])
    first = _post(client, "service-batches/", body)
    assert first.status_code == 201 and first.json()["data"]["identity_method"] == "facial"
    assert _post(client, "service-batches/", body).status_code == 200  # replay, same key
    second = Item.objects.create(
        organization=world["org"],
        equipment_type=world["type"],
        unit=world["unit"],
        storage_location=world["location"],
        serial_number="SYN-002",
    )
    reuse = _basket(world, approved["id"], item_ids=[str(second.id)])
    response = _post(client, "service-batches/", reuse)
    assert response.status_code == 409 and "já utilizada" in response.json()["error"]
    assert ServiceBatch.objects.get().face_verification_id is not None


def test_verification_is_bound_to_person_operator_operation_and_time(client, world, gestor):
    _enroll(client, gestor, world["person"])
    other_person = Person.objects.create(organization=world["org"], name="Outra pessoa")
    Membership.objects.create(
        organization=world["org"],
        person=other_person,
        registration="MAT-2",
        main_unit=world["unit"],
    )
    verification = _verify(client, world["account"], world["person"]).json()["data"]["id"]
    for change in ({"recipient_id": str(other_person.id)},):
        assert (
            _post(client, "service-batches/", _basket(world, verification, **change)).status_code
            == 409
        )
    return_verification = _verify(client, world["account"], world["person"], "return").json()[
        "data"
    ]["id"]
    assert _post(client, "service-batches/", _basket(world, return_verification)).status_code == 409
    FaceVerification.objects.filter(pk=verification).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert _post(client, "service-batches/", _basket(world, verification)).status_code == 409
    fresh = _verify(client, world["account"], world["person"]).json()["data"]["id"]
    client.force_login(gestor)
    assert _post(client, "service-batches/", _basket(world, fresh)).status_code == 403
    assert not ServiceBatch.objects.exists()


def test_verification_demands_visual_check_and_enrollment(client, world, gestor):
    assert _verify(client, world["account"], world["person"]).status_code == 409
    _enroll(client, gestor, world["person"])
    assert _verify(client, world["account"], world["person"], confirmed="false").status_code == 400
    client.force_login(gestor)
    assert _verify(client, gestor, world["person"]).status_code == 403


def test_return_with_facial_verification_records_the_method(client, world, gestor):
    _enroll(client, gestor, world["person"])
    checkout = _verify(client, world["account"], world["person"]).json()["data"]["id"]
    assert _post(client, "service-batches/", _basket(world, checkout)).status_code == 201
    verification = _verify(client, world["account"], world["person"], "return").json()["data"]["id"]
    body = {
        "person_id": str(world["person"].id),
        "items": [{"item_id": str(world["item"].id), "condition": "fit"}],
        "stock": [],
        "idempotency_key": str(uuid4()),
        "confirmed": True,
    }
    assert _post(client, "return-batches/", body).status_code == 400
    response = _post(client, "return-batches/", {**body, "face_verification_id": verification})
    assert response.status_code == 201 and response.json()["data"]["identity_method"] == "facial"
    register = client.get("/api/v1/movements/?kind=individual").json()["data"]
    assert {row["identity_method"] for row in register} == {"facial"}


def test_paper_contingency_entry_still_works_without_verification(client, api_world):
    client.force_login(api_world["account"])
    response = _post(
        client,
        f"items/{api_world['item'].id}/checkout/",
        {
            "recipient_id": str(api_world["person"].id),
            "idempotency_key": str(uuid4()),
            "confirmed": True,
            "contingency": {
                "occurred_at": (timezone.now() - timedelta(hours=1)).isoformat(),
                "paper_reference": "F01/L01",
            },
        },
    )
    assert response.status_code == 201, response.json()


# Signed term approved by the inventory administrator (ADR 0008, section 8)


def _checked_out(world):
    """Deliver the item outside the identity requirement to prepare a return scenario."""
    from django.test import override_settings

    with override_settings(SIGAB_REQUIRE_IDENTITY_CHECK=False):
        checkout_basket(
            world["ctx"],
            recipient_id=world["person"].id,
            item_ids=[world["item"].id],
            stock=[],
            idempotency_key=uuid4(),
            custody_mode="indefinite",
            due_at=None,
            confirmed=True,
        )


def _term(client, world, operation="return", **request):
    client.force_login(world["account"])
    if not request:
        request = (
            {"items": [{"item_id": str(world["item"].id), "condition": "fit"}], "stock": []}
            if operation == "return"
            else {"items": [str(world["item"].id)], "stock": [], "custody_mode": "indefinite"}
        )
    return _post(
        client,
        "identity-exceptions/",
        {
            "operation": operation,
            "person_id": str(world["person"].id),
            "reason_code": "verification_failed",
            "reason": "",
            "request": request,
            "idempotency_key": str(uuid4()),
            "confirmed": True,
        },
    )


def test_signed_return_term_waits_for_the_administrator_and_then_returns(client, world, gestor):
    _checked_out(world)
    created = _term(client, world)
    assert created.status_code == 201
    term = created.json()["data"]
    assert term["code"].startswith("TM-") and term["status"] == "pending_signature"
    assert term["person"]["registration"] == "MAT-1" and "cpf" not in json.dumps(term).lower()

    # While open, the material cannot be returned by another path.
    options = client.get(f"/api/v1/return-batches/options/?person={world['person'].id}").json()
    assert options["data"]["items"][0]["awaiting_approval"] is True

    client.force_login(gestor)
    assert (
        _post(
            client,
            f"identity-exceptions/{term['id']}/decision/",
            {"approve": True, "confirmed": True},
        ).status_code
        == 409
    )
    client.force_login(world["account"])
    assert (
        _post(client, f"identity-exceptions/{term['id']}/signed/", {"confirmed": True}).status_code
        == 200
    )
    # The operator who registered the term never approves it.
    assert _post(
        client, f"identity-exceptions/{term['id']}/decision/", {"approve": True, "confirmed": True}
    ).status_code in (403, 404)
    assert Item.objects.get(pk=world["item"].pk).availability == "in_custody"

    client.force_login(gestor)
    pending = client.get("/api/v1/identity-exceptions/?status=pending_approval").json()["data"]
    assert [row["code"] for row in pending] == [term["code"]]
    assert pending[0]["permissions"]["can_decide"] is True
    decided = _post(
        client, f"identity-exceptions/{term['id']}/decision/", {"approve": True, "confirmed": True}
    )
    assert decided.status_code == 200 and decided.json()["data"]["status"] == "approved"
    item = Item.objects.get(pk=world["item"].pk)
    assert item.availability == "available" and item.current_holder is None
    batch = ReturnBatch.objects.get()
    assert batch.identity_method == "signed_term" and batch.operator == world["account"]
    exception = IdentityException.objects.get()
    assert exception.decided_by == gestor
    assert AuditEvent.objects.filter(action="identity_exception.approved", actor=gestor).exists()
    assert (
        _post(
            client,
            f"identity-exceptions/{term['id']}/decision/",
            {"approve": True, "confirmed": True},
        ).status_code
        == 409
    )


def test_checkout_term_rejection_and_cancellation_move_nothing(client, world, gestor):
    term = _term(client, world, "checkout").json()["data"]
    _post(client, f"identity-exceptions/{term['id']}/signed/", {"confirmed": True})
    client.force_login(gestor)
    no_reason = _post(
        client, f"identity-exceptions/{term['id']}/decision/", {"approve": False, "confirmed": True}
    )
    assert no_reason.status_code == 400
    rejected = _post(
        client,
        f"identity-exceptions/{term['id']}/decision/",
        {"approve": False, "reason": "Termo sem assinatura legível", "confirmed": True},
    )
    assert rejected.json()["data"]["status"] == "rejected"
    assert not ServiceBatch.objects.exists()
    assert Item.objects.get(pk=world["item"].pk).availability == "available"

    second = _term(client, world, "checkout").json()["data"]
    assert (
        _post(
            client,
            f"identity-exceptions/{second['id']}/cancel/",
            {"reason": "Erro de seleção", "confirmed": True},
        ).json()["data"]["status"]
        == "cancelled"
    )


def test_checkout_term_approval_executes_with_operator_and_revalidates(client, world, gestor):
    term = _term(client, world, "checkout").json()["data"]
    _post(client, f"identity-exceptions/{term['id']}/signed/", {"confirmed": True})
    # The item leaves through another path before the decision: approval must fail.
    Item.objects.filter(pk=world["item"].pk).update(availability="unavailable")
    client.force_login(gestor)
    response = _post(
        client, f"identity-exceptions/{term['id']}/decision/", {"approve": True, "confirmed": True}
    )
    assert response.status_code in (400, 409)
    assert IdentityException.objects.get().status == "pending_approval"
    Item.objects.filter(pk=world["item"].pk).update(availability="available")
    response = _post(
        client, f"identity-exceptions/{term['id']}/decision/", {"approve": True, "confirmed": True}
    )
    assert response.status_code == 200
    batch = ServiceBatch.objects.get()
    assert batch.identity_method == "signed_term" and batch.operator == world["account"]
    assert Item.objects.get(pk=world["item"].pk).current_holder == world["person"]


def test_term_requires_permission_and_rejects_duplicate_open_terms(client, world, gestor):
    _checked_out(world)
    assert _term(client, world).status_code == 201
    assert _term(client, world).status_code == 409
    approver_without_scope = Account.objects.create_user(
        username="leitor", password="Senha-forte-123", organization=world["org"]
    )
    client.force_login(approver_without_scope)
    assert client.get("/api/v1/identity-exceptions/").status_code == 403
    term = IdentityException.objects.get()
    assert client.get(f"/api/v1/identity-exceptions/{term.id}/").status_code == 404


def test_return_term_with_stock_line_settles_the_loan(client, world, gestor):
    kind, _ = _quantitative_stock(world, "40")
    from django.test import override_settings

    with override_settings(SIGAB_REQUIRE_IDENTITY_CHECK=False):
        batch, _ = checkout_basket(
            world["ctx"],
            recipient_id=world["person"].id,
            item_ids=[],
            stock=[StockRequest(kind.id, world["unit"].id, world["location"].id, Decimal("10"))],
            idempotency_key=uuid4(),
            custody_mode="indefinite",
            due_at=None,
            confirmed=True,
        )
    loan = StockLoan.objects.get(batch=batch)
    term = _term(
        client, world, items=[], stock=[{"loan_id": str(loan.id), "quantity": "4"}]
    ).json()["data"]
    assert term["stock"][0]["quantity"] == "4"
    _post(client, f"identity-exceptions/{term['id']}/signed/", {"confirmed": True})
    client.force_login(gestor)
    _post(
        client, f"identity-exceptions/{term['id']}/decision/", {"approve": True, "confirmed": True}
    )
    loan.refresh_from_db()
    assert loan.open_quantity == 6


def test_unit_scoped_approver_cannot_decide_term_of_other_unit(client, world, gestor):
    unit = Unit.objects.create(organization=world["org"], name="Unidade B", code="UB")
    grant = gestor.grants.get()
    grant.scope_type, grant.unit = "unit", unit
    grant.save()
    term = _term(client, world, "checkout").json()["data"]
    _post(client, f"identity-exceptions/{term['id']}/signed/", {"confirmed": True})
    client.force_login(gestor)
    assert client.get("/api/v1/identity-exceptions/").json()["data"] == []
    assert (
        _post(
            client,
            f"identity-exceptions/{term['id']}/decision/",
            {"approve": True, "confirmed": True},
        ).status_code
        == 404
    )


def test_session_exposes_identity_flags(client, world, gestor):
    client.force_login(gestor)
    permissions = client.get("/api/v1/session/").json()["data"]["permissions"]
    assert permissions["can_manage_biometrics"] and permissions["can_approve_identity_exceptions"]
    assert permissions["identity_check_required"] is True


# Counter entry point: registration, then face (identity-first flow).


def test_counter_identifies_person_by_exact_registration(client, world, gestor):
    _enroll(client, gestor, world["person"])
    client.force_login(world["account"])
    response = client.get("/api/v1/counter/identify/?registration=mat-1")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["id"] == str(world["person"].id)
    assert body["registration"] == "MAT-1"
    assert body["biometric_enrolled"] is True
    assert body["operations"] == {"checkout": True, "return": True}
    # Minimal identification only: no CPF, phone or account data.
    assert set(body) == {
        "id",
        "name",
        "registration",
        "biometric_enrolled",
        "open_possessions",
        "own",
        "operations",
    }


def test_counter_identify_refuses_partial_inactive_and_unauthorized(client, world, gestor):
    client.force_login(world["account"])
    assert client.get("/api/v1/counter/identify/?registration=MAT").status_code == 404
    assert client.get("/api/v1/counter/identify/").status_code == 400
    Membership.objects.filter(person=world["person"]).update(is_active=False)
    assert client.get("/api/v1/counter/identify/?registration=MAT-1").status_code == 404
    client.force_login(gestor)
    assert client.get("/api/v1/counter/identify/?registration=MAT-1").status_code == 403


def test_identity_first_verification_survives_material_selection(client, world, gestor):
    """The verification taken at identification is still valid minutes later, once."""
    _enroll(client, gestor, world["person"])
    verification = _verify(client, world["account"], world["person"]).json()["data"]["id"]
    FaceVerification.objects.filter(pk=verification).update(
        verified_at=timezone.now() - timedelta(minutes=5)
    )
    assert _post(client, "service-batches/", _basket(world, verification)).status_code == 201
    second = _post(client, "service-batches/", _basket(world, verification))
    assert second.status_code in {400, 409}


def test_person_created_with_first_membership_atomically(client, world, gestor):
    admin = world["account"]
    role = Role.objects.create(
        organization=world["org"], name="Identidade", permissions=["identity.manage"]
    )
    Grant.objects.create(
        organization=world["org"], account=admin, role=role, scope_type=Grant.Scope.ORGANIZATION
    )
    client.force_login(admin)
    body = {"name": "Pessoa Nova", "registration": "MAT-9", "main_unit_id": str(world["unit"].id)}
    response = _post(client, "people/", body)
    assert response.status_code == 201, response.content
    person = Person.objects.get(name="Pessoa Nova")
    assert person.memberships.get().registration == "MAT-9"
    # Duplicate registration: nothing is created, not even the person.
    duplicate = _post(client, "people/", {**body, "name": "Outra Pessoa", "registration": "MAT-1"})
    assert duplicate.status_code == 400
    assert not Person.objects.filter(name="Outra Pessoa").exists()
    # Then the face can be enrolled immediately.
    assert _enroll(client, gestor, person, who="nova").status_code in {200, 201}


def test_existing_inventory_manager_role_receives_identity_permissions(world):
    """Installations created before matrix 1.4.0 get the new codes by migration 0015."""
    from importlib import import_module

    from django.apps import apps

    migration = import_module("sigab.migrations.0015_inventory_manager_identity_permissions")
    legacy = Role.objects.create(
        organization=world["org"], name="Gestor de acervo", permissions=["item.view"]
    )
    other = Role.objects.create(organization=world["org"], name="Leitor", permissions=["item.view"])
    migration.forward(apps, None)
    migration.forward(apps, None)  # idempotent
    legacy.refresh_from_db()
    other.refresh_from_db()
    assert legacy.permissions == ["item.view", "biometric.manage", "movement.exception.approve"]
    assert other.permissions == ["item.view"]
    migration.backward(apps, None)
    legacy.refresh_from_db()
    assert legacy.permissions == ["item.view"]


def test_operator_cancels_verification_after_identification(client, world, gestor):
    """Cancel after the face was recognized: the verification can no longer authorize."""
    _enroll(client, gestor, world["person"])
    verification = _verify(client, world["account"], world["person"]).json()["data"]["id"]
    path = f"face-verifications/{verification}/cancel/"
    assert _post(client, path, {}).status_code == 400  # explicit confirmation
    # Another account cannot cancel it, and cannot learn it exists.
    client.force_login(gestor)
    assert _post(client, path, {"confirmed": True}).status_code == 404
    client.force_login(world["account"])
    assert _post(client, path, {"confirmed": True}).status_code == 200
    assert AuditEvent.objects.filter(action="face.verification.cancelled").count() == 1
    refused = _post(client, "service-batches/", _basket(world, verification))
    assert refused.status_code == 409
    assert Item.objects.get(pk=world["item"].pk).availability == "available"
    # Cancelling again changes nothing.
    assert _post(client, path, {"confirmed": True}).status_code == 200
    assert AuditEvent.objects.filter(action="face.verification.cancelled").count() == 1


def test_used_verification_cannot_be_cancelled(client, world, gestor):
    _enroll(client, gestor, world["person"])
    verification = _verify(client, world["account"], world["person"]).json()["data"]["id"]
    assert _post(client, "service-batches/", _basket(world, verification)).status_code == 201
    response = _post(client, f"face-verifications/{verification}/cancel/", {"confirmed": True})
    assert response.status_code == 409


def test_counter_identify_by_person_id_and_item_codes_for_typed_lookup(client, world):
    client.force_login(world["account"])
    response = client.get(f"/api/v1/counter/identify/?person={world['person'].id}")
    assert response.status_code == 200
    assert response.json()["data"]["registration"] == "MAT-1"
    assert client.get(f"/api/v1/counter/identify/?person={uuid4()}").status_code == 404
    options = client.get("/api/v1/service-batches/options/").json()["data"]
    item = world["item"]
    expected = [code for code in (item.serial_number, item.asset_number) if code]
    assert options["items"][0]["codes"] == expected


def test_operator_never_registers_own_checkout_or_return(client, world, gestor):
    """The operator's own face is enrolled to take material; another operator serves him."""
    from sigab.services import checkout_item

    operator = world["account"]
    operator.person = world["person"]
    operator.save(update_fields=["person"])
    _enroll(client, gestor, world["person"])
    client.force_login(operator)
    identified = client.get("/api/v1/counter/identify/?registration=MAT-1").json()["data"]
    assert identified["own"] is True
    assert identified["operations"] == {"checkout": False, "return": False}
    refused = _verify(client, operator, world["person"])
    assert refused.status_code == 409
    assert "Outro operador" in refused.json()["error"]
    assert _post(client, "service-batches/", _basket(world)).status_code == 409
    term = _post(
        client,
        "identity-exceptions/",
        {
            "operation": "checkout",
            "person_id": str(world["person"].id),
            "reason_code": "camera_unavailable",
            "request": {
                "items": [str(world["item"].id)],
                "stock": [],
                "custody_mode": "indefinite",
            },
            "idempotency_key": str(uuid4()),
            "confirmed": True,
        },
    )
    assert term.status_code == 409
    with pytest.raises(ValidationError):
        checkout_item(
            world["ctx"],
            item_id=world["item"].id,
            recipient_id=world["person"].id,
            idempotency_key=uuid4(),
            confirmed=True,
        )
    assert Item.objects.get(pk=world["item"].pk).availability == "available"
    assert not FaceVerification.objects.exists()

    # Another operator serves him normally.
    other = Account.objects.create_user(
        username="operador-2", password="Senha-forte-123", organization=world["org"]
    )
    role = Role.objects.get(organization=world["org"], name="Operador")
    Grant.objects.create(
        organization=world["org"], account=other, role=role, scope_type=Grant.Scope.ORGANIZATION
    )
    verification = _verify(client, other, world["person"]).json()["data"]["id"]
    assert _post(client, "service-batches/", _basket(world, verification)).status_code == 201
    # And he cannot register his own return either.
    client.force_login(operator)
    own_return = _post(
        client,
        "return-batches/",
        {
            "person_id": str(world["person"].id),
            "items": [{"item_id": str(world["item"].id), "condition": "fit"}],
            "stock": [],
            "confirmed": True,
            "idempotency_key": str(uuid4()),
        },
    )
    assert own_return.status_code == 409


@pytest.fixture
def administrator(world):
    """Account holding the real "Gestor de acervo" template of matrix 1.5.0."""
    from sigab.roles import ROLE_TEMPLATES

    template = next(t for t in ROLE_TEMPLATES if t["key"] == "organization_inventory_manager")
    account = Account.objects.create_user(
        username="administrador", password="Senha-forte-123", organization=world["org"]
    )
    role = Role.objects.create(
        organization=world["org"],
        name="Gestor de acervo (modelo)",
        permissions=list(template["permissions"]),
    )
    Grant.objects.create(
        organization=world["org"],
        account=account,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
        granted_by=world["account"],
    )
    return account


def test_administrator_checks_out_and_returns_any_material(client, world, administrator):
    """Matrix 1.5.0: the inventory administrator serves the counter, with and without record."""
    other_unit = Unit.objects.create(organization=world["org"], name="Unidade B", code="UB")
    kind, _ = _quantitative_stock(world, "40")
    _enroll(client, administrator, world["person"])
    client.force_login(administrator)
    session = client.get("/api/v1/session/").json()["data"]["permissions"]
    assert session["can_checkout"] and session["can_return"]

    checkout = _verify(client, administrator, world["person"]).json()["data"]["id"]
    stock_line = {
        "equipment_type_id": str(kind.id),
        "unit_id": str(world["unit"].id),
        "storage_location_id": str(world["location"].id),
        "quantity": "10",
    }
    response = _post(client, "service-batches/", _basket(world, checkout, stock=[stock_line]))
    assert response.status_code == 201, response.content
    assert ServiceBatch.objects.get().operator == administrator
    assert Item.objects.get(pk=world["item"].pk).current_holder == world["person"]
    loan = StockLoan.objects.get()

    verification = _verify(client, administrator, world["person"], "return").json()["data"]["id"]
    returned = _post(
        client,
        "return-batches/",
        {
            "person_id": str(world["person"].id),
            "items": [{"item_id": str(world["item"].id), "condition": "fit"}],
            "stock": [{"loan_id": str(loan.id), "quantity": "10"}],
            "face_verification_id": verification,
            "idempotency_key": str(uuid4()),
            "confirmed": True,
        },
    )
    assert returned.status_code == 201, returned.content
    assert ReturnBatch.objects.get().operator == administrator
    assert Item.objects.get(pk=world["item"].pk).availability == "available"
    loan.refresh_from_db()
    assert loan.open_quantity == 0
    # Organization scope: the permission reaches every unit, not only the first one.
    from sigab.permissions import MOVEMENT_CHECKOUT, MOVEMENT_RETURN, has_permission

    assert has_permission(administrator, MOVEMENT_CHECKOUT, world["org"], other_unit)
    assert has_permission(administrator, MOVEMENT_RETURN, world["org"], other_unit)


def test_administrator_never_approves_the_term_they_registered(client, world, administrator):
    """Operating does not lift the four-eyes rule: another administrator approves the term."""
    response = _post_term_as(client, administrator, world)
    assert response.status_code == 201, response.content
    term = response.json()["data"]
    _post(client, f"identity-exceptions/{term['id']}/signed/", {"confirmed": True})
    own = _post(
        client, f"identity-exceptions/{term['id']}/decision/", {"approve": True, "confirmed": True}
    )
    assert own.status_code == 409
    assert "não aprova o próprio termo" in own.json()["error"]
    assert not ServiceBatch.objects.exists()
    assert IdentityException.objects.get().status == "pending_approval"


def _post_term_as(client, account, world):
    client.force_login(account)
    return _post(
        client,
        "identity-exceptions/",
        {
            "operation": "checkout",
            "person_id": str(world["person"].id),
            "reason_code": "verification_failed",
            "reason": "",
            "request": {
                "items": [str(world["item"].id)],
                "stock": [],
                "custody_mode": "indefinite",
            },
            "idempotency_key": str(uuid4()),
            "confirmed": True,
        },
    )


def test_existing_inventory_manager_role_receives_movement_permissions(world):
    """Installations created before matrix 1.5.0 get checkout and return by migration 0016."""
    from importlib import import_module

    from django.apps import apps

    migration = import_module("sigab.migrations.0016_inventory_manager_movements")
    legacy = Role.objects.create(
        organization=world["org"], name="Gestor de acervo", permissions=["item.view"]
    )
    other = Role.objects.create(organization=world["org"], name="Leitor", permissions=["item.view"])
    migration.forward(apps, None)
    migration.forward(apps, None)  # idempotent
    legacy.refresh_from_db()
    other.refresh_from_db()
    assert legacy.permissions == ["item.view", "movement.checkout", "movement.return"]
    assert other.permissions == ["item.view"]
    migration.backward(apps, None)
    legacy.refresh_from_db()
    assert legacy.permissions == ["item.view"]
