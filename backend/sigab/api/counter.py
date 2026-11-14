"""Counter return by person and movement register (SIGAB-082)."""

from django.core.exceptions import PermissionDenied, ValidationError

from sigab.domain.biometrics import pending_return_lines
from sigab.domain.operations import ItemReturnLine, StockReturnLine, return_basket
from sigab.domain.queries import (
    COUNTER_MOVEMENT_TYPES,
    counter_movements,
    filtered_open_possessions,
    merge_counter_movements,
)
from sigab.models import (
    Account,
    BiometricTemplate,
    EquipmentType,
    Membership,
    Person,
    ReturnBatch,
)
from sigab.permissions import (
    ALL_UNITS,
    MOVEMENT_CHECKOUT,
    MOVEMENT_RETURN,
    VIEW_ITEM,
    permitted_unit_ids,
)
from sigab.services import NotFoundError

from .operations import _optional_uuid
from .views import (
    _context,
    _date_range,
    _organization,
    _page,
    _parse_json,
    _required_confirmation,
    _required_uuid,
    _response,
    _string,
    _uuid_param,
    api_view,
)


def _scope(request, organization, permission):
    scope = permitted_unit_ids(request.user, permission, organization)
    if scope is not ALL_UNITS and not scope:
        raise PermissionDenied
    return None if scope is ALL_UNITS else scope


def _open_possessions(organization, unit_ids, person_id=None):
    items, loans = filtered_open_possessions(organization, person_id=person_id)
    if unit_ids is not None:
        items = items.filter(unit_id__in=unit_ids)
        loans = loans.filter(balance__unit_id__in=unit_ids)
    return items, loans


@api_view(methods={"GET"})
def counter_identify(request):
    """Counter entry point: find who is at the counter by exact registration (ADR 0008).

    Exact match only, so the endpoint cannot be used to browse people. Returns just what the
    operator needs to choose the operation and start the facial verification.
    """
    organization = _organization(request)
    checkout_units = permitted_unit_ids(request.user, MOVEMENT_CHECKOUT, organization)
    return_units = permitted_unit_ids(request.user, MOVEMENT_RETURN, organization)
    if not checkout_units and not return_units:
        raise PermissionDenied
    registration = request.GET.get("registration", "").strip()
    person_id = _uuid_param(request, "person")
    memberships = Membership.objects.filter(
        organization=organization, is_active=True, person__is_active=True
    )
    if person_id:
        # Reopening an identified person (counter page reload): exact id, same rules.
        memberships = memberships.filter(person_id=person_id).order_by("created_at")
    elif registration:
        if len(registration) > 64:
            raise ValidationError({"registration": "Use no máximo 64 caracteres."})
        memberships = memberships.filter(registration__iexact=registration)
    else:
        raise ValidationError({"registration": "Informe a matrícula."})
    membership = memberships.select_related("person").first()
    if not membership:
        raise NotFoundError
    person = membership.person
    # The operator never serves himself: another operator registers his operations.
    own = request.user.person_id == person.id
    possessions = 0
    if return_units:
        items, loans = _open_possessions(
            organization, None if return_units is ALL_UNITS else return_units, person.id
        )
        possessions = items.count() + loans.count()
    return _response(
        {
            "id": str(person.id),
            "name": str(person),
            "registration": membership.registration,
            "biometric_enrolled": BiometricTemplate.objects.filter(person=person).exists(),
            "open_possessions": possessions,
            "own": own,
            "operations": {
                "checkout": bool(checkout_units) and not own,
                "return": bool(return_units) and not own,
            },
        }
    )


@api_view(methods={"GET"})
def return_options(request):
    """People with open possessions the operator may receive and, for one person, the lines."""
    organization = _organization(request)
    unit_ids = _scope(request, organization, MOVEMENT_RETURN)
    items, loans = _open_possessions(organization, unit_ids)
    holder_ids = set(items.values_list("current_holder_id", flat=True))
    holder_ids.update(loans.values_list("recipient_id", flat=True))
    people = Person.objects.filter(organization=organization, pk__in=holder_ids).order_by(
        "functional_name", "name", "id"
    )
    data = {"people": [{"id": str(person.id), "name": str(person)} for person in people]}
    person_id = _uuid_param(request, "person")
    if person_id:
        items, loans = _open_possessions(organization, unit_ids, person_id)
        pending_items, pending_loans = pending_return_lines(organization, person_id)
        data["items"] = [
            {
                "id": str(item.id),
                "identifier": item.display_identifier,
                "codes": [code for code in (item.serial_number, item.asset_number) if code],
                "equipment_type": item.equipment_type.name,
                "unit": item.unit.name,
                "awaiting_approval": str(item.id) in pending_items,
            }
            for item in items.order_by("equipment_type__name", "serial_number", "id")
        ]
        data["stock"] = [
            {
                "loan_id": str(loan.id),
                "equipment_type": loan.balance.equipment_type.name,
                "unit": loan.balance.unit.name,
                "open_quantity": str(loan.open_quantity),
                "due_at": loan.due_at.isoformat() if loan.due_at else None,
                "awaiting_approval": str(loan.id) in pending_loans,
            }
            for loan in loans.order_by("balance__equipment_type__name", "id")
        ]
    return _response(data)


def _lines(payload, field):
    raw = payload.get(field, [])
    if not isinstance(raw, list):
        raise ValidationError({field: "Informe uma lista."})
    for index, line in enumerate(raw):
        if not isinstance(line, dict):
            raise ValidationError({field: f"Linha {index + 1} inválida."})
    return raw


def return_batch_resource(batch):
    item_lines = batch.items.select_related("movement__item__equipment_type").order_by("id")
    stock_lines = batch.stock_lines.select_related("entry__balance__equipment_type").order_by("id")
    return {
        "id": str(batch.id),
        "receipt_code": batch.receipt_code,
        "person": {"id": str(batch.person_id), "name": str(batch.person)},
        "operator": {"id": str(batch.operator_id), "username": batch.operator.username},
        "confirmed_at": batch.confirmed_at.isoformat(),
        "identity_method": batch.identity_method,
        "items": [
            {
                "id": str(line.movement.item_id),
                "identifier": line.movement.item.display_identifier,
                "equipment_type": line.movement.item.equipment_type.name,
                "condition": line.movement.condition_on_return,
            }
            for line in item_lines
        ],
        "stock": [
            {
                "loan_id": str(line.entry.loan_id),
                "equipment_type": line.entry.balance.equipment_type.name,
                "quantity": str(line.entry.quantity),
            }
            for line in stock_lines
        ],
    }


@api_view(methods={"POST"})
def return_batch_create(request):
    payload = _parse_json(request)
    items = [
        ItemReturnLine(
            item_id=_required_uuid(line, "item_id"),
            condition=_string(line, "condition", max_length=16),
            reason=_string(line, "reason", max_length=200),
        )
        for line in _lines(payload, "items")
    ]
    stock = [
        StockReturnLine(loan_id=_required_uuid(line, "loan_id"), quantity=line.get("quantity"))
        for line in _lines(payload, "stock")
    ]
    batch, created = return_basket(
        _context(request),
        person_id=_required_uuid(payload, "person_id"),
        items=items,
        stock=stock,
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
        face_verification_id=_optional_uuid(payload, "face_verification_id"),
    )
    batch = ReturnBatch.objects.select_related("person", "operator").get(pk=batch.pk)
    return _response(return_batch_resource(batch), status=201 if created else 200)


def _register_filters(request):
    movement_type = request.GET.get("type") or None
    if movement_type and movement_type not in COUNTER_MOVEMENT_TYPES:
        raise ValidationError({"type": "Valor inválido."})
    kind = request.GET.get("kind") or None
    if kind and kind not in ("individual", "quantitative"):
        raise ValidationError({"kind": "Valor inválido."})
    return {
        "person_id": _uuid_param(request, "person"),
        "operator_id": _uuid_param(request, "operator"),
        "equipment_type_id": _uuid_param(request, "equipment_type"),
        "movement_type": movement_type,
        "kind": kind,
    }


@api_view(methods={"GET"})
def movement_register(request):
    """Read-only register of checkouts, returns and consumption in the reader's scope."""
    organization = _organization(request)
    unit_ids = _scope(request, organization, VIEW_ITEM)
    movements, entries = counter_movements(organization, unit_ids, **_register_filters(request))
    movements = _date_range(request, movements, "confirmed_at")
    entries = _date_range(request, entries, "occurred_at")
    limit, offset = _page(request)
    return _response(
        merge_counter_movements(movements, entries, offset=offset, limit=limit),
        meta={"count": movements.count() + entries.count(), "limit": limit, "offset": offset},
    )


@api_view(methods={"GET"})
def movement_register_options(request):
    """Filter choices derived only from movements the reader can already see."""
    organization = _organization(request)
    unit_ids = _scope(request, organization, VIEW_ITEM)
    movements, entries = counter_movements(organization, unit_ids)
    people = set(movements.values_list("recipient_id", flat=True))
    people.update(entries.values_list("recipient_id", flat=True))
    operators = set(movements.values_list("operator_id", flat=True))
    operators.update(entries.values_list("operator_id", flat=True))
    types = set(movements.values_list("item__equipment_type_id", flat=True))
    types.update(entries.values_list("balance__equipment_type_id", flat=True))

    def ids(values):
        return [value for value in values if value is not None]

    return _response(
        {
            "people": [
                {"id": str(person.id), "name": str(person)}
                for person in Person.objects.filter(
                    organization=organization, pk__in=ids(people)
                ).order_by("functional_name", "name", "id")
            ],
            "operators": [
                {"id": str(account.id), "username": account.username}
                for account in Account.objects.filter(
                    organization=organization, pk__in=ids(operators)
                ).order_by("username")
            ],
            "equipment_types": [
                {"id": str(kind.id), "name": kind.name}
                for kind in EquipmentType.objects.filter(
                    organization=organization, pk__in=ids(types)
                ).order_by("name")
            ],
        }
    )
