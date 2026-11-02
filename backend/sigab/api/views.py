import json
from functools import wraps
from json import JSONDecodeError
from uuid import UUID

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.views import defaults
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.csrf import ensure_csrf_cookie

from sigab.models import Item, Membership, Person, Unit
from sigab.observability import correlation_id_var
from sigab.permissions import (
    ALL_UNITS,
    MANAGE_IDENTITY,
    MOVE_ITEM,
    SET_ITEM_CONDITION,
    VIEW_ITEM,
    has_permission,
    permitted_unit_ids,
)
from sigab.services import (
    CommandContext,
    ConflictError,
    NotFoundError,
    checkout_item,
    create_account,
    create_membership,
    create_person,
    reactivate_account,
    return_item,
    revoke_account,
    set_item_condition,
    set_membership_active,
    set_person_active,
    suspend_account,
    update_person,
)

MAX_JSON_BODY_BYTES = 16 * 1024
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


def _response(data=None, *, status=200, meta=None):
    payload = {"success": True, "data": data}
    if meta is not None:
        payload["meta"] = meta
    return JsonResponse(payload, status=status)


def _error(message, *, status, details=None):
    payload = {"success": False, "error": message, "correlation_id": correlation_id_var.get()}
    if details:
        payload["details"] = details
    return JsonResponse(payload, status=status)


def _validation_details(exc):
    if hasattr(exc, "error_dict"):
        return {
            "non_field_errors" if field == "__all__" else field: messages
            for field, messages in exc.message_dict.items()
        }
    return {"non_field_errors": exc.messages}


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
            except (Http404, NotFoundError):
                return _error("Recurso não encontrado.", status=404)
            except PermissionDenied:
                return _error("Acesso negado.", status=403)
            except ConflictError as exc:
                return _error(_validation_message(exc), status=409)
            except IntegrityError:
                # A concurrent request won a unique constraint; the client may reload and retry.
                return _error("A operação conflita com outro registro.", status=409)
            except (JSONDecodeError, UnicodeDecodeError):
                return _error("JSON inválido.", status=400)
            except ValidationError as exc:
                return _error("Dados inválidos.", status=400, details=_validation_details(exc))

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


def _required_string(payload, field, *, max_length=200):
    value = _string(payload, field, max_length=max_length)
    if not value.strip():
        raise ValidationError({field: "Campo obrigatório."})
    return value


def _boolean(payload, field):
    value = payload.get(field)
    if not isinstance(value, bool):
        raise ValidationError({field: "Informe verdadeiro ou falso."})
    return value


def _page(request):
    try:
        limit = int(request.GET.get("limit", DEFAULT_PAGE_SIZE))
        offset = int(request.GET.get("offset", 0))
    except ValueError as exc:
        raise ValidationError("Paginação inválida.") from exc
    if not 1 <= limit <= MAX_PAGE_SIZE or offset < 0:
        raise ValidationError(f"Use limit entre 1 e {MAX_PAGE_SIZE} e offset não negativo.")
    return limit, offset


def _paginated(request, queryset, serialize):
    limit, offset = _page(request)
    count = queryset.count()
    rows = [serialize(row) for row in queryset[offset : offset + limit]]
    return _response(rows, meta={"count": count, "limit": limit, "offset": offset})


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


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return _error(
            "A validação de segurança expirou. Atualize a página e tente novamente.", status=403
        )
    return django_csrf_failure(request, reason=reason)


def server_error(request):
    if request.path.startswith("/api/"):
        return _error("Erro interno. Informe o código de correlação ao suporte.", status=500)
    return defaults.server_error(request)


def not_found(request, path=""):
    return _error("Recurso não encontrado.", status=404)


@ensure_csrf_cookie
@api_view(methods={"GET"})
def session_detail(request):
    organization = _organization(request)
    return _response(
        {
            "user": {"id": str(request.user.id), "username": request.user.username},
            "organization": {"id": str(organization.id), "name": organization.name},
            "permissions": {
                "can_manage_identity": has_permission(request.user, MANAGE_IDENTITY, organization),
            },
        }
    )


@api_view(methods={"POST"})
def session_logout(request):
    logout(request)
    return _response(None)


@api_view(methods={"GET"})
def item_list(request):
    organization = _organization(request)
    items = Item.objects.filter(organization=organization)
    unit_ids = permitted_unit_ids(request.user, VIEW_ITEM, organization)
    if unit_ids is not ALL_UNITS:
        items = items.filter(unit_id__in=unit_ids)
    items = items.select_related(
        "equipment_type", "unit", "storage_location", "current_holder"
    ).order_by("equipment_type__name", "serial_number", "id")
    return _paginated(request, items, _item_summary)


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


def _movement_response(request, item, movement, created):
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
    return _movement_response(request, item, movement, created)


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
    return _movement_response(request, item, movement, created)


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
    return _movement_response(request, item, movement, created)


# Identity (SIGAB-019/020). Every endpoint requires identity.manage at organization scope.


def _identity_organization(request):
    organization = _organization(request)
    if not has_permission(request.user, MANAGE_IDENTITY, organization):
        raise PermissionDenied
    return organization


def _masked_cpf(cpf):
    # CPF is write-only through the API: only presence and the last two digits are shown.
    return f"***.***.***-{cpf[-2:]}" if cpf else ""


def _account_resource(account):
    return {
        "id": str(account.id),
        "username": account.username,
        "email": account.email,
        "status": account.status,
        "last_login": account.last_login.isoformat() if account.last_login else None,
        "revoked_at": account.revoked_at.isoformat() if account.revoked_at else None,
    }


def _membership_resource(membership):
    return {
        "id": str(membership.id),
        "registration": membership.registration,
        "rank": membership.rank,
        "is_active": membership.is_active,
        "main_unit": {
            "id": str(membership.main_unit_id),
            "code": membership.main_unit.code,
            "name": membership.main_unit.name,
        },
    }


def _person_summary(person):
    active = [m for m in person.memberships.all() if m.is_active]
    return {
        "id": str(person.id),
        "name": person.name,
        "functional_name": person.functional_name,
        "is_active": person.is_active,
        "registrations": [m.registration for m in active],
        "has_account": any(a.revoked_at is None for a in person.accounts.all()),
    }


def _person_resource(person):
    accounts = sorted(person.accounts.all(), key=lambda a: a.date_joined, reverse=True)
    return {
        "id": str(person.id),
        "name": person.name,
        "functional_name": person.functional_name,
        "phone": person.phone,
        "cpf_masked": _masked_cpf(person.cpf),
        "is_active": person.is_active,
        "memberships": [
            _membership_resource(m)
            for m in sorted(person.memberships.all(), key=lambda m: m.created_at)
        ],
        "accounts": [_account_resource(a) for a in accounts],
    }


def _people(organization):
    return Person.objects.filter(organization=organization).prefetch_related(
        "accounts", "memberships__main_unit"
    )


def _person(request, pk):
    person = _people(_identity_organization(request)).filter(pk=pk).first()
    if not person:
        raise Http404
    return person


@api_view(methods={"GET", "POST"})
def person_list(request):
    organization = _identity_organization(request)
    if request.method == "POST":
        payload = _parse_json(request)
        person = create_person(
            _context(request),
            name=_required_string(payload, "name", max_length=180),
            functional_name=_string(payload, "functional_name", max_length=120),
            cpf=_string(payload, "cpf", max_length=14),
            phone=_string(payload, "phone", max_length=24),
        )
        return _response(_person_resource(_person(request, person.pk)), status=201)
    people = _people(organization)
    query = request.GET.get("q", "").strip()
    if query:
        people = people.filter(
            Q(name__icontains=query)
            | Q(functional_name__icontains=query)
            | Q(memberships__registration__icontains=query)
        ).distinct()
    return _paginated(request, people.order_by("name", "id"), _person_summary)


@api_view(methods={"GET", "PATCH"})
def person_detail(request, pk):
    person = _person(request, pk)
    if request.method == "PATCH":
        payload = _parse_json(request)
        values = {}
        for field, max_length in (
            ("name", 180),
            ("functional_name", 120),
            ("cpf", 14),
            ("phone", 24),
        ):
            if field in payload:
                values[field] = _string(payload, field, max_length=max_length)
        unknown = sorted(set(payload) - {"name", "functional_name", "cpf", "phone"})
        if unknown:
            raise ValidationError({field: "Campo não editável." for field in unknown})
        update_person(_context(request), person_id=person.id, values=values)
        person = _person(request, pk)
    return _response(_person_resource(person))


@api_view(methods={"POST"})
def person_status(request, pk):
    person = _person(request, pk)
    payload = _parse_json(request)
    set_person_active(
        _context(request),
        person_id=person.id,
        is_active=_boolean(payload, "is_active"),
        confirmed=_required_confirmation(payload),
        reason=_string(payload, "reason"),
    )
    return _response(_person_resource(_person(request, pk)))


@api_view(methods={"POST"})
def person_memberships(request, pk):
    person = _person(request, pk)
    payload = _parse_json(request)
    create_membership(
        _context(request),
        person_id=person.id,
        registration=_required_string(payload, "registration", max_length=64),
        main_unit_id=_required_uuid(payload, "main_unit_id"),
        rank=_string(payload, "rank", max_length=80),
    )
    return _response(_person_resource(_person(request, pk)), status=201)


@api_view(methods={"POST"})
def person_account(request, pk):
    person = _person(request, pk)
    payload = _parse_json(request)
    create_account(
        _context(request),
        person_id=person.id,
        username=_required_string(payload, "username", max_length=150),
        password=_required_string(payload, "password", max_length=128),
        email=_string(payload, "email", max_length=254),
    )
    return _response(_person_resource(_person(request, pk)), status=201)


@api_view(methods={"POST"})
def membership_status(request, pk):
    organization = _identity_organization(request)
    membership = Membership.objects.filter(pk=pk, organization=organization).first()
    if not membership:
        raise Http404
    payload = _parse_json(request)
    set_membership_active(
        _context(request),
        membership_id=membership.id,
        is_active=_boolean(payload, "is_active"),
        confirmed=_required_confirmation(payload),
        reason=_string(payload, "reason"),
    )
    return _response(_person_resource(_person(request, membership.person_id)))


ACCOUNT_ACTIONS = {
    "suspend": suspend_account,
    "reactivate": reactivate_account,
    "revoke": revoke_account,
}


@api_view(methods={"POST"})
def account_action(request, pk, action):
    _identity_organization(request)
    payload = _parse_json(request)
    account = ACCOUNT_ACTIONS[action](
        _context(request),
        account_id=pk,
        confirmed=_required_confirmation(payload),
        reason=_string(payload, "reason"),
    )
    if not account.person_id:
        return _response(_account_resource(account))
    return _response(_person_resource(_person(request, account.person_id)))


@api_view(methods={"GET"})
def unit_list(request):
    organization = _identity_organization(request)
    units = Unit.objects.filter(organization=organization, is_active=True).order_by("code")
    return _response([{"id": str(u.id), "code": u.code, "name": u.name} for u in units])
