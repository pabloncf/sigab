from django.db.models import Q

from sigab.models import Item, Movement, StockLedgerEntry, StockLoan


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
