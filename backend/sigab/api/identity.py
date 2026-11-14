"""Facial biometrics and signed-term endpoints (ADR 0008, SIGAB-085/086).

Captures arrive as multipart uploads, are read into memory and handed to the engine; they
are never stored, logged or echoed back. Responses carry results, never scores or templates.
"""

from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404

from sigab import biometrics as infrastructure
from sigab.domain import biometrics as domain
from sigab.models import IdentityException, Person
from sigab.permissions import (
    BIOMETRIC_MANAGE,
    MOVEMENT_CHECKOUT,
    MOVEMENT_EXCEPTION_APPROVE,
    MOVEMENT_RETURN,
    has_permission,
    permitted_unit_ids,
)

from .views import (
    _context,
    _organization,
    _parse_json,
    _required_confirmation,
    _required_string,
    _required_uuid,
    _response,
    _string,
    api_view,
)


def _form_uuid(request, field):
    try:
        return UUID(str(request.POST.get(field, "")))
    except ValueError as exc:
        raise ValidationError({field: "Informe um UUID válido."}) from exc


def _form_true(request, field):
    return request.POST.get(field) == "true"


def _status(record):
    return {
        "enrolled": record is not None,
        "enrolled_at": record.enrolled_at.isoformat() if record else None,
        "engine_version": record.engine_version if record else None,
    }


@api_view(methods={"GET", "POST"})
def person_biometric(request, pk):
    """Status (enrolled or not, and when) and enrollment of the person's facial template."""
    ctx = _context(request)
    if request.method == "POST":
        record = domain.enroll_biometric(
            ctx,
            person_id=pk,
            image=infrastructure.read_image(request.FILES.get("image")),
            confirmed=_form_true(request, "confirmed"),
        )
        return _response(_status(record), status=201)
    _, record = domain.biometric_status(ctx, pk)
    return _response(_status(record))


@api_view(methods={"GET"})
def biometric_list(request):
    """People with an active membership and whether their facial biometrics is enrolled.

    Minimal identification only (name and registration), for ``biometric.manage``.
    """
    organization = _organization(request)
    if not has_permission(request.user, BIOMETRIC_MANAGE, organization):
        raise PermissionDenied
    people = (
        Person.objects.filter(
            organization=organization, is_active=True, memberships__is_active=True
        )
        .select_related("biometric")
        .prefetch_related("memberships")
        .distinct()
        .order_by("functional_name", "name", "id")
    )
    query = request.GET.get("q", "").strip()[:100]
    if query:
        people = people.filter(
            Q(name__icontains=query)
            | Q(functional_name__icontains=query)
            | Q(memberships__registration__icontains=query)
        )
    rows = []
    for person in people[:500]:
        record = getattr(person, "biometric", None)
        rows.append(
            {
                "id": str(person.id),
                "name": str(person),
                "registrations": [m.registration for m in person.memberships.all() if m.is_active],
                **_status(record),
            }
        )
    return _response(rows)


@api_view(methods={"POST"})
def person_biometric_delete(request, pk):
    payload = _parse_json(request)
    domain.delete_biometric(
        _context(request),
        person_id=pk,
        reason=_required_string(payload, "reason", max_length=500),
        confirmed=_required_confirmation(payload),
    )
    return _response(_status(None))


@api_view(methods={"POST"})
def face_verification_create(request):
    verification = domain.verify_face(
        _context(request),
        person_id=_form_uuid(request, "person_id"),
        operation=request.POST.get("operation", ""),
        image=infrastructure.read_image(request.FILES.get("image")),
        operator_confirmed=_form_true(request, "operator_confirmed"),
    )
    return _response(
        {
            "id": str(verification.id),
            "result": verification.result,
            "expires_at": verification.expires_at.isoformat(),
        },
        status=201,
    )


@api_view(methods={"POST"})
def face_verification_cancel(request, pk):
    payload = _parse_json(request)
    verification = domain.cancel_verification(
        _context(request), verification_id=pk, confirmed=_required_confirmation(payload)
    )
    return _response({"id": str(verification.id), "cancelled": True})


def exception_resource(ctx, exception):
    from sigab.models import Item, StockBalance, StockLoan

    request = exception.request
    if exception.operation == "checkout":
        items = Item.objects.filter(
            organization=ctx.organization, pk__in=request["item_ids"]
        ).select_related("equipment_type", "unit")
        item_rows = [
            {
                "id": str(item.id),
                "identifier": item.display_identifier,
                "equipment_type": item.equipment_type.name,
                "unit": item.unit.name,
                "condition": None,
            }
            for item in items.order_by("equipment_type__name", "serial_number")
        ]
        stock_rows = []
        for line in request["stock"]:
            balance = (
                StockBalance.objects.filter(
                    organization=ctx.organization,
                    equipment_type_id=line["equipment_type_id"],
                    unit_id=line["unit_id"],
                    storage_location_id=line["storage_location_id"],
                )
                .select_related("equipment_type", "unit")
                .first()
            )
            stock_rows.append(
                {
                    "equipment_type": balance.equipment_type.name if balance else "—",
                    "unit": balance.unit.name if balance else "—",
                    "quantity": line["quantity"],
                }
            )
    else:
        conditions = {line["item_id"]: line for line in request["items"]}
        items = Item.objects.filter(
            organization=ctx.organization, pk__in=list(conditions)
        ).select_related("equipment_type", "unit")
        item_rows = [
            {
                "id": str(item.id),
                "identifier": item.display_identifier,
                "equipment_type": item.equipment_type.name,
                "unit": item.unit.name,
                "condition": conditions[str(item.id)]["condition"],
                "reason": conditions[str(item.id)]["reason"],
            }
            for item in items.order_by("equipment_type__name", "serial_number")
        ]
        quantities = {line["loan_id"]: line["quantity"] for line in request["stock"]}
        stock_rows = [
            {
                "equipment_type": loan.balance.equipment_type.name,
                "unit": loan.balance.unit.name,
                "quantity": quantities[str(loan.id)],
            }
            for loan in StockLoan.objects.filter(
                organization=ctx.organization, pk__in=list(quantities)
            ).select_related("balance__equipment_type", "balance__unit")
        ]
    registration = (
        exception.person.memberships.filter(is_active=True).values_list("registration", flat=True)
    ).first()
    is_requester = exception.requested_by_id == ctx.actor.id
    approver = domain.can_approve(ctx, exception) and not is_requester
    pending = exception.status in domain.OPEN_STATUSES
    return {
        "id": str(exception.id),
        "code": exception.code,
        "operation": exception.operation,
        "operation_label": exception.get_operation_display(),
        "status": exception.status,
        "status_label": exception.get_status_display(),
        # Name and registration only: CPF never appears on the term (privacy policy).
        "person": {
            "id": str(exception.person_id),
            "name": str(exception.person),
            "registration": registration,
        },
        "requested_by": exception.requested_by.username,
        "requested_at": exception.requested_at.isoformat(),
        "reason_code": exception.reason_code,
        "reason_label": exception.get_reason_code_display(),
        "reason": exception.reason,
        "custody_mode": request.get("custody_mode"),
        "due_at": request.get("due_at"),
        "items": item_rows,
        "stock": stock_rows,
        "signed_collected_at": (
            exception.signed_collected_at.isoformat() if exception.signed_collected_at else None
        ),
        "decided_by": exception.decided_by.username if exception.decided_by_id else None,
        "decided_at": exception.decided_at.isoformat() if exception.decided_at else None,
        "decision_reason": exception.decision_reason,
        "permissions": {
            "can_register_signature": is_requester
            and exception.status == IdentityException.Status.PENDING_SIGNATURE,
            "can_cancel": is_requester and pending,
            "can_decide": approver
            and exception.status == IdentityException.Status.PENDING_APPROVAL,
        },
    }


def _visible_exceptions(request, ctx, exceptions):
    """Own terms, plus terms whose every unit the reader may decide."""
    organization = ctx.organization
    approves = bool(permitted_unit_ids(request.user, MOVEMENT_EXCEPTION_APPROVE, organization))
    operates = any(
        permitted_unit_ids(request.user, code, organization)
        for code in (MOVEMENT_CHECKOUT, MOVEMENT_RETURN)
    )
    if not approves and not operates:
        raise PermissionDenied
    if not approves:
        return list(exceptions.filter(requested_by=request.user)[:200])
    return [
        exception
        for exception in exceptions[:200]
        if exception.requested_by_id == request.user.id or domain.can_approve(ctx, exception)
    ]


@api_view(methods={"GET", "POST"})
def identity_exception_list(request):
    organization = _organization(request)
    ctx = _context(request)
    if request.method == "POST":
        payload = _parse_json(request)
        exception, created = domain.request_identity_exception(
            ctx,
            operation=_required_string(payload, "operation", max_length=16),
            person_id=_required_uuid(payload, "person_id"),
            reason_code=_required_string(payload, "reason_code", max_length=24),
            reason=_string(payload, "reason", max_length=500),
            request=payload.get("request"),
            idempotency_key=_required_uuid(payload, "idempotency_key"),
            confirmed=_required_confirmation(payload),
        )
        return _response(exception_resource(ctx, exception), status=201 if created else 200)
    exceptions = IdentityException.objects.filter(organization=organization).select_related(
        "person", "requested_by", "decided_by"
    )
    status = request.GET.get("status")
    if status:
        if status not in IdentityException.Status.values:
            raise ValidationError({"status": "Valor inválido."})
        exceptions = exceptions.filter(status=status)
    visible = _visible_exceptions(request, ctx, exceptions.order_by("-requested_at", "-id"))
    return _response([exception_resource(ctx, exception) for exception in visible])


def _visible_exception(request, pk):
    organization = _organization(request)
    ctx = _context(request)
    exception = (
        IdentityException.objects.filter(pk=pk, organization=organization)
        .select_related("person", "requested_by", "decided_by")
        .first()
    )
    if not exception or not (
        exception.requested_by_id == request.user.id or domain.can_approve(ctx, exception)
    ):
        raise Http404
    return ctx, exception


@api_view(methods={"GET"})
def identity_exception_detail(request, pk):
    ctx, exception = _visible_exception(request, pk)
    return _response(exception_resource(ctx, exception))


@api_view(methods={"POST"})
def identity_exception_signed(request, pk):
    ctx, _ = _visible_exception(request, pk)
    payload = _parse_json(request)
    exception = domain.register_signed_term(
        ctx, exception_id=pk, confirmed=_required_confirmation(payload)
    )
    return _response(exception_resource(ctx, exception))


@api_view(methods={"POST"})
def identity_exception_cancel(request, pk):
    ctx, _ = _visible_exception(request, pk)
    payload = _parse_json(request)
    exception = domain.cancel_identity_exception(
        ctx,
        exception_id=pk,
        reason=_required_string(payload, "reason", max_length=500),
        confirmed=_required_confirmation(payload),
    )
    return _response(exception_resource(ctx, exception))


@api_view(methods={"POST"})
def identity_exception_decision(request, pk):
    ctx, _ = _visible_exception(request, pk)
    payload = _parse_json(request)
    exception = domain.decide_identity_exception(
        ctx,
        exception_id=pk,
        approve=payload.get("approve"),
        reason=_string(payload, "reason", max_length=500),
        confirmed=_required_confirmation(payload),
    )
    return _response(exception_resource(ctx, exception))
