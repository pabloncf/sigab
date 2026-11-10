from django.http import Http404

from sigab.domain.inventory import (
    close_inventory_session,
    open_inventory_session,
    record_inventory_count,
    update_divergence,
)
from sigab.models import InventorySession
from sigab.permissions import VIEW_ITEM, has_permission

from .views import (
    _context,
    _parse_json,
    _required_string,
    _required_uuid,
    _response,
    _string,
    api_view,
)


def _session_resource(session):
    divergences = session.divergences.select_related("count__item", "assignee").order_by("id")
    return {
        "id": str(session.id),
        "unit": {"id": str(session.unit_id), "name": session.unit.name},
        "status": session.status,
        "reference_at": session.reference_at.isoformat(),
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        "counts": session.counts.count(),
        "divergences": [
            {
                "id": str(value.id),
                "item_id": str(value.count.item_id),
                "identifier": value.count.item.display_identifier,
                "expected": value.expected_state,
                "counted": value.counted_state,
                "status": value.status,
                "assignee": value.assignee.username if value.assignee else None,
                "reason": value.reason,
                "resolution": value.resolution,
            }
            for value in divergences
        ],
    }


@api_view(methods={"POST"})
def inventory_open(request):
    payload = _parse_json(request)
    session = open_inventory_session(_context(request), unit_id=_required_uuid(payload, "unit_id"))
    session = InventorySession.objects.select_related("unit").get(pk=session.pk)
    return _response(_session_resource(session), status=201)


@api_view(methods={"GET"})
def inventory_detail(request, pk):
    session = (
        InventorySession.objects.filter(pk=pk, organization=request.user.organization)
        .select_related("unit")
        .first()
    )
    if not session or not (
        has_permission(request.user, VIEW_ITEM, request.user.organization, session.unit)
        or has_permission(
            request.user,
            "inventory.adjust.approve",
            request.user.organization,
            session.unit,
        )
    ):
        raise Http404
    return _response(_session_resource(session))


@api_view(methods={"POST"})
def inventory_count(request, pk):
    payload = _parse_json(request)
    count = record_inventory_count(
        _context(request),
        session_id=pk,
        item_id=_required_uuid(payload, "item_id"),
        counted_state=_required_string(payload, "counted_state", max_length=24),
    )
    return _response(
        {
            "id": str(count.id),
            "expected": count.expected_state,
            "counted": count.counted_state,
        }
    )


@api_view(methods={"POST"})
def divergence_update(request, pk):
    payload = _parse_json(request)
    divergence = update_divergence(
        _context(request),
        divergence_id=pk,
        status=_required_string(payload, "status", max_length=16),
        assignee_id=_required_uuid(payload, "assignee_id") if payload.get("assignee_id") else None,
        reason=_string(payload, "reason", max_length=500),
        resolution=_string(payload, "resolution", max_length=500),
    )
    return _response({"id": str(divergence.id), "status": divergence.status})


@api_view(methods={"POST"})
def inventory_close(request, pk):
    session = close_inventory_session(_context(request), session_id=pk)
    return _response({"id": str(session.id), "status": session.status})
