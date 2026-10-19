from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AuditEvent, Item, Movement, MovementEvent, Organization, Person
from .permissions import MOVE_ITEM, has_permission


class ConflictError(ValidationError):
    pass


@dataclass(frozen=True)
class CommandContext:
    actor: object
    organization: Organization
    correlation_id: str


def audit(ctx, action, instance, changes=None, result="success"):
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
    if item.availability != Item.Availability.AVAILABLE or item.condition != Item.Condition.FIT:
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
    updated = Item.objects.filter(pk=item.pk, availability=Item.Availability.AVAILABLE).update(
        availability=Item.Availability.IN_CUSTODY, current_holder=recipient, updated_at=now
    )
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


@transaction.atomic
def return_item(ctx, *, item_id: UUID, condition: str, idempotency_key: UUID, confirmed: bool):
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
    if condition not in Item.Condition.values:
        raise ValidationError("Condição de retorno inválida.")
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
    )
    availability = (
        Item.Availability.AVAILABLE
        if condition == Item.Condition.FIT
        else Item.Availability.UNAVAILABLE
    )
    Item.objects.filter(pk=item.pk, availability=Item.Availability.IN_CUSTODY).update(
        availability=availability, condition=condition, current_holder=None, updated_at=now
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
    audit(ctx, "item.return", movement, {"item_id": str(item.id), "condition": condition})
    return movement, True
