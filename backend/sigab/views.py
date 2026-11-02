from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CheckoutForm, ConditionForm, ReturnForm
from .models import Item
from .permissions import (
    MOVEMENT_CHECKOUT,
    MOVEMENT_RETURN,
    SET_ITEM_CONDITION,
    VIEW_ITEM,
    has_permission,
)
from .services import CommandContext, checkout_item, return_item, set_item_condition


def _organization(request):
    if not request.user.organization_id:
        raise PermissionDenied
    return request.user.organization


def _item(request, pk, permission=VIEW_ITEM):
    organization = _organization(request)
    item = get_object_or_404(
        Item.objects.select_related("equipment_type", "unit", "storage_location", "current_holder"),
        pk=pk,
        organization=organization,
    )
    if not has_permission(request.user, permission, organization, item.unit):
        raise Http404
    return item


@login_required
def dashboard(request):
    organization = _organization(request)
    candidate_items = (
        Item.objects.filter(organization=organization)
        .select_related("equipment_type", "current_holder")
        .order_by("equipment_type__name", "serial_number")
    )
    items = [
        item
        for item in candidate_items
        if has_permission(request.user, VIEW_ITEM, organization, item.unit)
    ]
    return render(request, "sigab/dashboard.html", {"organization": organization, "items": items})


@login_required
def item_detail(request, pk):
    item = _item(request, pk)
    events = item.events.select_related("movement", "actor").all()
    can_set_condition = has_permission(
        request.user, SET_ITEM_CONDITION, request.user.organization, item.unit
    )
    return render(
        request,
        "sigab/item_detail.html",
        {"item": item, "events": events, "can_set_condition": can_set_condition},
    )


@login_required
def checkout(request, pk):
    item = _item(request, pk, MOVEMENT_CHECKOUT)
    form = CheckoutForm(request.POST or None, organization=request.user.organization)
    if request.method == "POST" and form.is_valid():
        ctx = CommandContext(request.user, request.user.organization, request.correlation_id)
        try:
            _, created = checkout_item(
                ctx,
                item_id=item.id,
                recipient_id=form.cleaned_data["recipient"].id,
                idempotency_key=form.cleaned_data["idempotency_key"],
                confirmed=form.cleaned_data["confirmed"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request, "Saída confirmada." if created else "Requisição já processada."
            )
            return redirect("item-detail", pk=item.id)
    return render(
        request,
        "sigab/movement_form.html",
        {"item": item, "form": form, "title": "Confirmar saída"},
    )


@login_required
def checkin(request, pk):
    item = _item(request, pk, MOVEMENT_RETURN)
    form = ReturnForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ctx = CommandContext(request.user, request.user.organization, request.correlation_id)
        try:
            _, created = return_item(
                ctx,
                item_id=item.id,
                condition=form.cleaned_data["condition"],
                reason=form.cleaned_data["reason"],
                idempotency_key=form.cleaned_data["idempotency_key"],
                confirmed=form.cleaned_data["confirmed"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request, "Devolução confirmada." if created else "Requisição já processada."
            )
            return redirect("item-detail", pk=item.id)
    return render(
        request,
        "sigab/movement_form.html",
        {"item": item, "form": form, "title": "Confirmar devolução"},
    )


@login_required
def change_condition(request, pk):
    item = _item(request, pk, SET_ITEM_CONDITION)
    target = Item.Condition.FIT if item.condition == Item.Condition.UNFIT else Item.Condition.UNFIT
    form = ConditionForm(request.POST or None, target=target)
    if request.method == "POST" and form.is_valid():
        ctx = CommandContext(request.user, request.user.organization, request.correlation_id)
        try:
            _, created = set_item_condition(
                ctx,
                item_id=item.id,
                condition=target,
                reason=form.cleaned_data["reason"],
                idempotency_key=form.cleaned_data["idempotency_key"],
                confirmed=form.cleaned_data["confirmed"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request, "Condição alterada." if created else "Requisição já processada."
            )
            return redirect("item-detail", pk=item.id)
    title = "Liberar item como apto" if target == Item.Condition.FIT else "Declarar item inapto"
    return render(
        request,
        "sigab/movement_form.html",
        {"item": item, "form": form, "title": title},
    )
