from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AuditEvent, Item, Movement, MovementEvent, Organization, Person
from .permissions import MOVE_ITEM, SET_ITEM_CONDITION, has_permission


class ConflictError(ValidationError):
    pass


@dataclass(frozen=True)
class CommandContext:
    actor: object
    organization: Organization
    correlation_id: str


def audit(ctx, action, instance, changes=None, result="success", reason=""):
    return AuditEvent.objects.create(
        organization=ctx.organization,
        actor=ctx.actor,
        action=action,
        object_type=instance._meta.label_lower,
        object_id=str(instance.pk),
        occurred_at=timezone.now(),
        correlation_id=ctx.correlation_id,
        result=result,
        changes=changes or {},
        reason=reason,
    )


@transaction.atomic
def record_incorporation(ctx, item):
    """Record the initial domain fact after a validated item is persisted."""
    now = timezone.now()
    movement = Movement.objects.create(
        organization=ctx.organization,
        movement_type=Movement.Type.INCORPORATION,
        item=item,
        operator=ctx.actor,
        idempotency_key=UUID(int=item.id.int),
        confirmed_at=now,
    )
    MovementEvent.objects.create(
        organization=ctx.organization,
        movement=movement,
        item=item,
        event_type="item.incorporated",
        actor=ctx.actor,
        occurred_at=now,
        metadata={"schema": "item.incorporated.v1"},
    )
    audit(ctx, "item.incorporate", item, {"availability": item.availability})
    return movement


def _existing(ctx, idempotency_key, movement_type):
    existing = Movement.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing and existing.movement_type != movement_type:
        raise ConflictError("A chave de idempotência já foi usada em outra operação.")
    return existing


@transaction.atomic
def checkout_item(
    ctx, *, item_id: UUID, recipient_id: UUID, idempotency_key: UUID, confirmed: bool
):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    existing = _existing(ctx, idempotency_key, Movement.Type.CHECKOUT)
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(ctx, idempotency_key, Movement.Type.CHECKOUT)
    if existing:
        return existing, False
    recipient = Person.objects.filter(
        id=recipient_id, organization=ctx.organization, is_active=True
    ).first()
    if not item or not recipient:
        raise ValidationError("Item ou destinatário inválido.")
    if not has_permission(ctx.actor, MOVE_ITEM, ctx.organization, item.unit):
        raise PermissionDenied
    if not recipient.memberships.filter(organization=ctx.organization, is_active=True).exists():
        raise ValidationError("O destinatário não possui vínculo ativo.")
    if (
        item.administrative_status != Item.AdministrativeStatus.ACTIVE
        or item.availability != Item.Availability.AVAILABLE
        or item.condition != Item.Condition.FIT
    ):
        raise ConflictError("O item não está disponível para saída.")
    now = timezone.now()
    movement = Movement.objects.create(
        organization=ctx.organization,
        movement_type=Movement.Type.CHECKOUT,
        item=item,
        operator=ctx.actor,
        recipient=recipient,
        idempotency_key=idempotency_key,
        confirmed_at=now,
    )
    updated = Item.objects.filter(
        pk=item.pk,
        administrative_status=Item.AdministrativeStatus.ACTIVE,
        availability=Item.Availability.AVAILABLE,
    ).update(availability=Item.Availability.IN_CUSTODY, current_holder=recipient, updated_at=now)
    if updated != 1:
        raise ConflictError("O item foi movimentado por outra operação.")
    MovementEvent.objects.create(
        organization=ctx.organization,
        movement=movement,
        item=item,
        event_type="item.checked_out",
        actor=ctx.actor,
        occurred_at=now,
        metadata={"recipient_id": str(recipient.id), "schema": "item.checked_out.v1"},
    )
    audit(
        ctx, "item.checkout", movement, {"item_id": str(item.id), "recipient_id": str(recipient.id)}
    )
    return movement, True


def _condition_reason(condition, reason):
    if condition not in Item.Condition.values:
        raise ValidationError("Condição inválida.")
    reason = (reason or "").strip()
    if condition == Item.Condition.UNFIT and not reason:
        raise ValidationError("Informe o motivo de inapto.")
    if len(reason) > 200:
        raise ValidationError("O motivo deve ter no máximo 200 caracteres.")
    return reason


@transaction.atomic
def return_item(
    ctx,
    *,
    item_id: UUID,
    condition: str,
    idempotency_key: UUID,
    confirmed: bool,
    reason: str = "",
):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    existing = _existing(ctx, idempotency_key, Movement.Type.RETURN)
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(ctx, idempotency_key, Movement.Type.RETURN)
    if existing:
        return existing, False
    if not item:
        raise ValidationError("Item inválido.")
    if not has_permission(ctx.actor, MOVE_ITEM, ctx.organization, item.unit):
        raise PermissionDenied
    checkout = (
        Movement.objects.filter(
            organization=ctx.organization,
            item=item,
            movement_type=Movement.Type.CHECKOUT,
            responses__isnull=True,
        )
        .order_by("-confirmed_at")
        .first()
    )
    if item.availability != Item.Availability.IN_CUSTODY or not checkout:
        raise ConflictError("O item não possui saída aberta.")
    reason = _condition_reason(condition, reason)
    item_reason = reason if condition == Item.Condition.UNFIT else ""
    now = timezone.now()
    movement = Movement.objects.create(
        organization=ctx.organization,
        movement_type=Movement.Type.RETURN,
        item=item,
        operator=ctx.actor,
        recipient=item.current_holder,
        related_movement=checkout,
        idempotency_key=idempotency_key,
        confirmed_at=now,
        condition_on_return=condition,
        condition_reason=reason,
    )
    availability = (
        Item.Availability.AVAILABLE
        if condition == Item.Condition.FIT
        else Item.Availability.UNAVAILABLE
    )
    Item.objects.filter(pk=item.pk, availability=Item.Availability.IN_CUSTODY).update(
        availability=availability,
        condition=condition,
        condition_reason=item_reason,
        current_holder=None,
        updated_at=now,
    )
    MovementEvent.objects.create(
        organization=ctx.organization,
        movement=movement,
        item=item,
        event_type="item.returned",
        actor=ctx.actor,
        occurred_at=now,
        metadata={"condition": condition, "schema": "item.returned.v1"},
    )
    audit(
        ctx,
        "item.return",
        movement,
        {"item_id": str(item.id), "condition": condition},
        reason=reason,
    )
    return movement, True


@transaction.atomic
def set_item_condition(
    ctx, *, item_id: UUID, condition: str, reason: str, idempotency_key: UUID, confirmed: bool
):
    """Declare an item in the reserve unfit (T05) or release it as fit (T06)."""
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    existing = _existing(ctx, idempotency_key, Movement.Type.CONDITION_CHANGE)
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(ctx, idempotency_key, Movement.Type.CONDITION_CHANGE)
    if existing:
        return existing, False
    if not item:
        raise ValidationError("Item inválido.")
    if not has_permission(ctx.actor, SET_ITEM_CONDITION, ctx.organization, item.unit):
        raise PermissionDenied
    reason = _condition_reason(condition, reason)
    if not reason:
        raise ValidationError("Informe a referência da conferência que libera o item.")
    if item.administrative_status != Item.AdministrativeStatus.ACTIVE:
        raise ConflictError("O item não está ativo.")
    if item.availability == Item.Availability.IN_CUSTODY:
        raise ConflictError("A condição de item em posse é registrada na devolução.")
    if item.condition == condition:
        raise ConflictError("O item já está nessa condição.")
    now = timezone.now()
    previous = item.condition
    movement = Movement.objects.create(
        organization=ctx.organization,
        movement_type=Movement.Type.CONDITION_CHANGE,
        item=item,
        operator=ctx.actor,
        idempotency_key=idempotency_key,
        confirmed_at=now,
        new_condition=condition,
        condition_reason=reason,
    )
    fit = condition == Item.Condition.FIT
    updated = Item.objects.filter(
        pk=item.pk,
        administrative_status=Item.AdministrativeStatus.ACTIVE,
        condition=previous,
        availability__in=[Item.Availability.AVAILABLE, Item.Availability.UNAVAILABLE],
    ).update(
        condition=condition,
        condition_reason="" if fit else reason,
        availability=Item.Availability.AVAILABLE if fit else Item.Availability.UNAVAILABLE,
        updated_at=now,
    )
    if updated != 1:
        raise ConflictError("O item foi movimentado por outra operação.")
    MovementEvent.objects.create(
        organization=ctx.organization,
        movement=movement,
        item=item,
        event_type="item.condition_changed",
        actor=ctx.actor,
        occurred_at=now,
        metadata={
            "previous_condition": previous,
            "condition": condition,
            "schema": "item.condition_changed.v1",
        },
    )
    audit(
        ctx,
        "item.condition_change",
        movement,
        {"item_id": str(item.id), "condition": {"from": previous, "to": condition}},
        reason=reason,
    )
    return movement, True
