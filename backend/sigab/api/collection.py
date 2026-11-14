"""Read-only views for the home page (SIGAB-079) and the split collection (SIGAB-081).

Every aggregate is computed on the server inside the reader's ``item.view`` unit scope;
the browser never derives totals on its own.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from sigab.domain.queries import (
    filtered_open_possessions,
    individual_totals_by_type,
    recent_counter_movements,
    stock_positions_with_custody,
)
from sigab.models import StockLedgerEntry
from sigab.permissions import ALL_UNITS, VIEW_ITEM, permitted_unit_ids

from .views import _date_range, _organization, _paginated, _response, _uuid_param, api_view


def _view_scope(request, organization):
    scope = permitted_unit_ids(request.user, VIEW_ITEM, organization)
    if scope is not ALL_UNITS and not scope:
        raise PermissionDenied
    return None if scope is ALL_UNITS else scope


def _quantitative_by_type(positions):
    by_type = {}
    for balance, reserve, in_custody, total in positions:
        entry = by_type.setdefault(
            balance.equipment_type_id,
            {
                "equipment_type_id": str(balance.equipment_type_id),
                "equipment_type": balance.equipment_type.name,
                "reserve": Decimal("0"),
                "in_custody": Decimal("0"),
                "total": Decimal("0"),
            },
        )
        entry["reserve"] += reserve
        entry["in_custody"] += in_custody
        entry["total"] += total
    return [
        {**row, **{key: str(row[key]) for key in ("reserve", "in_custody", "total")}}
        for row in by_type.values()
    ]


@api_view(methods={"GET"})
def overview(request):
    """Home page summary: totals, open possessions and latest counter movements."""
    organization = _organization(request)
    unit_ids = _view_scope(request, organization)
    by_type = individual_totals_by_type(organization, unit_ids)
    totals = {
        key: sum(row[key] for row in by_type) for key in ("available", "in_custody", "unavailable")
    }
    _, loans = filtered_open_possessions(organization)
    if unit_ids is not None:
        loans = loans.filter(balance__unit_id__in=unit_ids)
    return _response(
        {
            "individual": {
                "totals": {**totals, "total": sum(totals.values())},
                "by_type": [
                    {**row, "equipment_type_id": str(row["equipment_type_id"])} for row in by_type
                ],
            },
            "quantitative": _quantitative_by_type(
                stock_positions_with_custody(organization, unit_ids)
            ),
            "pending": {
                "individual_in_custody": totals["in_custody"],
                "quantitative_open": loans.count(),
                "quantitative_overdue": loans.filter(due_at__lt=timezone.now()).count(),
            },
            "recent": recent_counter_movements(organization, unit_ids),
        }
    )


@api_view(methods={"GET"})
def stock_summary(request):
    """Material without registration per type, unit and location (RF-13, RF-14)."""
    organization = _organization(request)
    unit_ids = _view_scope(request, organization)
    rows = stock_positions_with_custody(
        organization, unit_ids, equipment_type_id=_uuid_param(request, "type")
    )
    unit = _uuid_param(request, "unit")
    query = request.GET.get("q", "").strip()[:100].casefold()
    return _response(
        [
            {
                "id": str(balance.id),
                "equipment_type": {
                    "id": str(balance.equipment_type_id),
                    "name": balance.equipment_type.name,
                },
                "unit": {"id": str(balance.unit_id), "name": balance.unit.name},
                "storage_location": {
                    "id": str(balance.storage_location_id),
                    "name": balance.storage_location.name,
                },
                "reserve": str(reserve),
                "in_custody": str(in_custody),
                "total": str(total),
            }
            for balance, reserve, in_custody, total in rows
            if (not unit or balance.unit_id == unit)
            and (not query or query in balance.equipment_type.name.casefold())
        ]
    )


@api_view(methods={"GET"})
def stock_history(request):
    """Read-only ledger history of material without registration (RF-54)."""
    organization = _organization(request)
    unit_ids = _view_scope(request, organization)
    entries = StockLedgerEntry.objects.filter(organization=organization)
    if unit_ids is not None:
        entries = entries.filter(balance__unit_id__in=unit_ids)
    equipment_type = _uuid_param(request, "type")
    if equipment_type:
        entries = entries.filter(balance__equipment_type_id=equipment_type)
    entries = _date_range(request, entries, "occurred_at").select_related(
        "balance__equipment_type",
        "balance__unit",
        "balance__storage_location",
        "operator",
        "recipient",
    )

    def row(entry):
        return {
            "id": str(entry.id),
            "type": entry.entry_type,
            "type_label": entry.get_entry_type_display(),
            "equipment_type": entry.balance.equipment_type.name,
            "quantity": str(entry.quantity),
            "balance_delta": str(entry.balance_delta),
            "unit": entry.balance.unit.name,
            "storage_location": entry.balance.storage_location.name,
            "operator": entry.operator.username,
            "recipient": str(entry.recipient) if entry.recipient_id else None,
            "reason": entry.reason,
            "reverses": str(entry.reverses_id) if entry.reverses_id else None,
            "occurred_at": entry.occurred_at.isoformat(),
        }

    return _paginated(request, entries.order_by("-occurred_at", "-id"), row)
