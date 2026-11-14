from decimal import Decimal

from django.db.models import Count, Q, Sum

from sigab.models import Item, Movement, StockBalance, StockLedgerEntry, StockLoan


def possessions_for_person(organization, person):
    items = (
        Item.objects.filter(
            organization=organization,
            current_holder=person,
            availability=Item.Availability.IN_CUSTODY,
        )
        .select_related("equipment_type", "unit")
        .order_by("equipment_type__name", "id")
    )
    stock = (
        StockLoan.objects.filter(
            organization=organization,
            recipient=person,
            open_quantity__gt=0,
        )
        .select_related("balance__equipment_type", "balance__unit", "batch")
        .order_by("due_at", "id")
    )
    return items, stock


def history_for_person(organization, person):
    movements = (
        Movement.objects.filter(organization=organization, recipient=person)
        .select_related("item__equipment_type", "operator", "reverses")
        .order_by("-confirmed_at", "-id")
    )
    stock = (
        StockLedgerEntry.objects.filter(organization=organization, recipient=person)
        .select_related("balance__equipment_type", "operator", "loan")
        .order_by("-occurred_at", "-id")
    )
    return movements, stock


def filtered_open_possessions(organization, *, person_id=None, unit_id=None):
    item_filter = Q(organization=organization, availability=Item.Availability.IN_CUSTODY)
    stock_filter = Q(organization=organization, open_quantity__gt=0)
    if person_id:
        item_filter &= Q(current_holder_id=person_id)
        stock_filter &= Q(recipient_id=person_id)
    if unit_id:
        item_filter &= Q(unit_id=unit_id)
        stock_filter &= Q(balance__unit_id=unit_id)
    return (
        Item.objects.filter(item_filter).select_related("equipment_type", "unit", "current_holder"),
        StockLoan.objects.filter(stock_filter).select_related(
            "balance__equipment_type", "balance__unit", "recipient", "batch"
        ),
    )


# Read models for the home page (SIGAB-079) and the split collection (SIGAB-081).
# Every function receives the unit scope already resolved by the caller; ALL_UNITS
# (or None) means organization-wide.


QUANTITY_STEP = Decimal("0.001")


def quantity(value):
    """Normalize aggregated quantities to the ledger precision (three decimal places)."""
    return (value or Decimal("0")).quantize(QUANTITY_STEP)


def _scoped(queryset, unit_ids, field):
    if unit_ids is None:
        return queryset
    return queryset.filter(**{f"{field}__in": unit_ids})


def individual_totals_by_type(organization, unit_ids):
    """Active items with registration per type and availability (RF-40, SIGAB-059)."""
    items = _scoped(
        Item.objects.filter(
            organization=organization, administrative_status=Item.AdministrativeStatus.ACTIVE
        ),
        unit_ids,
        "unit_id",
    )
    rows = {}
    for row in items.values("equipment_type_id", "equipment_type__name", "availability").annotate(
        total=Count("id")
    ):
        entry = rows.setdefault(
            row["equipment_type_id"],
            {
                "equipment_type_id": row["equipment_type_id"],
                "equipment_type": row["equipment_type__name"],
                "available": 0,
                "in_custody": 0,
                "unavailable": 0,
            },
        )
        entry[row["availability"]] = row["total"]
    return sorted(rows.values(), key=lambda value: value["equipment_type"])


def stock_positions_with_custody(organization, unit_ids, *, equipment_type_id=None):
    """Quantitative positions with reserve, open custody and total (RF-13, RF-14).

    Reserve is the ledger-derived balance; custody is the open quantity of loans taken
    from that position. Available/unfit split for quantitative material depends on
    SIGAB-008 and is not inferred here.
    """
    balances = _scoped(
        StockBalance.objects.filter(organization=organization), unit_ids, "unit_id"
    ).select_related("equipment_type", "unit", "storage_location")
    if equipment_type_id:
        balances = balances.filter(equipment_type_id=equipment_type_id)
    custody = dict(
        StockLoan.objects.filter(
            organization=organization, balance__in=balances, open_quantity__gt=0
        )
        .values("balance_id")
        .annotate(total=Sum("open_quantity"))
        .values_list("balance_id", "total")
    )
    rows = []
    for balance in balances.order_by(
        "equipment_type__name", "unit__code", "storage_location__code"
    ):
        reserve = quantity(balance.quantity)
        in_custody = quantity(custody.get(balance.id))
        rows.append((balance, reserve, in_custody, reserve + in_custody))
    return rows


COUNTER_MOVEMENT_TYPES = ("checkout", "return", "consume")


def _batch(line_owner, attribute):
    line = getattr(line_owner, attribute, None)
    return line.batch if line is not None else None


def _identity(batch, origin="system"):
    """How the person was identified (ADR 0008); never biometric data."""
    if origin == "contingency":
        return "paper_contingency"
    return batch.identity_method if batch is not None else None


def _movement_row(movement):
    batch = (
        _batch(movement, "service_batch_line")
        if movement.movement_type == Movement.Type.CHECKOUT
        else _batch(movement, "return_batch_line")
    )
    receipt = batch.receipt_code if batch is not None else None
    return {
        "kind": "individual",
        "id": str(movement.id),
        "type": movement.movement_type,
        "type_label": movement.get_movement_type_display(),
        "equipment_type": movement.item.equipment_type.name,
        "identifier": movement.item.display_identifier,
        "item_id": str(movement.item_id),
        "quantity": None,
        "condition": movement.condition_on_return or None,
        "unit": movement.item.unit.name,
        "operator": movement.operator.username,
        "recipient": str(movement.recipient) if movement.recipient_id else None,
        "recipient_id": str(movement.recipient_id) if movement.recipient_id else None,
        "receipt_code": receipt,
        "origin": movement.origin,
        "identity_method": _identity(batch, movement.origin),
        "occurred_at": movement.confirmed_at,
    }


def _entry_row(entry):
    if entry.entry_type == StockLedgerEntry.Type.CHECKOUT:
        batch = entry.loan.batch if entry.loan_id else None
    else:
        batch = _batch(entry, "return_batch_line")
    receipt = batch.receipt_code if batch is not None else None
    return {
        "kind": "quantitative",
        "id": str(entry.id),
        "type": entry.entry_type,
        "type_label": entry.get_entry_type_display(),
        "equipment_type": entry.balance.equipment_type.name,
        "identifier": None,
        "item_id": None,
        "quantity": str(entry.quantity),
        "condition": "fit" if entry.entry_type == StockLedgerEntry.Type.RETURN else None,
        "unit": entry.balance.unit.name,
        "operator": entry.operator.username,
        "recipient": str(entry.recipient) if entry.recipient_id else None,
        "recipient_id": str(entry.recipient_id) if entry.recipient_id else None,
        "receipt_code": receipt,
        "origin": "system",
        "identity_method": _identity(batch),
        "occurred_at": entry.occurred_at,
    }


def counter_movements(
    organization,
    unit_ids,
    *,
    person_id=None,
    operator_id=None,
    equipment_type_id=None,
    movement_type=None,
    kind=None,
):
    """Checkouts, returns and consumption, individual and quantitative (RF-52, RF-53, RF-55).

    Returns two querysets ordered from newest to oldest. Reversed facts stay listed:
    corrections are compensating movements, never edits.
    """
    types = [movement_type] if movement_type else list(COUNTER_MOVEMENT_TYPES)
    movements = _scoped(
        Movement.objects.filter(
            organization=organization,
            movement_type__in=[value for value in types if value in ("checkout", "return")],
        ),
        unit_ids,
        "item__unit_id",
    )
    entries = _scoped(
        StockLedgerEntry.objects.filter(organization=organization, entry_type__in=types),
        unit_ids,
        "balance__unit_id",
    )
    if person_id:
        movements = movements.filter(recipient_id=person_id)
        entries = entries.filter(recipient_id=person_id)
    if operator_id:
        movements = movements.filter(operator_id=operator_id)
        entries = entries.filter(operator_id=operator_id)
    if equipment_type_id:
        movements = movements.filter(item__equipment_type_id=equipment_type_id)
        entries = entries.filter(balance__equipment_type_id=equipment_type_id)
    if kind == "individual":
        entries = entries.none()
    elif kind == "quantitative":
        movements = movements.none()
    movements = movements.select_related(
        "item__equipment_type",
        "item__unit",
        "operator",
        "recipient",
        "service_batch_line__batch",
        "return_batch_line__batch",
    ).order_by("-confirmed_at", "-id")
    entries = entries.select_related(
        "balance__equipment_type",
        "balance__unit",
        "operator",
        "recipient",
        "loan__batch",
        "return_batch_line__batch",
    ).order_by("-occurred_at", "-id")
    return movements, entries


def merge_counter_movements(movements, entries, *, offset, limit):
    """Merge both newest-first streams and return one page of serialized rows."""
    window = offset + limit
    rows = [_movement_row(value) for value in movements[:window]]
    rows += [_entry_row(value) for value in entries[:window]]
    rows.sort(key=lambda row: (row["occurred_at"], row["id"]), reverse=True)
    return [
        {**row, "occurred_at": row["occurred_at"].isoformat()}
        for row in rows[offset : offset + limit]
    ]


def recent_counter_movements(organization, unit_ids, *, limit=10):
    """Latest checkouts and returns, individual and quantitative, with operator and recipient."""
    movements, entries = counter_movements(organization, unit_ids)
    entries = entries.exclude(entry_type=StockLedgerEntry.Type.CONSUME)
    return merge_counter_movements(movements, entries, offset=0, limit=limit)
