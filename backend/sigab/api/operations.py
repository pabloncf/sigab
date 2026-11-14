from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from sigab.domain.operations import (
    StockRequest,
    checkout_basket,
    positive_quantity,
    receive_stock,
    reverse_stock_entry,
    settle_stock_loan,
)
from sigab.models import EquipmentType, Item, Person, ServiceBatch, StockBalance, StockLoan, Unit
from sigab.permissions import (
    ALL_UNITS,
    MOVEMENT_CHECKOUT,
    MOVEMENT_RETURN,
    VIEW_ITEM,
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


def _optional_uuid(payload, field):
    value = payload.get(field)
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValidationError({field: "Informe um UUID válido."}) from exc


def _due_at(payload):
    value = payload.get("due_at")
    if value in (None, ""):
        return None
    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed is None or timezone.is_naive(parsed):
        raise ValidationError({"due_at": "Informe data e hora ISO 8601 com fuso."})
    return parsed


def _stock_requests(payload):
    raw = payload.get("stock", [])
    if not isinstance(raw, list):
        raise ValidationError({"stock": "Informe uma lista."})
    requests = []
    for index, line in enumerate(raw):
        if not isinstance(line, dict):
            raise ValidationError({"stock": f"Linha {index + 1} inválida."})
        requests.append(
            StockRequest(
                equipment_type_id=_required_uuid(line, "equipment_type_id"),
                unit_id=_required_uuid(line, "unit_id"),
                storage_location_id=_required_uuid(line, "storage_location_id"),
                quantity=positive_quantity(line.get("quantity")),
            )
        )
    return requests


def batch_resource(batch):
    item_lines = batch.items.select_related("item__equipment_type").order_by("item_id")
    stock_lines = batch.stock_loans.select_related("balance__equipment_type").order_by("id")
    return {
        "id": str(batch.id),
        "receipt_code": batch.receipt_code,
        "recipient": {"id": str(batch.recipient_id), "name": str(batch.recipient)},
        "operator": {"id": str(batch.operator_id), "username": batch.operator.username},
        "pickup_person": (
            {"id": str(batch.pickup_person_id), "name": str(batch.pickup_person)}
            if batch.pickup_person_id
            else None
        ),
        "custody_mode": batch.custody_mode,
        "identity_method": batch.identity_method,
        "due_at": batch.due_at.isoformat() if batch.due_at else None,
        "confirmed_at": batch.confirmed_at.isoformat(),
        "items": [
            {
                "id": str(line.item_id),
                "identifier": line.item.display_identifier,
                "equipment_type": line.item.equipment_type.name,
            }
            for line in item_lines
        ],
        "stock": [
            {
                "loan_id": str(line.id),
                "equipment_type": line.balance.equipment_type.name,
                "quantity": str(line.original_quantity),
                "open_quantity": str(line.open_quantity),
            }
            for line in stock_lines
        ],
    }


@api_view(methods={"POST"})
def service_batch_create(request):
    payload = _parse_json(request)
    raw_items = payload.get("item_ids", [])
    if not isinstance(raw_items, list):
        raise ValidationError({"item_ids": "Informe uma lista."})
    try:
        item_ids = [UUID(str(value)) for value in raw_items]
    except (TypeError, ValueError) as exc:
        raise ValidationError({"item_ids": "A lista contém UUID inválido."}) from exc
    batch, created = checkout_basket(
        _context(request),
        recipient_id=_required_uuid(payload, "recipient_id"),
        pickup_person_id=_optional_uuid(payload, "pickup_person_id"),
        item_ids=item_ids,
        stock=_stock_requests(payload),
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        custody_mode=_required_string(payload, "custody_mode", max_length=16),
        due_at=_due_at(payload),
        confirmed=_required_confirmation(payload),
        face_verification_id=_optional_uuid(payload, "face_verification_id"),
    )
    batch = ServiceBatch.objects.select_related("recipient", "pickup_person", "operator").get(
        pk=batch.pk
    )
    return _response(batch_resource(batch), status=201 if created else 200)


@api_view(methods={"POST"})
def stock_loan_settle(request, pk):
    payload = _parse_json(request)
    entry, created = settle_stock_loan(
        _context(request),
        loan_id=pk,
        quantity=payload.get("quantity"),
        disposition=_required_string(payload, "disposition", max_length=12),
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        confirmed=_required_confirmation(payload),
        reason=_string(payload, "reason", max_length=500),
    )
    return _response(
        {
            "id": str(entry.id),
            "type": entry.entry_type,
            "quantity": str(entry.quantity),
            "created": created,
        },
        status=201 if created else 200,
    )


@api_view(methods={"POST"})
def stock_entry_reverse(request, pk):
    payload = _parse_json(request)
    entry, created = reverse_stock_entry(
        _context(request),
        entry_id=pk,
        idempotency_key=_required_uuid(payload, "idempotency_key"),
        reason=_required_string(payload, "reason", max_length=500),
        confirmed=_required_confirmation(payload),
    )
    return _response(
        {"id": str(entry.id), "type": entry.entry_type, "created": created},
        status=201 if created else 200,
    )


@api_view(methods={"GET", "POST"})
def stock_positions(request):
    organization = _organization(request)
    if request.method == "POST":
        payload = _parse_json(request)
        entry, created = receive_stock(
            _context(request),
            equipment_type_id=_required_uuid(payload, "equipment_type_id"),
            unit_id=_required_uuid(payload, "unit_id"),
            storage_location_id=_required_uuid(payload, "storage_location_id"),
            quantity=payload.get("quantity"),
            idempotency_key=_required_uuid(payload, "idempotency_key"),
            reason=_required_string(payload, "reason", max_length=500),
            confirmed=_required_confirmation(payload),
        )
        entry.balance.refresh_from_db()
        return _response(
            {
                "id": str(entry.balance_id),
                "quantity": str(entry.balance.quantity),
                "created": created,
            },
            status=201 if created else 200,
        )
    allowed_units = _stock_units(request, organization)
    if not allowed_units:
        raise PermissionDenied
    balances = StockBalance.objects.filter(organization=organization).select_related(
        "equipment_type", "unit", "storage_location"
    )
    if allowed_units is not ALL_UNITS:
        balances = balances.filter(unit_id__in=allowed_units)
    return _response(
        [
            {
                "id": str(balance.id),
                "equipment_type": balance.equipment_type.name,
                "unit": {"id": str(balance.unit_id), "name": balance.unit.name},
                "storage_location": {
                    "id": str(balance.storage_location_id),
                    "name": balance.storage_location.name,
                },
                "quantity": str(balance.quantity),
            }
            for balance in balances.order_by("equipment_type__name", "unit__code")
        ]
    )


@api_view(methods={"GET"})
def service_batch_options(request):
    organization = _organization(request)
    unit_ids = permitted_unit_ids(request.user, MOVEMENT_CHECKOUT, organization)
    if not unit_ids:
        raise PermissionDenied
    items = Item.objects.filter(
        organization=organization,
        administrative_status=Item.AdministrativeStatus.ACTIVE,
        availability=Item.Availability.AVAILABLE,
        condition=Item.Condition.FIT,
    ).select_related("equipment_type", "unit")
    stock = StockBalance.objects.filter(organization=organization, quantity__gt=0).select_related(
        "equipment_type", "unit", "storage_location"
    )
    if unit_ids is not ALL_UNITS:
        items = items.filter(unit_id__in=unit_ids)
        stock = stock.filter(unit_id__in=unit_ids)
    people = (
        Person.objects.filter(
            organization=organization, is_active=True, memberships__is_active=True
        )
        .distinct()
        .order_by("functional_name", "name")
    )
    return _response(
        {
            "people": [{"id": str(person.id), "name": str(person)} for person in people],
            "items": [
                {
                    "id": str(item.id),
                    "identifier": item.display_identifier,
                    "codes": [code for code in (item.serial_number, item.asset_number) if code],
                    "equipment_type": item.equipment_type.name,
                    "unit": item.unit.name,
                }
                for item in items.order_by("equipment_type__name", "serial_number", "id")
            ],
            "stock": [
                {
                    "id": str(balance.id),
                    "equipment_type_id": str(balance.equipment_type_id),
                    "equipment_type": balance.equipment_type.name,
                    "unit_id": str(balance.unit_id),
                    "unit": balance.unit.name,
                    "storage_location_id": str(balance.storage_location_id),
                    "storage_location": balance.storage_location.name,
                    "quantity": str(balance.quantity),
                }
                for balance in stock.order_by("equipment_type__name", "unit__code")
            ],
        }
    )


def _stock_units(request, organization):
    scopes = [
        permitted_unit_ids(request.user, code, organization)
        for code in (VIEW_ITEM, MOVEMENT_RETURN, "inventory.adjust.approve")
    ]
    if any(scope is ALL_UNITS for scope in scopes):
        return ALL_UNITS
    return set().union(*scopes)


@api_view(methods={"GET"})
def stock_options(request):
    organization = _organization(request)
    unit_ids = _stock_units(request, organization)
    if not unit_ids:
        raise PermissionDenied
    units = Unit.objects.filter(organization=organization, is_active=True).prefetch_related(
        "locations"
    )
    if unit_ids is not ALL_UNITS:
        units = units.filter(pk__in=unit_ids)
    return _response(
        {
            "equipment_types": [
                {"id": str(kind.id), "name": kind.name}
                for kind in EquipmentType.objects.filter(
                    organization=organization, is_active=True, classification="quantitative"
                ).order_by("name", "id")
            ],
            "units": [
                {
                    "id": str(unit.id),
                    "name": unit.name,
                    "can_receive": has_permission(
                        request.user, "inventory.adjust.approve", organization, unit
                    ),
                    "locations": [
                        {"id": str(loc.id), "name": loc.name}
                        for loc in unit.locations.all()
                        if loc.is_active
                    ],
                }
                for unit in units.order_by("name", "id")
            ],
        }
    )


@api_view(methods={"GET"})
def stock_loans(request):
    organization = _organization(request)
    unit_ids = _stock_units(request, organization)
    if not unit_ids:
        raise PermissionDenied
    loans = StockLoan.objects.filter(organization=organization, open_quantity__gt=0).select_related(
        "recipient", "balance__equipment_type", "balance__unit", "balance__storage_location"
    )
    if unit_ids is not ALL_UNITS:
        loans = loans.filter(balance__unit_id__in=unit_ids)
    return _response(
        [
            {
                "id": str(loan.id),
                "person": str(loan.recipient),
                "equipment_type": loan.balance.equipment_type.name,
                "unit": loan.balance.unit.name,
                "location": loan.balance.storage_location.name,
                "quantity": str(loan.open_quantity),
                "can_settle": has_permission(
                    request.user, MOVEMENT_RETURN, organization, loan.balance.unit
                ),
            }
            for loan in loans.order_by("recipient__name", "balance__equipment_type__name", "id")
        ]
    )
