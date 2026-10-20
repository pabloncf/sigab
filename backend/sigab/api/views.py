import json
from functools import wraps
from json import JSONDecodeError
from uuid import UUID

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from sigab.models import Item, Person
from sigab.permissions import MOVE_ITEM, SET_ITEM_CONDITION, VIEW_ITEM, has_permission
from sigab.services import (
    CommandContext,
    ConflictError,
    checkout_item,
    return_item,
    set_item_condition,
)

MAX_JSON_BODY_BYTES = 16 * 1024


def _response(data=None, *, status=200, meta=None):
    payload = {"success": True, "data": data}
    if meta is not None:
        payload["meta"] = meta
    return JsonResponse(payload, status=status)


def _error(message, *, status, details=None):
    payload = {"success": False, "error": message}
    if details:
        payload["details"] = details
    return JsonResponse(payload, status=status)


def api_view(*, methods):
    """Apply consistent API authentication, method, and domain error handling."""

    allowed_methods = frozenset(methods)

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in allowed_methods:
                response = _error("Método não permitido.", status=405)
                response["Allow"] = ", ".join(sorted(allowed_methods))
                return response
            if not request.user.is_authenticated or not request.user.is_active:
                return _error("Autenticação necessária.", status=401)
            try:
                return view(request, *args, **kwargs)
            except Http404:
                return _error("Recurso não encontrado.", status=404)
            except PermissionDenied:
                return _error("Acesso negado.", status=403)
            except ConflictError as exc:
                return _error(_validation_message(exc), status=409)
            except (JSONDecodeError, UnicodeDecodeError):
                return _error("JSON inválido.", status=400)
            except ValidationError as exc:
                return _error(
                    "Dados inválidos.", status=400, details={"non_field_errors": exc.messages}
                )

        return wrapped

    return decorator


def _validation_message(exc):
    return exc.messages[0] if exc.messages else "A operação conflita com o estado atual."


def _organization(request):
    if not request.user.organization_id:
        raise PermissionDenied
    return request.user.organization


def _item(request, pk, permission=VIEW_ITEM):
    organization = _organization(request)
    item = (
        Item.objects.filter(pk=pk, organization=organization)
        .select_related("equipment_type", "unit", "storage_location", "current_holder")
        .first()
    )
    if not item or not has_permission(request.user, permission, organization, item.unit):
        raise Http404
    return item


def _parse_json(request):
    if request.content_type != "application/json":
        raise ValidationError("Envie o corpo como application/json.")
    if len(request.body) > MAX_JSON_BODY_BYTES:
        raise ValidationError("O corpo da requisição excede o limite permitido.")
    payload = json.loads(request.body or b"{}")
    if not isinstance(payload, dict):
        raise ValidationError("O corpo JSON deve ser um objeto.")
    return payload


def _required_uuid(payload, field):
    try:
        return UUID(str(payload[field]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError({field: "Informe um UUID válido."}) from exc


def _required_confirmation(payload):
    if payload.get("confirmed") is not True:
        raise ValidationError({"confirmed": "A confirmação explícita é obrigatória."})
    return True


def _string(payload, field, *, max_length=200):
    value = payload.get(field, "")
    if not isinstance(value, str):
        raise ValidationError({field: "Informe um texto válido."})
    if len(value) > max_length:
        raise ValidationError({field: f"Use no máximo {max_length} caracteres."})
    return value


def _item_summary(item):
    return {
        "id": str(item.id),
        "identifier": item.display_identifier,
        "equipment_type": item.equipment_type.name,
        "administrative_status": item.administrative_status,
        "administrative_status_label": item.get_administrative_status_display(),
        "condition": item.condition,
        "condition_label": item.get_condition_display(),
        "condition_reason": item.condition_reason,
        "availability": item.availability,
        "availability_label": item.get_availability_display(),
        "current_holder": (
            {"id": str(item.current_holder_id), "name": str(item.current_holder)}
            if item.current_holder_id
            else None
        ),
    }


def _item_resource(request, item, *, include_events=False):
    organization = request.user.organization
    resource = {
        **_item_summary(item),
        "unit": {"id": str(item.unit_id), "code": item.unit.code, "name": item.unit.name},
        "storage_location": {
            "id": str(item.storage_location_id),
            "code": item.storage_location.code,
            "name": item.storage_location.name,
        },
        "permissions": {
            "can_move": has_permission(request.user, MOVE_ITEM, organization, item.unit),
            "can_set_condition": has_permission(
                request.user, SET_ITEM_CONDITION, organization, item.unit
            ),
        },
    }
    if include_events:
        resource["events"] = [
            {
                "id": str(event.id),
                "type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
                "actor": event.actor.username,
            }
            for event in item.events.select_related("actor").all()
        ]
    return resource


def _context(request):
    return CommandContext(request.user, _organization(request), request.correlation_id)


@ensure_csrf_cookie
@api_view(methods={"GET"})
def session_detail(request):
    organization = _organization(request)
    return _response(
        {
            "user": {"id": str(request.user.id), "username": request.user.username},
            "organization": {"id": str(organization.id), "name": organization.name},
        }
    )


@api_view(methods={"POST"})
def session_logout(request):
    logout(request)
    return _response(None)


@api_view(methods={"GET"})
def item_list(request):
    organization = _organization(request)
    candidate_items = (
        Item.objects.filter(organization=organization)
        .select_related("equipment_type", "unit", "storage_location", "current_holder")
        .order_by("equipment_type__name", "serial_number", "id")
    )
    items = [
        _item_summary(item)
        for item in candidate_items
        if has_permission(request.user, VIEW_ITEM, organization, item.unit)
    ]
    return _response(items, meta={"count": len(items)})


@api_view(methods={"GET"})
def item_detail(request, pk):
    return _response(_item_resource(request, _item(request, pk), include_events=True))


@api_view(methods={"GET"})
def recipient_list(request, pk):
    organization = _organization(request)
    _item(request, pk, MOVE_ITEM)
    people = (
        Person.objects.filter(
            organization=organization, is_active=True, memberships__is_active=True
        )
        .distinct()
        .order_by("functional_name", "name", "id")
    )
    return _response([{"id": str(person.id), "name": str(person)} for person in people])


@api_view(methods={"POST"})
def item_checkout(request, pk):
    item = _item(request, pk, MOVE_ITEM)
    payload = _parse_json(request)
    movement, created = checkout_item(
        _context(request),
        item_id=item.id,
        recipient_id=_required_uuid(payload, "recipient_id"),
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
    )
    item.refresh_from_db()
    return _response(
        {
            "movement_id": str(movement.id),
            "created": created,
            "item": _item_resource(request, item),
        },
        status=201 if created else 200,
    )


@api_view(methods={"POST"})
def item_return(request, pk):
    item = _item(request, pk, MOVE_ITEM)
    payload = _parse_json(request)
    movement, created = return_item(
        _context(request),
        item_id=item.id,
        condition=_string(payload, "condition", max_length=16),
        reason=_string(payload, "reason"),
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
    )
    item.refresh_from_db()
    return _response(
        {
            "movement_id": str(movement.id),
            "created": created,
            "item": _item_resource(request, item),
        },
        status=201 if created else 200,
    )


@api_view(methods={"POST"})
def item_condition(request, pk):
    item = _item(request, pk, SET_ITEM_CONDITION)
    payload = _parse_json(request)
    movement, created = set_item_condition(
        _context(request),
        item_id=item.id,
        condition=_string(payload, "condition", max_length=16),
        reason=_string(payload, "reason"),
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
    )
    item.refresh_from_db()
    return _response(
        {
            "movement_id": str(movement.id),
            "created": created,
            "item": _item_resource(request, item),
        },
        status=201 if created else 200,
    )
