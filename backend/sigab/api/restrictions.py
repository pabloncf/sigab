from uuid import UUID

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from sigab.domain.restrictions import (
    change_restriction,
    create_restriction,
    require_manager,
    snapshot,
)
from sigab.models import EquipmentType, Person, PersonRestriction
from sigab.services import NotFoundError, audit

from .views import (
    _context,
    _parse_json,
    _required_confirmation,
    _required_string,
    _required_uuid,
    _response,
    _string,
    api_view,
)


def fields(payload):
    if any(key in payload for key in ("attachment", "attachment_id", "exception")):
        raise ValidationError("Anexos e exceções não estão habilitados.")

    def instant(key, required=False):
        raw = payload.get(key)
        if not raw and not required:
            return None
        value = parse_datetime(raw) if isinstance(raw, str) else None
        if value is None or timezone.is_naive(value):
            raise ValidationError({key: "Informe data e hora com fuso."})
        return value

    raw_types = payload.get("equipment_type_ids", [])
    if not isinstance(raw_types, list) or len(raw_types) > 100:
        raise ValidationError({"equipment_type_ids": "Use uma lista de até 100 tipos."})
    try:
        type_ids = [UUID(str(value)) for value in raw_types]
    except (ValueError, TypeError) as exc:
        raise ValidationError({"equipment_type_ids": "UUID inválido."}) from exc
    return {
        "category": _required_string(payload, "category", max_length=16),
        "summary": _required_string(payload, "summary", max_length=200),
        "source": _required_string(payload, "source", max_length=160),
        "reference": _string(payload, "reference", max_length=160),
        "starts_at": instant("starts_at", required=True),
        "ends_at": instant("ends_at"),
        "equipment_type_ids": type_ids,
    }


def resource(value):
    return {
        "id": str(value.id),
        "person_id": str(value.person_id),
        "person_name": str(value.person),
        **snapshot(value),
    }


@api_view(methods={"GET", "POST"})
def restriction_list(request):
    ctx = _context(request)
    require_manager(ctx)
    if request.method == "POST":
        payload = _parse_json(request)
        value = create_restriction(
            ctx,
            person_id=_required_uuid(payload, "person_id"),
            confirmed=_required_confirmation(payload),
            **fields(payload),
        )
        return _response(resource(value), status=201)
    # This response contains restricted summaries; reads are recorded without their content.
    audit(ctx, "restriction.viewed", ctx.organization, {"collection": True})
    values = (
        PersonRestriction.objects.filter(organization=ctx.organization)
        .select_related("person")
        .prefetch_related("equipment_types")
        .order_by("-starts_at", "id")
    )
    return _response(
        {
            "restrictions": [resource(value) for value in values],
            "people": [
                {"id": str(person.id), "name": str(person)}
                for person in Person.objects.filter(organization=ctx.organization).order_by(
                    "name", "id"
                )
            ],
            "equipment_types": [
                {"id": str(kind.id), "name": kind.name}
                for kind in EquipmentType.objects.filter(organization=ctx.organization).order_by(
                    "name", "id"
                )
            ],
        }
    )


@api_view(methods={"GET", "POST"})
def restriction_detail(request, pk):
    ctx = _context(request)
    require_manager(ctx)
    value = (
        PersonRestriction.objects.filter(pk=pk, organization=ctx.organization)
        .select_related("person")
        .first()
    )
    if not value:
        raise NotFoundError
    if request.method == "POST":
        payload = _parse_json(request)
        action = payload.get("action")
        if action not in ("change", "close"):
            raise ValidationError({"action": "Use change ou close."})
        value = change_restriction(
            ctx,
            restriction_id=pk,
            reason=_required_string(payload, "reason"),
            confirmed=_required_confirmation(payload),
            close=action == "close",
            **(fields(payload) if action == "change" else {}),
        )
    else:
        audit(ctx, "restriction.viewed", value)
    return _response(
        {
            **resource(value),
            "history": [
                {
                    "id": str(event.id),
                    "action": event.action,
                    "reason": event.reason,
                    "occurred_at": event.occurred_at.isoformat(),
                    "before": event.before,
                    "after": event.after,
                }
                for event in value.history.order_by("occurred_at", "id")
            ],
        }
    )
