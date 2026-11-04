import json
from functools import wraps
from json import JSONDecodeError
from uuid import UUID

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views import defaults
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.csrf import ensure_csrf_cookie

from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Item,
    Membership,
    MovementEvent,
    Person,
    Role,
    StorageLocation,
    Unit,
)
from sigab.observability import correlation_id_var
from sigab.permissions import (
    ALL_UNITS,
    AUDIT_VIEW,
    CATALOG_MANAGE,
    ITEM_CREATE,
    MANAGE_IDENTITY,
    MOVEMENT_CHECKOUT,
    MOVEMENT_RETURN,
    MOVEMENT_REVERSE,
    PERSON_VIEW_MINIMAL,
    SET_ITEM_CONDITION,
    VIEW_ITEM,
    has_any_scope,
    has_permission,
    permitted_unit_ids,
)
from sigab.services import (
    REVERSIBLE_TYPES,
    CommandContext,
    ConflictError,
    Contingency,
    DivergenceError,
    NotFoundError,
    checkout_item,
    create_account,
    create_equipment_type,
    create_grant,
    create_membership,
    create_person,
    create_storage_location,
    create_unit,
    end_account_sessions,
    incorporate_item,
    latest_movement_in_force,
    reactivate_account,
    return_item,
    reverse_movement,
    revoke_account,
    revoke_grant,
    set_equipment_type_active,
    set_item_condition,
    set_membership_active,
    set_person_active,
    set_storage_location_active,
    set_unit_active,
    suspend_account,
    update_equipment_type,
    update_person,
    update_unit,
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
                _audit_refusal(request, kwargs, "not_found")
                return _error("Recurso não encontrado.", status=404)
            except PermissionDenied:
                _audit_refusal(request, kwargs, "denied")
                return _error("Acesso negado.", status=403)
            except DivergenceError as exc:
                _audit_refusal(request, kwargs, "divergence")
                return _error(_validation_message(exc), status=409)
            except ConflictError as exc:
                _audit_refusal(request, kwargs, "conflict")
                return _error(_validation_message(exc), status=409)
            except IntegrityError:
                # A concurrent request won a unique constraint; the client may reload and retry.
                _audit_refusal(request, kwargs, "conflict")
                return _error("A operação conflita com outro registro.", status=409)
            except (JSONDecodeError, UnicodeDecodeError):
                return _error("JSON inválido.", status=400)
            except ValidationError as exc:
                return _error("Dados inválidos.", status=400, details=_validation_details(exc))

        return wrapped

    return decorator


def _audit_refusal(request, kwargs, result):
    """Audit refused writes (T-04): denied, missing or conflicting targets leave a trace."""
    if request.method in ("GET", "HEAD", "OPTIONS") or not request.user.organization_id:
        return
    match = request.resolver_match
    AuditEvent.objects.create(
        organization_id=request.user.organization_id,
        actor=request.user,
        action=f"api.{match.url_name if match else 'unknown'}",
        object_type="api.request",
        object_id=str(kwargs.get("pk", ""))[:64],
        occurred_at=timezone.now(),
        correlation_id=request.correlation_id,
        result=result,
        changes={},
    )


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


def _item_resource(request, item):
    organization = request.user.organization
    resource = {
        **_item_summary(item),
        "unit": {"id": str(item.unit_id), "code": item.unit.code, "name": item.unit.name},
        "storage_location": {
            "id": str(item.storage_location_id),
            "code": item.storage_location.code,
            "name": item.storage_location.name,
        },
        "serial_number": item.serial_number,
        "asset_number": item.asset_number,
        "official_identifier": item.official_identifier,
        "reversible_movement_id": _reversible_movement_id(request, item),
        "permissions": {
            "can_checkout": has_permission(
                request.user, MOVEMENT_CHECKOUT, organization, item.unit
            ),
            "can_return": has_permission(request.user, MOVEMENT_RETURN, organization, item.unit),
            "can_reverse": has_permission(request.user, MOVEMENT_REVERSE, organization, item.unit),
            "can_set_condition": has_permission(
                request.user, SET_ITEM_CONDITION, organization, item.unit
            ),
        },
    }
    return resource


def _reversible_movement_id(request, item):
    if not has_permission(request.user, MOVEMENT_REVERSE, item.organization, item.unit):
        return None
    latest = latest_movement_in_force(item)
    if latest is None or latest.movement_type not in REVERSIBLE_TYPES:
        return None
    return str(latest.id)


def _event_resource(event):
    movement = event.movement
    return {
        "id": str(event.id),
        "type": event.event_type,
        "occurred_at": event.occurred_at.isoformat(),
        "actor": event.actor.username,
        "movement": {
            "id": str(movement.id),
            "type": movement.movement_type,
            "recipient": (
                {"id": str(movement.recipient_id), "name": str(movement.recipient)}
                if movement.recipient_id
                else None
            ),
            "condition": movement.condition_on_return or movement.new_condition or None,
            "reason": movement.reason or movement.condition_reason,
            "reverses": str(movement.reverses_id) if movement.reverses_id else None,
            "reversed": hasattr(movement, "reversal"),
            "origin": movement.origin,
            "paper_reference": movement.paper_reference,
            "recorded_at": movement.confirmed_at.isoformat(),
        },
    }


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
                "can_manage_catalog": has_permission(request.user, CATALOG_MANAGE, organization),
                "can_create_item": has_any_scope(request.user, ITEM_CREATE, organization),
                "can_view_items": has_any_scope(request.user, VIEW_ITEM, organization),
                "can_view_audit": has_permission(request.user, AUDIT_VIEW, organization),
            },
        }
    )


@api_view(methods={"POST"})
def session_logout(request):
    logout(request)
    return _response(None)


@api_view(methods={"GET", "POST"})
def item_list(request):
    organization = _organization(request)
    if request.method == "POST":
        payload = _parse_json(request)
        item = incorporate_item(
            _context(request),
            equipment_type_id=_required_uuid(payload, "equipment_type_id"),
            unit_id=_required_uuid(payload, "unit_id"),
            storage_location_id=_required_uuid(payload, "storage_location_id"),
            serial_number=_string(payload, "serial_number", max_length=100),
            asset_number=_string(payload, "asset_number", max_length=100),
            official_identifier=_string(payload, "official_identifier", max_length=100),
            condition=_string(payload, "condition", max_length=16) or Item.Condition.FIT,
            condition_reason=_string(payload, "condition_reason"),
            confirmed=_required_confirmation(payload),
        )
        return _response(_item_resource(request, _item(request, item.pk)), status=201)
    items = Item.objects.filter(organization=organization)
    items = _filter_items(request, items)
    unit_ids = permitted_unit_ids(request.user, VIEW_ITEM, organization)
    if unit_ids is not ALL_UNITS:
        items = items.filter(unit_id__in=unit_ids)
    items = items.select_related(
        "equipment_type", "unit", "storage_location", "current_holder"
    ).order_by("equipment_type__name", "serial_number", "id")
    return _paginated(request, items, _item_summary)


@api_view(methods={"GET"})
def item_detail(request, pk):
    return _response(_item_resource(request, _item(request, pk)))


@api_view(methods={"GET"})
def item_events(request, pk):
    """Confirmed facts of the item in chronological order (RF-15, RF-53); read only."""
    item = _item(request, pk)
    events = (
        MovementEvent.objects.filter(item=item, organization=item.organization)
        .select_related("actor", "movement", "movement__recipient", "movement__reversal")
        .order_by("occurred_at", "id")
    )
    return _paginated(request, events, _event_resource)


@api_view(methods={"POST"})
def movement_reverse(request, pk):
    """Compensating reversal of a checkout, return or condition change (SIGAB-034)."""
    organization = _organization(request)
    payload = _parse_json(request)
    reversal, created = reverse_movement(
        _context(request),
        movement_id=pk,
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
        reason=_required_string(payload, "reason", max_length=500),
    )
    item = Item.objects.select_related(
        "equipment_type", "unit", "storage_location", "current_holder"
    ).get(pk=reversal.item_id, organization=organization)
    return _movement_response(request, item, reversal, created)


@api_view(methods={"GET"})
def recipient_list(request, pk):
    organization = _organization(request)
    _item(request, pk, MOVEMENT_CHECKOUT)
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


def _contingency(payload):
    """Optional paper record being reconciled (SIGAB-046); absent for a live registration."""
    value = payload.get("contingency")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationError({"contingency": "Informe um objeto."})
    occurred_at = _optional_datetime(value, "occurred_at")
    if occurred_at is None:
        raise ValidationError({"occurred_at": "Campo obrigatório."})
    return Contingency(
        occurred_at=occurred_at,
        paper_reference=_required_string(value, "paper_reference", max_length=64),
    )


@api_view(methods={"POST"})
def item_checkout(request, pk):
    item = _item(request, pk, MOVEMENT_CHECKOUT)
    payload = _parse_json(request)
    movement, created = checkout_item(
        _context(request),
        item_id=item.id,
        recipient_id=_required_uuid(payload, "recipient_id"),
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
        contingency=_contingency(payload),
    )
    return _movement_response(request, item, movement, created)


@api_view(methods={"POST"})
def item_return(request, pk):
    item = _item(request, pk, MOVEMENT_RETURN)
    payload = _parse_json(request)
    movement, created = return_item(
        _context(request),
        item_id=item.id,
        condition=_string(payload, "condition", max_length=16),
        reason=_string(payload, "reason"),
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
        contingency=_contingency(payload),
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


def _grant_resource(grant):
    return {
        "id": str(grant.id),
        "role": {"id": str(grant.role_id), "name": grant.role.name},
        "scope_type": grant.scope_type,
        "unit": (
            {"id": str(grant.unit_id), "code": grant.unit.code, "name": grant.unit.name}
            if grant.unit_id
            else None
        ),
        "valid_from": grant.valid_from.isoformat() if grant.valid_from else None,
        "valid_until": grant.valid_until.isoformat() if grant.valid_until else None,
        "active": grant.is_active and grant.revoked_at is None,
    }


def _account_resource(account):
    return {
        "id": str(account.id),
        "username": account.username,
        "email": account.email,
        "status": account.status,
        "last_login": account.last_login.isoformat() if account.last_login else None,
        "revoked_at": account.revoked_at.isoformat() if account.revoked_at else None,
        "grants": [
            _grant_resource(grant)
            for grant in sorted(account.grants.all(), key=lambda g: g.created_at)
            if grant.is_active and grant.revoked_at is None
        ],
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
        "accounts__grants__role", "accounts__grants__unit", "memberships__main_unit"
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


ACCOUNT_ACTIONS["end-sessions"] = end_account_sessions


def _optional_datetime(payload, field):
    value = payload.get(field)
    if value in (None, ""):
        return None
    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed is None or parsed.tzinfo is None:
        raise ValidationError({field: "Informe data e hora ISO 8601 com fuso."})
    return parsed


@api_view(methods={"GET"})
def role_list(request):
    organization = _identity_organization(request)
    roles = Role.objects.filter(organization=organization).order_by("name")
    return _response(
        [
            {
                "id": str(role.id),
                "name": role.name,
                "permissions": sorted(role.permissions),
                "allowed_scopes": role.allowed_scopes,
            }
            for role in roles
        ]
    )


@api_view(methods={"POST"})
def account_grants(request, pk):
    _identity_organization(request)
    payload = _parse_json(request)
    grant = create_grant(
        _context(request),
        account_id=pk,
        role_id=_required_uuid(payload, "role_id"),
        scope_type=_required_string(payload, "scope_type", max_length=20),
        unit_id=_required_uuid(payload, "unit_id") if payload.get("unit_id") else None,
        valid_from=_optional_datetime(payload, "valid_from"),
        valid_until=_optional_datetime(payload, "valid_until"),
        reason=_required_string(payload, "reason"),
    )
    return _account_or_person_response(request, grant.account, status=201)


@api_view(methods={"POST"})
def grant_revoke(request, pk):
    _identity_organization(request)
    payload = _parse_json(request)
    grant = revoke_grant(
        _context(request),
        grant_id=pk,
        confirmed=_required_confirmation(payload),
        reason=_required_string(payload, "reason"),
    )
    return _account_or_person_response(request, grant.account)


def _account_or_person_response(request, account, status=200):
    if account.person_id:
        return _response(_person_resource(_person(request, account.person_id)), status=status)
    account = Account.objects.prefetch_related("grants__role", "grants__unit").get(pk=account.pk)
    return _response(_account_resource(account), status=status)


# Organization structure and catalog (SIGAB-024/026).


def _can_read_structure(request, organization):
    return any(
        (
            has_permission(request.user, MANAGE_IDENTITY, organization),
            has_permission(request.user, CATALOG_MANAGE, organization),
            has_any_scope(request.user, ITEM_CREATE, organization),
        )
    )


def _location_resource(location):
    return {
        "id": str(location.id),
        "code": location.code,
        "name": location.name,
        "is_active": location.is_active,
    }


def _unit_resource(unit):
    return {
        "id": str(unit.id),
        "code": unit.code,
        "name": unit.name,
        "is_active": unit.is_active,
        "locations": [
            _location_resource(location)
            for location in sorted(unit.locations.all(), key=lambda loc: loc.code)
        ],
    }


def _units(organization):
    return Unit.objects.filter(organization=organization).prefetch_related("locations")


def _catalog_object(model, request, pk):
    organization = _organization(request)
    if not has_permission(request.user, CATALOG_MANAGE, organization):
        raise PermissionDenied
    instance = model.objects.filter(pk=pk, organization=organization).first()
    if not instance:
        raise Http404
    return instance


@api_view(methods={"GET", "POST"})
def unit_list(request):
    organization = _organization(request)
    if request.method == "POST":
        payload = _parse_json(request)
        unit = create_unit(
            _context(request),
            code=_required_string(payload, "code", max_length=40),
            name=_required_string(payload, "name", max_length=160),
        )
        return _response(_unit_resource(_units(organization).get(pk=unit.pk)), status=201)
    if not _can_read_structure(request, organization):
        raise PermissionDenied
    return _response([_unit_resource(unit) for unit in _units(organization).order_by("code")])


@api_view(methods={"PATCH"})
def unit_detail(request, pk):
    unit = _catalog_object(Unit, request, pk)
    payload = _parse_json(request)
    update_unit(
        _context(request), unit_id=unit.id, name=_required_string(payload, "name", max_length=160)
    )
    return _response(_unit_resource(_units(unit.organization).get(pk=unit.pk)))


@api_view(methods={"POST"})
def unit_status(request, pk):
    unit = _catalog_object(Unit, request, pk)
    payload = _parse_json(request)
    set_unit_active(
        _context(request),
        unit_id=unit.id,
        is_active=_boolean(payload, "is_active"),
        confirmed=_required_confirmation(payload),
        reason=_string(payload, "reason"),
    )
    return _response(_unit_resource(_units(unit.organization).get(pk=unit.pk)))


@api_view(methods={"POST"})
def unit_locations(request, pk):
    unit = _catalog_object(Unit, request, pk)
    payload = _parse_json(request)
    create_storage_location(
        _context(request),
        unit_id=unit.id,
        code=_required_string(payload, "code", max_length=40),
        name=_required_string(payload, "name", max_length=120),
    )
    return _response(_unit_resource(_units(unit.organization).get(pk=unit.pk)), status=201)


@api_view(methods={"POST"})
def location_status(request, pk):
    location = _catalog_object(StorageLocation, request, pk)
    payload = _parse_json(request)
    set_storage_location_active(
        _context(request),
        location_id=location.id,
        is_active=_boolean(payload, "is_active"),
        confirmed=_required_confirmation(payload),
        reason=_string(payload, "reason"),
    )
    return _response(_unit_resource(_units(location.organization).get(pk=location.unit_id)))


def _type_resource(equipment_type):
    return {
        "id": str(equipment_type.id),
        "name": equipment_type.name,
        "description": equipment_type.description,
        "classification": equipment_type.classification,
        "classification_label": equipment_type.get_classification_display(),
        "is_active": equipment_type.is_active,
    }


@api_view(methods={"GET", "POST"})
def equipment_type_list(request):
    organization = _organization(request)
    if request.method == "POST":
        payload = _parse_json(request)
        equipment_type = create_equipment_type(
            _context(request),
            name=_required_string(payload, "name", max_length=160),
            classification=_required_string(payload, "classification", max_length=16),
            description=_string(payload, "description", max_length=2000),
        )
        return _response(_type_resource(equipment_type), status=201)
    if not (
        has_permission(request.user, CATALOG_MANAGE, organization)
        or has_any_scope(request.user, ITEM_CREATE, organization)
    ):
        raise PermissionDenied
    types = EquipmentType.objects.filter(organization=organization).order_by("name")
    return _response([_type_resource(t) for t in types])


@api_view(methods={"PATCH"})
def equipment_type_detail(request, pk):
    equipment_type = _catalog_object(EquipmentType, request, pk)
    payload = _parse_json(request)
    if "classification" in payload:
        raise ValidationError({"classification": "A classificação não pode ser alterada."})
    unknown = sorted(set(payload) - {"name", "description"})
    if unknown:
        raise ValidationError({field: "Campo não editável." for field in unknown})
    equipment_type = update_equipment_type(
        _context(request),
        type_id=equipment_type.id,
        name=_string(payload, "name", max_length=160) or equipment_type.name,
        description=_string(payload, "description", max_length=2000)
        if "description" in payload
        else equipment_type.description,
    )
    return _response(_type_resource(equipment_type))


@api_view(methods={"POST"})
def equipment_type_status(request, pk):
    equipment_type = _catalog_object(EquipmentType, request, pk)
    payload = _parse_json(request)
    equipment_type = set_equipment_type_active(
        _context(request),
        type_id=equipment_type.id,
        is_active=_boolean(payload, "is_active"),
        confirmed=_required_confirmation(payload),
        reason=_string(payload, "reason"),
    )
    return _response(_type_resource(equipment_type))


# Search (SIGAB-038, RF-50), activity feed (SIGAB-036, RF-61) and audit trail (SIGAB-035).

ITEM_FILTERS = {
    "availability": Item.Availability.values,
    "condition": Item.Condition.values,
}


def _uuid_param(request, name):
    value = request.GET.get(name)
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValidationError({name: "Informe um UUID válido."}) from exc


def _filter_items(request, items):
    holder = _uuid_param(request, "holder")
    if holder:
        # RF-51: current possession of a person.
        items = items.filter(current_holder_id=holder)
    for name, allowed in ITEM_FILTERS.items():
        value = request.GET.get(name)
        if value:
            if value not in allowed:
                raise ValidationError({name: "Valor inválido."})
            items = items.filter(**{name: value})
    for name, field in (("unit", "unit_id"), ("type", "equipment_type_id")):
        value = _uuid_param(request, name)
        if value:
            items = items.filter(**{field: value})
    query = request.GET.get("q", "").strip()[:100]
    if query:
        items = items.filter(
            Q(serial_number__icontains=query)
            | Q(asset_number__icontains=query)
            | Q(official_identifier__icontains=query)
            | Q(equipment_type__name__icontains=query)
            | Q(unit__code__icontains=query)
            | Q(unit__name__icontains=query)
            | Q(current_holder__name__icontains=query)
            | Q(current_holder__functional_name__icontains=query)
        )
    return items


@api_view(methods={"GET"})
def search(request):
    """Single search box (RF-50): items in the reader's scope and people, minimally."""
    organization = _organization(request)
    query = request.GET.get("q", "").strip()[:100]
    if len(query) < 2:
        raise ValidationError({"q": "Informe ao menos 2 caracteres."})
    unit_ids = permitted_unit_ids(request.user, VIEW_ITEM, organization)
    items = Item.objects.filter(organization=organization)
    if unit_ids is not ALL_UNITS:
        items = items.filter(unit_id__in=unit_ids)
    items = _filter_items(request, items).select_related(
        "equipment_type", "unit", "storage_location", "current_holder"
    )
    people = []
    if has_any_scope(request.user, PERSON_VIEW_MINIMAL, organization):
        matches = (
            Person.objects.filter(organization=organization)
            .filter(
                Q(name__icontains=query)
                | Q(functional_name__icontains=query)
                | Q(memberships__registration__icontains=query)
            )
            .prefetch_related("memberships")
            .distinct()
            .order_by("name", "id")[:20]
        )
        # person.view_minimal: identification only, never CPF or phone.
        people = [
            {
                "id": str(person.id),
                "name": str(person),
                "is_active": person.is_active,
                "registrations": [m.registration for m in person.memberships.all() if m.is_active],
            }
            for person in matches
        ]
    limit, offset = _page(request)
    item_rows = items.order_by("equipment_type__name", "serial_number", "id")
    return _response(
        {
            "items": [_item_summary(item) for item in item_rows[offset : offset + limit]],
            "people": people,
        },
        meta={"items_count": item_rows.count(), "limit": limit, "offset": offset},
    )


def _date_range(request, queryset, field):
    for name, lookup in (("from", "gte"), ("to", "lte")):
        value = request.GET.get(name)
        if value:
            day = parse_date(value)
            if day is None:
                raise ValidationError({name: "Use a data no formato AAAA-MM-DD."})
            queryset = queryset.filter(**{f"{field}__date__{lookup}": day})
    return queryset


@api_view(methods={"GET"})
def activity_feed(request):
    """Read-only projection of domain events; it never replaces the audit trail (RF-61)."""
    organization = _organization(request)
    unit_ids = permitted_unit_ids(request.user, VIEW_ITEM, organization)
    if unit_ids is not ALL_UNITS and not unit_ids:
        raise PermissionDenied
    events = MovementEvent.objects.filter(organization=organization)
    if unit_ids is not ALL_UNITS:
        events = events.filter(item__unit_id__in=unit_ids)
    person = _uuid_param(request, "person")
    if person:
        events = events.filter(
            Q(movement__recipient_id=person) | Q(movement__reverses__recipient_id=person)
        )
    item = _uuid_param(request, "item")
    if item:
        events = events.filter(item_id=item)
    action = request.GET.get("action")
    if action:
        events = events.filter(event_type=action)
    events = _date_range(request, events, "occurred_at").select_related(
        "actor", "item__equipment_type", "movement", "movement__recipient", "movement__reversal"
    )

    def row(event):
        return {
            **_event_resource(event),
            "item": {
                "id": str(event.item_id),
                "identifier": event.item.display_identifier,
                "equipment_type": event.item.equipment_type.name,
            },
        }

    return _paginated(request, events.order_by("-occurred_at", "-id"), row)


@api_view(methods={"GET"})
def audit_trail(request):
    """Audit events of the organization; read only, for audit.view at organization scope."""
    organization = _organization(request)
    if not has_permission(request.user, AUDIT_VIEW, organization):
        raise PermissionDenied
    events = AuditEvent.objects.filter(organization=organization)
    for name in ("action", "result", "object_id"):
        value = request.GET.get(name)
        if value:
            events = events.filter(**{name: value})
    actor = _uuid_param(request, "actor")
    if actor:
        events = events.filter(actor_id=actor)
    events = _date_range(request, events, "occurred_at").select_related("actor")

    def row(event):
        return {
            "id": str(event.id),
            "sequence": event.sequence,
            "occurred_at": event.occurred_at.isoformat(),
            "actor": event.actor.username if event.actor_id else None,
            "action": event.action,
            "object_type": event.object_type,
            "object_id": event.object_id,
            "result": event.result,
            "changes": event.changes,
            "reason": event.reason,
            "correlation_id": event.correlation_id,
        }

    return _paginated(request, events.order_by("-occurred_at", "-id"), row)
