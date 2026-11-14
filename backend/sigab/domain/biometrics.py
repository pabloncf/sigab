"""Facial enrollment, verification and the signed-term exception (ADR 0008).

Checkout and return require an approved facial verification of the selected person. When
that is not possible the operator generates a term, the person signs it on paper and only
an inventory administrator (``movement.exception.approve``) approves it; the operation is
executed only on approval. Images never leave this module's call stack.
"""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from sigab import biometrics
from sigab.models import (
    BiometricTemplate,
    FaceVerification,
    IdentityException,
    IdentityMethod,
    IdentityOperation,
    Item,
    Person,
    StockBalance,
    StockLoan,
    Unit,
)
from sigab.permissions import (
    BIOMETRIC_MANAGE,
    MOVEMENT_CHECKOUT,
    MOVEMENT_EXCEPTION_APPROVE,
    MOVEMENT_RETURN,
    has_any_scope,
    has_permission,
)
from sigab.services import (
    CommandContext,
    ConflictError,
    NotFoundError,
    audit,
    ensure_not_own_operation,
)

OPERATION_PERMISSION = {
    IdentityOperation.CHECKOUT: MOVEMENT_CHECKOUT,
    IdentityOperation.RETURN: MOVEMENT_RETURN,
}


def _confirmed(confirmed):
    if confirmed is not True:
        raise ValidationError({"confirmed": "A confirmação explícita é obrigatória."})


def _operation(value):
    if value not in IdentityOperation.values:
        raise ValidationError({"operation": "Use checkout ou return."})
    return IdentityOperation(value)


def _person(ctx, person_id, *, lock=False):
    people = Person.objects.filter(pk=person_id, organization=ctx.organization)
    if lock:
        people = people.select_for_update()
    person = people.first()
    if not person:
        raise ValidationError({"person_id": "Pessoa inválida."})
    return person


# Enrollment (SIGAB-085).


def _require_biometric_manager(ctx):
    if not has_permission(ctx.actor, BIOMETRIC_MANAGE, ctx.organization):
        raise PermissionDenied


@transaction.atomic
def enroll_biometric(ctx: CommandContext, *, person_id: UUID, image: bytes, confirmed: bool):
    """Create or replace the encrypted template of a person with an active membership."""
    _confirmed(confirmed)
    _require_biometric_manager(ctx)
    person = _person(ctx, person_id, lock=True)
    if not person.is_active or not person.memberships.filter(is_active=True).exists():
        raise ConflictError("Somente pessoa ativa e com vínculo ativo recebe biometria.")
    engine = biometrics.engine()
    token = biometrics.encrypt(engine.template(image))
    now = timezone.now()
    record = BiometricTemplate.objects.filter(person=person).first()
    action = "biometric.reenrolled" if record else "biometric.enrolled"
    record = record or BiometricTemplate(organization=ctx.organization, person=person)
    record.encrypted_template = token
    record.engine_version = engine.version
    record.legal_basis = settings.SIGAB_BIOMETRIC_LEGAL_BASIS
    record.enrolled_at = now
    record.enrolled_by = ctx.actor
    record.full_clean(exclude=["encrypted_template"])
    record.save()
    # Audit the fact only: never the template, the image or a similarity score.
    audit(
        ctx,
        action,
        record,
        {
            "person_id": str(person.id),
            "engine_version": engine.version,
            "legal_basis": record.legal_basis,
        },
    )
    return record


def _delete_template(ctx, record, reason):
    audit(
        ctx,
        "biometric.deleted",
        record,
        {"person_id": str(record.person_id), "engine_version": record.engine_version},
        reason=reason,
    )
    record.delete()


@transaction.atomic
def delete_biometric(ctx: CommandContext, *, person_id: UUID, reason: str, confirmed: bool):
    _confirmed(confirmed)
    _require_biometric_manager(ctx)
    person = _person(ctx, person_id, lock=True)
    record = BiometricTemplate.objects.filter(person=person).first()
    if not record:
        raise ConflictError("A pessoa não possui biometria cadastrada.")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Informe o motivo da exclusão."})
    _delete_template(ctx, record, reason[:500])


def purge_after_last_membership(ctx: CommandContext, person):
    """Retention rule: the template exists only while the person has an active membership."""
    if person.memberships.filter(is_active=True).exists():
        return
    record = BiometricTemplate.objects.filter(person=person).first()
    if record:
        _delete_template(ctx, record, "Encerramento do último vínculo ativo.")


def biometric_status(ctx: CommandContext, person_id: UUID):
    _require_biometric_manager(ctx)
    person = Person.objects.filter(pk=person_id, organization=ctx.organization).first()
    if not person:
        raise NotFoundError
    record = BiometricTemplate.objects.filter(person=person).first()
    return person, record


# Verification (SIGAB-086).


@transaction.atomic
def verify_face(
    ctx: CommandContext,
    *,
    person_id: UUID,
    operation: str,
    image: bytes,
    operator_confirmed: bool,
):
    operation = _operation(operation)
    if not has_any_scope(ctx.actor, OPERATION_PERMISSION[operation], ctx.organization):
        raise PermissionDenied
    if operator_confirmed is not True:
        raise ValidationError(
            {"operator_confirmed": "Confirme que conferiu visualmente a pessoa no balcão."}
        )
    person = _person(ctx, person_id)
    ensure_not_own_operation(ctx, person.id)
    record = BiometricTemplate.objects.filter(person=person).first()
    if not record:
        raise ConflictError("A pessoa não possui biometria cadastrada. Gere o termo.")
    engine = biometrics.engine()
    comparison = biometrics.compare(engine, record.encrypted_template, image)
    now = timezone.now()
    verification = FaceVerification.objects.create(
        organization=ctx.organization,
        person=person,
        operator=ctx.actor,
        operation=operation,
        result=(
            FaceVerification.Result.APPROVED
            if comparison.approved
            else FaceVerification.Result.REJECTED
        ),
        operator_confirmed=True,
        engine_version=comparison.engine_version,
        verified_at=now,
        expires_at=now + timedelta(seconds=settings.SIGAB_FACE_VERIFICATION_TTL_SECONDS),
    )
    audit(
        ctx,
        "face.verification",
        verification,
        {
            "person_id": str(person.id),
            "operation": operation,
            "engine_version": comparison.engine_version,
        },
        result="success" if comparison.approved else "rejected",
    )
    return verification


@transaction.atomic
def cancel_verification(ctx: CommandContext, *, verification_id: UUID, confirmed: bool):
    """Operator gives up after identification: the approved verification can no longer be used.

    Only the operator who verified may cancel; a verification already used by an operation
    stays as it is. Nothing else changes and no movement exists to compensate.
    """
    _confirmed(confirmed)
    verification = (
        FaceVerification.objects.select_for_update()
        .filter(pk=verification_id, organization=ctx.organization, operator=ctx.actor)
        .first()
    )
    if not verification:
        raise NotFoundError
    if verification.consumed_at is not None:
        raise ConflictError("A verificação já foi usada na operação e não pode ser cancelada.")
    now = timezone.now()
    if verification.expires_at > now:
        verification.expires_at = now
        verification.save(update_fields=["expires_at", "updated_at"])
        audit(
            ctx,
            "face.verification.cancelled",
            verification,
            {"person_id": str(verification.person_id), "operation": verification.operation},
        )
    return verification


def _consume_verification(ctx, verification_id, person, operation):
    now = timezone.now()
    verification = (
        FaceVerification.objects.select_for_update()
        .filter(pk=verification_id, organization=ctx.organization)
        .first()
    )
    if (
        not verification
        or verification.person_id != person.id
        or verification.operator_id != ctx.actor.id
        or verification.operation != operation
        or verification.result != FaceVerification.Result.APPROVED
        or verification.consumed_at is not None
        or verification.expires_at <= now
    ):
        raise ConflictError(
            "Verificação facial inválida, expirada ou já utilizada. Verifique de novo."
        )
    verification.consumed_at = now
    verification.save(update_fields=["consumed_at", "updated_at"])
    return verification


def resolve_identity(ctx, *, person, operation, face_verification_id, identity_exception):
    """Fields of the counter batch that prove who received or returned the material.

    Called inside the batch transaction, after the person row is locked, so the approved
    verification is consumed atomically with the movements it authorizes.
    """
    if face_verification_id and identity_exception is not None:
        raise ValidationError("Use verificação facial ou termo, não ambos.")
    if identity_exception is not None:
        if identity_exception.person_id != person.id or identity_exception.operation != operation:
            raise ConflictError("O termo não corresponde a esta operação.")
        return {
            "identity_method": IdentityMethod.SIGNED_TERM,
            "identity_exception": identity_exception,
        }
    if face_verification_id:
        return {
            "identity_method": IdentityMethod.FACIAL,
            "face_verification": _consume_verification(
                ctx, face_verification_id, person, operation
            ),
        }
    if settings.SIGAB_REQUIRE_IDENTITY_CHECK:
        raise ValidationError(
            {
                "face_verification_id": (
                    "Confirme a identidade por biometria facial ou gere o termo para aprovação."
                )
            }
        )
    return {"identity_method": IdentityMethod.NOT_REQUIRED}


# Signed term (ADR 0008, section 8).


def _parse_due_at(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None or timezone.is_naive(parsed):
        raise ValidationError({"due_at": "Informe data e hora ISO 8601 com fuso."})
    return parsed


def _lines(values, field):
    if any(not isinstance(line, dict) for line in values):
        raise ValidationError({"request": f"Linha inválida em {field}."})
    return values


def _uuid(value, field):
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValidationError({field: "Informe um UUID válido."}) from exc


def normalize_request(operation, request):
    """Validate the requested operation and return its canonical, JSON-safe form."""
    from sigab.domain.operations import positive_quantity

    if not isinstance(request, dict):
        raise ValidationError({"request": "Informe a operação solicitada."})
    items = request.get("items", [])
    stock = request.get("stock", [])
    if not isinstance(items, list) or not isinstance(stock, list):
        raise ValidationError({"request": "Itens e estoque devem ser listas."})
    if not items and not stock:
        raise ValidationError({"request": "Inclua ao menos um material."})
    if len(items) > 100 or len(stock) > 100:
        raise ValidationError({"request": "No máximo 100 linhas de cada modalidade."})
    if operation == IdentityOperation.CHECKOUT:
        custody_mode = request.get("custody_mode")
        due_at = request.get("due_at") or None
        return {
            "item_ids": sorted({str(_uuid(value, "items")) for value in items}),
            "stock": [
                {
                    "equipment_type_id": str(_uuid(line.get("equipment_type_id"), "stock")),
                    "unit_id": str(_uuid(line.get("unit_id"), "stock")),
                    "storage_location_id": str(_uuid(line.get("storage_location_id"), "stock")),
                    "quantity": str(positive_quantity(line.get("quantity"))),
                }
                for line in _lines(stock, "stock")
            ],
            "custody_mode": str(custody_mode or ""),
            "due_at": _parse_due_at(due_at).isoformat() if due_at else None,
        }
    lines = []
    for line in items:
        if not isinstance(line, dict) or line.get("condition") not in Item.Condition.values:
            raise ValidationError({"request": "Informe apto ou inapto para cada item."})
        reason = str(line.get("reason") or "").strip()[:200]
        if line["condition"] == Item.Condition.UNFIT and not reason:
            raise ValidationError({"request": "Item inapto exige motivo."})
        lines.append(
            {
                "item_id": str(_uuid(line.get("item_id"), "items")),
                "condition": line["condition"],
                "reason": reason if line["condition"] == Item.Condition.UNFIT else "",
            }
        )
    return {
        "items": sorted(lines, key=lambda value: value["item_id"]),
        "stock": [
            {
                "loan_id": str(_uuid(line.get("loan_id"), "stock")),
                "quantity": str(positive_quantity(line.get("quantity"))),
            }
            for line in _lines(stock, "stock")
        ],
    }


def _request_units(ctx, exception):
    request = exception.request
    if exception.operation == IdentityOperation.CHECKOUT:
        unit_ids = set(
            Item.objects.filter(
                organization=ctx.organization, pk__in=request["item_ids"]
            ).values_list("unit_id", flat=True)
        )
        unit_ids.update(line["unit_id"] for line in request["stock"])
    else:
        unit_ids = set(
            Item.objects.filter(
                organization=ctx.organization,
                pk__in=[line["item_id"] for line in request["items"]],
            ).values_list("unit_id", flat=True)
        )
        unit_ids.update(
            StockLoan.objects.filter(
                organization=ctx.organization,
                pk__in=[line["loan_id"] for line in request["stock"]],
            ).values_list("balance__unit_id", flat=True)
        )
    return list(Unit.objects.filter(organization=ctx.organization, pk__in=unit_ids))


def _referenced_lines(exception):
    request = exception.request
    if exception.operation == IdentityOperation.CHECKOUT:
        return set(request["item_ids"]), set()
    return (
        {line["item_id"] for line in request["items"]},
        {line["loan_id"] for line in request["stock"]},
    )


def _validate_lines(ctx, operation, person, request):
    permission = OPERATION_PERMISSION[operation]
    if operation == IdentityOperation.CHECKOUT:
        items = Item.objects.filter(organization=ctx.organization, pk__in=request["item_ids"])
        if items.count() != len(request["item_ids"]):
            raise ValidationError({"request": "A operação contém item inválido."})
        units = {item.unit for item in items.select_related("unit")}
        for line in request["stock"]:
            balance = (
                StockBalance.objects.filter(
                    organization=ctx.organization,
                    equipment_type_id=line["equipment_type_id"],
                    unit_id=line["unit_id"],
                    storage_location_id=line["storage_location_id"],
                )
                .select_related("unit")
                .first()
            )
            if not balance:
                raise ValidationError({"request": "Posição de estoque inexistente."})
            units.add(balance.unit)
    else:
        item_ids = [line["item_id"] for line in request["items"]]
        items = Item.objects.filter(
            organization=ctx.organization, pk__in=item_ids, current_holder=person
        ).select_related("unit")
        if items.count() != len(item_ids):
            raise ConflictError("Há item que não está em posse desta pessoa.")
        loan_ids = [line["loan_id"] for line in request["stock"]]
        loans = StockLoan.objects.filter(
            organization=ctx.organization, pk__in=loan_ids, recipient=person
        ).select_related("balance__unit")
        if loans.count() != len(loan_ids):
            raise ConflictError("Há pendência que não pertence a esta pessoa.")
        open_quantities = {str(loan.id): loan.open_quantity for loan in loans}
        for line in request["stock"]:
            if Decimal(line["quantity"]) > open_quantities[line["loan_id"]]:
                raise ConflictError("A quantidade excede a pendência aberta.")
        units = {item.unit for item in items} | {loan.balance.unit for loan in loans}
    for unit in units:
        if not has_permission(ctx.actor, permission, ctx.organization, unit):
            raise PermissionDenied


OPEN_STATUSES = (
    IdentityException.Status.PENDING_SIGNATURE,
    IdentityException.Status.PENDING_APPROVAL,
)


@transaction.atomic
def request_identity_exception(
    ctx: CommandContext,
    *,
    operation: str,
    person_id: UUID,
    reason_code: str,
    reason: str,
    request: dict,
    idempotency_key: UUID,
    confirmed: bool,
):
    """Generate the term. Nothing moves until an inventory administrator approves it."""
    _confirmed(confirmed)
    operation = _operation(operation)
    if not has_any_scope(ctx.actor, OPERATION_PERMISSION[operation], ctx.organization):
        raise PermissionDenied
    existing = IdentityException.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.requested_by_id != ctx.actor.id:
            raise ConflictError("A chave de idempotência já foi usada em outro termo.")
        return existing, False
    if reason_code not in IdentityException.Reason.values:
        raise ValidationError({"reason_code": "Motivo inválido."})
    reason = (reason or "").strip()
    if reason_code == IdentityException.Reason.OTHER and not reason:
        raise ValidationError({"reason": "Descreva o motivo."})
    person = _person(ctx, person_id, lock=True)
    ensure_not_own_operation(ctx, person.id)
    canonical = normalize_request(operation, request)
    _validate_lines(ctx, operation, person, canonical)
    candidate = IdentityException(operation=operation, request=canonical)
    items, loans = _referenced_lines(candidate)
    for other in IdentityException.objects.filter(
        organization=ctx.organization, person=person, operation=operation, status__in=OPEN_STATUSES
    ):
        other_items, other_loans = _referenced_lines(other)
        if items & other_items or loans & other_loans:
            raise ConflictError(f"Já existe o termo {other.code} em aberto para este material.")
    exception = IdentityException.objects.create(
        organization=ctx.organization,
        code=f"TM-{idempotency_key.hex[:16].upper()}",
        operation=operation,
        person=person,
        requested_by=ctx.actor,
        requested_at=timezone.now(),
        reason_code=reason_code,
        reason=reason[:500],
        request=canonical,
        idempotency_key=idempotency_key,
    )
    audit(
        ctx,
        "identity_exception.requested",
        exception,
        {
            "person_id": str(person.id),
            "operation": operation,
            "reason_code": reason_code,
            "code": exception.code,
        },
        reason=exception.reason,
    )
    return exception, True


def _locked_exception(ctx, exception_id):
    exception = (
        IdentityException.objects.select_for_update()
        .filter(pk=exception_id, organization=ctx.organization)
        .select_related("person", "requested_by")
        .first()
    )
    if not exception:
        raise NotFoundError
    return exception


@transaction.atomic
def register_signed_term(ctx: CommandContext, *, exception_id: UUID, confirmed: bool):
    _confirmed(confirmed)
    exception = _locked_exception(ctx, exception_id)
    if exception.requested_by_id != ctx.actor.id:
        raise PermissionDenied
    if exception.status != IdentityException.Status.PENDING_SIGNATURE:
        raise ConflictError("O termo não está aguardando assinatura.")
    exception.status = IdentityException.Status.PENDING_APPROVAL
    exception.signed_collected_at = timezone.now()
    exception.save(update_fields=["status", "signed_collected_at", "updated_at"])
    audit(ctx, "identity_exception.signed", exception, {"code": exception.code})
    return exception


@transaction.atomic
def cancel_identity_exception(
    ctx: CommandContext, *, exception_id: UUID, reason: str, confirmed: bool
):
    _confirmed(confirmed)
    exception = _locked_exception(ctx, exception_id)
    if exception.requested_by_id != ctx.actor.id:
        raise PermissionDenied
    if exception.status not in OPEN_STATUSES:
        raise ConflictError("O termo já foi decidido.")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Informe o motivo do cancelamento."})
    exception.status = IdentityException.Status.CANCELLED
    exception.decision_reason = reason[:500]
    exception.decided_at = timezone.now()
    exception.save(update_fields=["status", "decision_reason", "decided_at", "updated_at"])
    audit(ctx, "identity_exception.cancelled", exception, {"code": exception.code}, reason=reason)
    return exception


def can_approve(ctx, exception):
    units = _request_units(ctx, exception)
    return bool(units) and all(
        has_permission(ctx.actor, MOVEMENT_EXCEPTION_APPROVE, ctx.organization, unit)
        for unit in units
    )


@transaction.atomic
def decide_identity_exception(
    ctx: CommandContext,
    *,
    exception_id: UUID,
    approve: bool,
    reason: str,
    confirmed: bool,
):
    """Approve (executing the operation atomically) or reject a signed term."""
    from sigab.domain.operations import (
        ItemReturnLine,
        StockRequest,
        StockReturnLine,
        checkout_basket,
        return_basket,
    )

    _confirmed(confirmed)
    if not isinstance(approve, bool):
        raise ValidationError({"approve": "Informe verdadeiro ou falso."})
    exception = _locked_exception(ctx, exception_id)
    if not can_approve(ctx, exception):
        raise PermissionDenied
    if exception.requested_by_id == ctx.actor.id:
        raise ConflictError("Quem registrou a operação não aprova o próprio termo.")
    if exception.status != IdentityException.Status.PENDING_APPROVAL:
        raise ConflictError("O termo não está aguardando aprovação.")
    reason = (reason or "").strip()[:500]
    now = timezone.now()
    if not approve:
        if not reason:
            raise ValidationError({"reason": "Informe o motivo da recusa."})
        exception.status = IdentityException.Status.REJECTED
    else:
        # The operation is performed by the counter operator who served the person; the
        # approval is a separate, audited act of the inventory administrator.
        counter = CommandContext(exception.requested_by, ctx.organization, ctx.correlation_id)
        request = exception.request
        key = uuid5(exception.id, "execute")
        if exception.operation == IdentityOperation.CHECKOUT:
            checkout_basket(
                counter,
                recipient_id=exception.person_id,
                item_ids=[UUID(value) for value in request["item_ids"]],
                stock=[
                    StockRequest(
                        UUID(line["equipment_type_id"]),
                        UUID(line["unit_id"]),
                        UUID(line["storage_location_id"]),
                        Decimal(line["quantity"]),
                    )
                    for line in request["stock"]
                ],
                idempotency_key=key,
                custody_mode=request["custody_mode"],
                due_at=_parse_due_at(request["due_at"]),
                confirmed=True,
                identity_exception=exception,
            )
        else:
            return_basket(
                counter,
                person_id=exception.person_id,
                items=[
                    ItemReturnLine(UUID(line["item_id"]), line["condition"], line["reason"])
                    for line in request["items"]
                ],
                stock=[
                    StockReturnLine(UUID(line["loan_id"]), Decimal(line["quantity"]))
                    for line in request["stock"]
                ],
                idempotency_key=key,
                confirmed=True,
                identity_exception=exception,
            )
        exception.status = IdentityException.Status.APPROVED
    exception.decided_by = ctx.actor
    exception.decided_at = now
    exception.decision_reason = reason
    exception.save(
        update_fields=["status", "decided_by", "decided_at", "decision_reason", "updated_at"]
    )
    audit(
        ctx,
        "identity_exception.approved" if approve else "identity_exception.rejected",
        exception,
        {"code": exception.code, "operation": exception.operation},
        reason=reason,
    )
    return exception


def pending_return_lines(organization, person_id):
    """Items and loans already covered by an open return term of the person."""
    items, loans = set(), set()
    for exception in IdentityException.objects.filter(
        organization=organization,
        person_id=person_id,
        operation=IdentityOperation.RETURN,
        status__in=OPEN_STATUSES,
    ):
        exception_items, exception_loans = _referenced_lines(exception)
        items |= exception_items
        loans |= exception_loans
    return items, loans
