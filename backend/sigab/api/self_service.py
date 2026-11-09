import csv

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.utils import timezone

from sigab.domain.queries import (
    filtered_open_possessions,
    history_for_person,
    possessions_for_person,
)
from sigab.models import ServiceBatch
from sigab.permissions import ALL_UNITS, AUDIT_EXPORT, VIEW_ITEM, permitted_unit_ids

from .operations import batch_resource
from .views import _organization, _response, api_view


def _item_possession(item):
    return {
        "kind": "individual",
        "id": str(item.id),
        "equipment_type": item.equipment_type.name,
        "identifier": item.display_identifier,
        "unit": item.unit.name,
    }


def _stock_possession(loan):
    return {
        "kind": "quantitative",
        "id": str(loan.id),
        "equipment_type": loan.balance.equipment_type.name,
        "quantity": str(loan.open_quantity),
        "unit": loan.balance.unit.name,
        "due_at": loan.due_at.isoformat() if loan.due_at else None,
        "overdue": bool(loan.due_at and loan.due_at < timezone.now()),
    }


@api_view(methods={"GET"})
def my_possessions(request):
    organization = _organization(request)
    person = request.user.person
    if not person or person.organization_id != organization.id:
        raise PermissionDenied
    items, stock = possessions_for_person(organization, person)
    return _response(
        {
            "person": {"id": str(person.id), "name": str(person)},
            "possessions": [*map(_item_possession, items), *map(_stock_possession, stock)],
        }
    )


@api_view(methods={"GET"})
def my_history(request):
    organization = _organization(request)
    person = request.user.person
    if not person or person.organization_id != organization.id:
        raise PermissionDenied
    movements, stock = history_for_person(organization, person)
    return _response(
        {
            "individual": [
                {
                    "id": str(value.id),
                    "type": value.movement_type,
                    "equipment_type": value.item.equipment_type.name,
                    "identifier": value.item.display_identifier,
                    "occurred_at": value.confirmed_at.isoformat(),
                }
                for value in movements
            ],
            "quantitative": [
                {
                    "id": str(value.id),
                    "type": value.entry_type,
                    "equipment_type": value.balance.equipment_type.name,
                    "quantity": str(value.quantity),
                    "occurred_at": value.occurred_at.isoformat(),
                }
                for value in stock
            ],
            "receipts": [
                {
                    "id": str(batch.id),
                    "code": batch.receipt_code,
                    "confirmed_at": batch.confirmed_at.isoformat(),
                }
                for batch in ServiceBatch.objects.filter(
                    organization=organization, recipient=person
                ).order_by("-confirmed_at", "-id")
            ],
        }
    )


@api_view(methods={"GET"})
def my_receipt(request, pk):
    organization = _organization(request)
    person = request.user.person
    batch = (
        ServiceBatch.objects.filter(pk=pk, organization=organization, recipient=person)
        .select_related("recipient", "pickup_person", "operator")
        .first()
    )
    if not person or not batch:
        raise Http404
    return _response(batch_resource(batch))


@api_view(methods={"GET"})
def possession_list(request):
    organization = _organization(request)
    unit_ids = permitted_unit_ids(request.user, VIEW_ITEM, organization)
    if not unit_ids:
        raise PermissionDenied
    person_id = request.GET.get("person") or None
    unit_id = request.GET.get("unit") or None
    items, stock = filtered_open_possessions(organization, person_id=person_id, unit_id=unit_id)
    if unit_ids is not ALL_UNITS:
        items = items.filter(unit_id__in=unit_ids)
        stock = stock.filter(balance__unit_id__in=unit_ids)
    return _response(
        {
            "individual": [
                {**_item_possession(item), "person": str(item.current_holder)} for item in items
            ],
            "quantitative": [
                {**_stock_possession(loan), "person": str(loan.recipient)} for loan in stock
            ],
        }
    )


def _safe_csv(value):
    text = str(value or "")
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


@api_view(methods={"GET"})
def possession_export(request):
    organization = _organization(request)
    unit_ids = permitted_unit_ids(request.user, AUDIT_EXPORT, organization)
    if not unit_ids:
        raise PermissionDenied
    items, stock = filtered_open_possessions(
        organization,
        person_id=request.GET.get("person") or None,
        unit_id=request.GET.get("unit") or None,
    )
    if unit_ids is not ALL_UNITS:
        items = items.filter(unit_id__in=unit_ids)
        stock = stock.filter(balance__unit_id__in=unit_ids)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="pendencias.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        ["modalidade", "pessoa", "tipo", "identificador", "quantidade", "unidade", "prazo"]
    )
    for item in items.order_by("current_holder__name", "equipment_type__name", "id"):
        writer.writerow(
            [
                "individual",
                _safe_csv(item.current_holder),
                _safe_csv(item.equipment_type.name),
                _safe_csv(item.display_identifier),
                "1",
                _safe_csv(item.unit.name),
                "",
            ]
        )
    for loan in stock.order_by("recipient__name", "balance__equipment_type__name", "id"):
        writer.writerow(
            [
                "quantitativo",
                _safe_csv(loan.recipient),
                _safe_csv(loan.balance.equipment_type.name),
                "",
                str(loan.open_quantity),
                _safe_csv(loan.balance.unit.name),
                loan.due_at.isoformat() if loan.due_at else "",
            ]
        )
    return response
