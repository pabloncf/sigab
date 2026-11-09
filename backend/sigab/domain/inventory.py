from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from sigab.models import (
    Account,
    InventoryCount,
    InventoryDivergence,
    InventorySession,
    Item,
    Unit,
)
from sigab.permissions import VIEW_ITEM, has_permission
from sigab.services import ConflictError, NotFoundError, audit


@transaction.atomic
def open_inventory_session(ctx, *, unit_id):
    unit = Unit.objects.filter(pk=unit_id, organization=ctx.organization).first()
    if not unit or not has_permission(ctx.actor, VIEW_ITEM, ctx.organization, unit):
        raise PermissionDenied
    if InventorySession.objects.filter(unit=unit, status=InventorySession.Status.OPEN).exists():
        raise ConflictError("A unidade já possui inventário aberto.")
    now = timezone.now()
    session = InventorySession.objects.create(
        organization=ctx.organization,
        unit=unit,
        opened_by=ctx.actor,
        opened_at=now,
        reference_at=now,
    )
    counts = [
        InventoryCount(
            session=session,
            item=item,
            expected_state=item.availability,
        )
        for item in Item.objects.filter(organization=ctx.organization, unit=unit).order_by("id")
    ]
    InventoryCount.objects.bulk_create(counts)
    audit(ctx, "inventory.open", session, {"expected_items": len(counts)})
    return session


@transaction.atomic
def record_inventory_count(ctx, *, session_id, item_id, counted_state):
    if counted_state not in Item.Availability.values and counted_state != "missing":
        raise ValidationError({"counted_state": "Situação contada inválida."})
    session = (
        InventorySession.objects.select_for_update()
        .filter(pk=session_id, organization=ctx.organization)
        .select_related("unit")
        .first()
    )
    if not session:
        raise NotFoundError
    if session.status != InventorySession.Status.OPEN:
        raise ConflictError("O inventário está fechado.")
    if not has_permission(ctx.actor, VIEW_ITEM, ctx.organization, session.unit):
        raise PermissionDenied
    count = (
        InventoryCount.objects.select_for_update().filter(session=session, item_id=item_id).first()
    )
    if not count:
        item = Item.objects.filter(
            pk=item_id, organization=ctx.organization, unit=session.unit
        ).first()
        if not item:
            raise ValidationError("Item não pertence à sessão.")
        count = InventoryCount.objects.create(
            session=session,
            item=item,
            expected_state="unexpected",
        )
    previous = count.counted_state
    count.counted_state = counted_state
    count.counted_at = timezone.now()
    count.counted_by = ctx.actor
    count.save(update_fields=["counted_state", "counted_at", "counted_by", "updated_at"])
    if counted_state != count.expected_state:
        InventoryDivergence.objects.update_or_create(
            count=count,
            defaults={
                "session": session,
                "expected_state": count.expected_state,
                "counted_state": counted_state,
            },
        )
    else:
        InventoryDivergence.objects.filter(
            count=count,
            status__in=[InventoryDivergence.Status.OPEN, InventoryDivergence.Status.INVESTIGATING],
        ).delete()
    audit(
        ctx,
        "inventory.count",
        count,
        {"counted_state": {"from": previous, "to": counted_state}},
    )
    return count


@transaction.atomic
def update_divergence(
    ctx,
    *,
    divergence_id,
    status,
    assignee_id=None,
    reason="",
    resolution="",
):
    divergence = (
        InventoryDivergence.objects.select_for_update()
        .filter(pk=divergence_id, session__organization=ctx.organization)
        .select_related("session__unit")
        .first()
    )
    if not divergence:
        raise NotFoundError
    if divergence.session.status != InventorySession.Status.OPEN:
        raise ConflictError("Divergência de inventário fechado não pode ser alterada.")
    if not has_permission(
        ctx.actor, "inventory.adjust.approve", ctx.organization, divergence.session.unit
    ):
        raise PermissionDenied
    if status not in InventoryDivergence.Status.values:
        raise ValidationError({"status": "Situação inválida."})
    reason = (reason or "").strip()
    resolution = (resolution or "").strip()
    if status in (InventoryDivergence.Status.RESOLVED, InventoryDivergence.Status.DISMISSED):
        if not resolution:
            raise ValidationError({"resolution": "Encerramento exige resolução ou justificativa."})
        divergence.resolved_by = ctx.actor
        divergence.resolved_at = timezone.now()
    else:
        divergence.resolved_by = None
        divergence.resolved_at = None
    assignee = None
    if assignee_id:
        assignee = Account.objects.filter(
            pk=assignee_id, organization=ctx.organization, is_active=True
        ).first()
        if not assignee:
            raise ValidationError({"assignee_id": "Responsável inválido."})
    previous = divergence.status
    divergence.status = status
    divergence.assignee = assignee
    divergence.reason = reason
    divergence.resolution = resolution
    divergence.save()
    audit(
        ctx,
        "inventory.divergence.update",
        divergence,
        {"status": {"from": previous, "to": status}, "assignee_id": str(assignee_id or "")},
        reason=reason or resolution,
    )
    return divergence


@transaction.atomic
def close_inventory_session(ctx, *, session_id):
    session = (
        InventorySession.objects.select_for_update()
        .filter(pk=session_id, organization=ctx.organization)
        .select_related("unit")
        .first()
    )
    if not session:
        raise NotFoundError
    if session.status != InventorySession.Status.OPEN:
        raise ConflictError("O inventário já está fechado.")
    if not has_permission(ctx.actor, "inventory.adjust.approve", ctx.organization, session.unit):
        raise PermissionDenied
    if session.divergences.exclude(
        status__in=[InventoryDivergence.Status.RESOLVED, InventoryDivergence.Status.DISMISSED]
    ).exists():
        raise ConflictError("Resolva ou justifique todas as divergências antes de fechar.")
    if session.counts.filter(counted_at__isnull=True).exists():
        raise ConflictError("Todos os itens esperados devem ser contados.")
    session.status = InventorySession.Status.CLOSED
    session.closed_at = timezone.now()
    session.save(update_fields=["status", "closed_at", "updated_at"])
    audit(ctx, "inventory.close", session)
    return session
