from dataclasses import dataclass
from uuid import UUID

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    Account,
    AuditEvent,
    Item,
    Membership,
    Movement,
    MovementEvent,
    Organization,
    Person,
    Unit,
)
from .permissions import MANAGE_IDENTITY, MOVE_ITEM, SET_ITEM_CONDITION, has_permission


class ConflictError(ValidationError):
    pass


class NotFoundError(Exception):
    """The object does not exist in the caller's organization (or is not visible)."""


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


def _existing(ctx, idempotency_key, movement_type, **expected):
    """Return the movement already recorded under this key, if it is the same request.

    A key reused for another operation type, item or payload is a conflict, never a replay.
    """
    existing = Movement.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if not existing:
        return None
    if existing.movement_type != movement_type or any(
        getattr(existing, field) != value for field, value in expected.items()
    ):
        raise ConflictError("A chave de idempotência já foi usada em outra operação.")
    return existing


@transaction.atomic
def checkout_item(
    ctx, *, item_id: UUID, recipient_id: UUID, idempotency_key: UUID, confirmed: bool
):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    existing = _existing(
        ctx, idempotency_key, Movement.Type.CHECKOUT, item_id=item_id, recipient_id=recipient_id
    )
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(
        ctx, idempotency_key, Movement.Type.CHECKOUT, item_id=item_id, recipient_id=recipient_id
    )
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
    existing = _existing(
        ctx, idempotency_key, Movement.Type.RETURN, item_id=item_id, condition_on_return=condition
    )
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(
        ctx, idempotency_key, Movement.Type.RETURN, item_id=item_id, condition_on_return=condition
    )
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
    existing = _existing(
        ctx,
        idempotency_key,
        Movement.Type.CONDITION_CHANGE,
        item_id=item_id,
        new_condition=condition,
    )
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(
        ctx,
        idempotency_key,
        Movement.Type.CONDITION_CHANGE,
        item_id=item_id,
        new_condition=condition,
    )
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


# Identity: Person, Membership and Account have independent lifecycles (SIGAB-019/020).

PERSON_FIELDS = ("name", "functional_name", "cpf", "phone")


def _require_identity_manager(ctx):
    if not has_permission(ctx.actor, MANAGE_IDENTITY, ctx.organization):
        raise PermissionDenied


def _require_confirmation(confirmed):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")


def normalize_cpf(value):
    return "".join(character for character in value if character.isdigit())


def _person_for_update(ctx, person_id):
    person = (
        Person.objects.select_for_update()
        .filter(id=person_id, organization=ctx.organization)
        .first()
    )
    if not person:
        raise NotFoundError
    return person


@transaction.atomic
def create_person(ctx, *, name, functional_name="", cpf="", phone=""):
    """Register a person without creating any account (SIGAB-019)."""
    _require_identity_manager(ctx)
    person = Person(
        organization=ctx.organization,
        name=name.strip(),
        functional_name=functional_name.strip(),
        cpf=normalize_cpf(cpf),
        phone=phone.strip(),
    )
    person.full_clean()
    person.save()
    # Personal values never enter the audit trail; only which fields were filled.
    audit(
        ctx, "person.create", person, {"fields": [f for f in PERSON_FIELDS if getattr(person, f)]}
    )
    return person


@transaction.atomic
def update_person(ctx, *, person_id, values):
    _require_identity_manager(ctx)
    unknown = set(values) - set(PERSON_FIELDS)
    if unknown:
        raise ValidationError({field: "Campo não editável." for field in sorted(unknown)})
    person = _person_for_update(ctx, person_id)
    changed = []
    for field, value in values.items():
        value = normalize_cpf(value) if field == "cpf" else value.strip()
        if getattr(person, field) != value:
            setattr(person, field, value)
            changed.append(field)
    if not changed:
        return person
    person.full_clean()
    person.save(update_fields=[*changed, "updated_at"])
    audit(ctx, "person.update", person, {"fields": sorted(changed)})
    return person


@transaction.atomic
def set_person_active(ctx, *, person_id, is_active, confirmed, reason=""):
    """Deactivate or reactivate a person; accounts, memberships and history are untouched."""
    _require_identity_manager(ctx)
    _require_confirmation(confirmed)
    person = _person_for_update(ctx, person_id)
    if person.is_active == is_active:
        raise ConflictError("A pessoa já está nessa situação.")
    person.is_active = is_active
    person.save(update_fields=["is_active", "updated_at"])
    audit(
        ctx,
        "person.activate" if is_active else "person.deactivate",
        person,
        {"is_active": {"from": not is_active, "to": is_active}},
        reason=reason.strip(),
    )
    return person


@transaction.atomic
def create_membership(ctx, *, person_id, registration, main_unit_id, rank=""):
    _require_identity_manager(ctx)
    person = _person_for_update(ctx, person_id)
    unit = Unit.objects.filter(
        id=main_unit_id, organization=ctx.organization, is_active=True
    ).first()
    if not unit:
        raise ValidationError({"main_unit_id": "Unidade inválida."})
    membership = Membership(
        organization=ctx.organization,
        person=person,
        registration=registration.strip(),
        main_unit=unit,
        rank=rank.strip(),
    )
    membership.full_clean()
    membership.save()
    audit(
        ctx,
        "membership.create",
        membership,
        {"person_id": str(person.id), "main_unit_id": str(unit.id)},
    )
    return membership


@transaction.atomic
def set_membership_active(ctx, *, membership_id, is_active, confirmed, reason=""):
    _require_identity_manager(ctx)
    _require_confirmation(confirmed)
    membership = (
        Membership.objects.select_for_update()
        .filter(id=membership_id, organization=ctx.organization)
        .first()
    )
    if not membership:
        raise NotFoundError
    if membership.is_active == is_active:
        raise ConflictError("O vínculo já está nessa situação.")
    membership.is_active = is_active
    membership.save(update_fields=["is_active", "updated_at"])
    audit(
        ctx,
        "membership.activate" if is_active else "membership.deactivate",
        membership,
        {"is_active": {"from": not is_active, "to": is_active}},
        reason=reason.strip(),
    )
    return membership


@transaction.atomic
def create_account(ctx, *, person_id, username, password, email=""):
    """Create the access account of an active person (SIGAB-020)."""
    _require_identity_manager(ctx)
    person = _person_for_update(ctx, person_id)
    if not person.is_active:
        raise ConflictError("Pessoa inativa não recebe conta.")
    if person.accounts.filter(revoked_at__isnull=True).exists():
        raise ConflictError("A pessoa já possui conta não revogada.")
    username = username.strip()
    account = Account(
        organization=ctx.organization, person=person, username=username, email=email.strip()
    )
    try:
        account.full_clean(exclude=["password"])
    except ValidationError as exc:
        # Usernames are global: keep the message neutral about who holds the name.
        if (
            "username" in getattr(exc, "error_dict", {})
            and Account.objects.filter(username=username).exists()
        ):
            raise ValidationError({"username": "Identificador de login indisponível."}) from exc
        raise
    try:
        validate_password(password, account)
    except ValidationError as exc:
        raise ValidationError({"password": exc.messages}) from exc
    account.set_password(password)
    account.save()
    audit(ctx, "account.create", account, {"person_id": str(person.id)})
    return account


def _account_for_update(ctx, account_id):
    account = (
        Account.objects.select_for_update()
        .filter(id=account_id, organization=ctx.organization, is_superuser=False)
        .first()
    )
    if not account:
        raise NotFoundError
    if account.pk == ctx.actor.pk:
        raise ConflictError("Não é possível alterar a situação da própria conta.")
    return account


def _audit_account_status(ctx, action, account, previous, reason, extra=None):
    changes = {"status": {"from": previous, "to": account.status}, **(extra or {})}
    audit(ctx, action, account, changes, reason=reason.strip())


@transaction.atomic
def suspend_account(ctx, *, account_id, confirmed, reason=""):
    """Block login immediately; person, memberships, grants and history stay as they are."""
    _require_identity_manager(ctx)
    _require_confirmation(confirmed)
    account = _account_for_update(ctx, account_id)
    previous = account.status
    if previous != "active":
        raise ConflictError("Somente conta ativa pode ser suspensa.")
    account.is_active = False
    account.save(update_fields=["is_active"])
    _audit_account_status(ctx, "account.suspend", account, previous, reason)
    return account


@transaction.atomic
def reactivate_account(ctx, *, account_id, confirmed, reason=""):
    _require_identity_manager(ctx)
    _require_confirmation(confirmed)
    account = _account_for_update(ctx, account_id)
    previous = account.status
    if previous != "suspended":
        raise ConflictError("Somente conta suspensa pode ser reativada.")
    account.is_active = True
    account.save(update_fields=["is_active"])
    _audit_account_status(ctx, "account.reactivate", account, previous, reason)
    return account


@transaction.atomic
def revoke_account(ctx, *, account_id, confirmed, reason=""):
    """End an account permanently: no login, no password, grants revoked; history kept."""
    _require_identity_manager(ctx)
    _require_confirmation(confirmed)
    account = _account_for_update(ctx, account_id)
    previous = account.status
    if previous == "revoked":
        raise ConflictError("A conta já está revogada.")
    now = timezone.now()
    account.is_active = False
    account.revoked_at = now
    account.set_unusable_password()
    account.save(update_fields=["is_active", "revoked_at", "password"])
    revoked_grants = account.grants.filter(is_active=True, revoked_at__isnull=True).update(
        is_active=False, revoked_at=now, updated_at=now
    )
    _audit_account_status(
        ctx, "account.revoke", account, previous, reason, {"revoked_grants": revoked_grants}
    )
    return account
