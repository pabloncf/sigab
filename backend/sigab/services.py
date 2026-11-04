from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from .models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    Item,
    Membership,
    Movement,
    MovementEvent,
    Organization,
    Person,
    Role,
    StorageLocation,
    Unit,
)
from .permissions import (
    AUDIT_EXPORT,
    CATALOG_MANAGE,
    ITEM_CREATE,
    MANAGE_IDENTITY,
    MOVEMENT_CHECKOUT,
    MOVEMENT_RETURN,
    MOVEMENT_REVERSE,
    MUTATING_PERMISSIONS,
    SET_ITEM_CONDITION,
    has_permission,
)


class ConflictError(ValidationError):
    pass


class DivergenceError(ConflictError):
    """A paper record that contradicts the system; it is investigated, never forced (ADR 0004)."""


class NotFoundError(Exception):
    """The object does not exist in the caller's organization (or is not visible)."""


@dataclass(frozen=True)
class CommandContext:
    actor: object
    organization: Organization
    correlation_id: str


@dataclass(frozen=True)
class Contingency:
    """Line of the reserve's contingency book being reconciled (SIGAB-046, ADR 0004)."""

    occurred_at: datetime
    paper_reference: str


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
    audit(
        ctx,
        "item.incorporate",
        item,
        {"availability": item.availability, "condition": item.condition},
    )
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


def _origin_fields(contingency):
    """Movement fields that tell a system registration from a reconciled paper record."""
    if contingency is None:
        return {"origin": Movement.Origin.SYSTEM}
    reference = (contingency.paper_reference or "").strip()
    if not reference:
        raise ValidationError({"paper_reference": "Informe a folha e a linha do livro."})
    if len(reference) > 64:
        raise ValidationError({"paper_reference": "Use no máximo 64 caracteres."})
    occurred_at = contingency.occurred_at
    if not isinstance(occurred_at, datetime) or timezone.is_naive(occurred_at):
        raise ValidationError({"occurred_at": "Informe data e hora com fuso."})
    return {
        "origin": Movement.Origin.CONTINGENCY,
        "declared_occurred_at": occurred_at,
        "paper_reference": reference,
    }


def _is_contingency(origin):
    return origin["origin"] == Movement.Origin.CONTINGENCY


def _state_conflict(origin, message):
    if _is_contingency(origin):
        return DivergenceError(f"Divergência com o estado atual: {message}")
    return ConflictError(message)


def _check_contingency_fact(ctx, item, origin, now):
    """The paper fact must fit after everything already recorded for the item (ADR 0004)."""
    if not _is_contingency(origin):
        return
    occurred_at = origin["declared_occurred_at"]
    if occurred_at > now:
        raise ValidationError({"occurred_at": "O instante do fato não pode estar no futuro."})
    # Reversed facts and the reversals themselves correct registrations, not the item's past,
    # so a wrongly reconciled line can be reversed and reconciled again.
    latest = (
        MovementEvent.objects.filter(item=item, movement__reversal__isnull=True)
        .exclude(movement__movement_type=Movement.Type.REVERSAL)
        .order_by("-occurred_at")
        .first()
    )
    if latest and occurred_at <= latest.occurred_at:
        raise DivergenceError(
            "Divergência: o item tem registro igual ou posterior ao instante informado. "
            "Consulte o histórico antes de lançar."
        )
    # One book per reserve: a sheet/line is reconciled once. Guards against human error;
    # retries of the same request are replays through the idempotency key.
    if Movement.objects.filter(
        organization=ctx.organization,
        origin=Movement.Origin.CONTINGENCY,
        paper_reference=origin["paper_reference"],
        item__storage_location_id=item.storage_location_id,
        reversal__isnull=True,
    ).exists():
        raise DivergenceError("Divergência: esta folha/linha já foi lançada nesta reserva.")


def _movement_audit(ctx, action, movement, origin, changes, reason=""):
    if _is_contingency(origin):
        action = f"{action}.contingency"
        changes = {
            **changes,
            "occurred_at": origin["declared_occurred_at"].isoformat(),
            "paper_reference": origin["paper_reference"],
        }
    audit(ctx, action, movement, changes, reason=reason)


@transaction.atomic
def checkout_item(
    ctx,
    *,
    item_id: UUID,
    recipient_id: UUID,
    idempotency_key: UUID,
    confirmed: bool,
    contingency: Contingency | None = None,
):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    origin = _origin_fields(contingency)
    expected = {"item_id": item_id, "recipient_id": recipient_id, **origin}
    existing = _existing(ctx, idempotency_key, Movement.Type.CHECKOUT, **expected)
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(ctx, idempotency_key, Movement.Type.CHECKOUT, **expected)
    if existing:
        return existing, False
    recipient = Person.objects.filter(
        id=recipient_id, organization=ctx.organization, is_active=True
    ).first()
    if not item or not recipient:
        raise ValidationError("Item ou destinatário inválido.")
    if not has_permission(ctx.actor, MOVEMENT_CHECKOUT, ctx.organization, item.unit):
        raise PermissionDenied
    if not recipient.memberships.filter(organization=ctx.organization, is_active=True).exists():
        raise ValidationError("O destinatário não possui vínculo ativo.")
    if (
        item.administrative_status != Item.AdministrativeStatus.ACTIVE
        or item.availability != Item.Availability.AVAILABLE
        or item.condition != Item.Condition.FIT
    ):
        raise _state_conflict(origin, "O item não está disponível para saída.")
    now = timezone.now()
    _check_contingency_fact(ctx, item, origin, now)
    movement = Movement.objects.create(
        organization=ctx.organization,
        movement_type=Movement.Type.CHECKOUT,
        item=item,
        operator=ctx.actor,
        recipient=recipient,
        idempotency_key=idempotency_key,
        confirmed_at=now,
        **origin,
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
        occurred_at=origin.get("declared_occurred_at", now),
        metadata={"recipient_id": str(recipient.id), "schema": "item.checked_out.v1"},
    )
    _movement_audit(
        ctx,
        "item.checkout",
        movement,
        origin,
        {"item_id": str(item.id), "recipient_id": str(recipient.id)},
    )
    return movement, True


def _open_checkout(ctx, item):
    """The checkout in force: neither reversed nor closed by a return still in force."""
    returned = Movement.objects.filter(
        related_movement=OuterRef("pk"),
        movement_type=Movement.Type.RETURN,
        reversal__isnull=True,
    )
    return (
        Movement.objects.filter(
            organization=ctx.organization,
            item=item,
            movement_type=Movement.Type.CHECKOUT,
            reversal__isnull=True,
        )
        .exclude(Exists(returned))
        .order_by("-confirmed_at")
        .first()
    )


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
    contingency: Contingency | None = None,
):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    origin = _origin_fields(contingency)
    expected = {"item_id": item_id, "condition_on_return": condition, **origin}
    existing = _existing(ctx, idempotency_key, Movement.Type.RETURN, **expected)
    if existing:
        return existing, False
    item = (
        Item.objects.select_for_update().filter(id=item_id, organization=ctx.organization).first()
    )
    existing = _existing(ctx, idempotency_key, Movement.Type.RETURN, **expected)
    if existing:
        return existing, False
    if not item:
        raise ValidationError("Item inválido.")
    if not has_permission(ctx.actor, MOVEMENT_RETURN, ctx.organization, item.unit):
        raise PermissionDenied
    checkout = _open_checkout(ctx, item)
    if item.availability != Item.Availability.IN_CUSTODY or not checkout:
        raise _state_conflict(origin, "O item não possui saída aberta.")
    reason = _condition_reason(condition, reason)
    item_reason = reason if condition == Item.Condition.UNFIT else ""
    now = timezone.now()
    _check_contingency_fact(ctx, item, origin, now)
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
        **origin,
    )
    availability = (
        Item.Availability.AVAILABLE
        if condition == Item.Condition.FIT
        else Item.Availability.UNAVAILABLE
    )
    updated = Item.objects.filter(pk=item.pk, availability=Item.Availability.IN_CUSTODY).update(
        availability=availability,
        condition=condition,
        condition_reason=item_reason,
        current_holder=None,
        updated_at=now,
    )
    if updated != 1:
        raise ConflictError("O item foi movimentado por outra operação.")
    MovementEvent.objects.create(
        organization=ctx.organization,
        movement=movement,
        item=item,
        event_type="item.returned",
        actor=ctx.actor,
        occurred_at=origin.get("declared_occurred_at", now),
        metadata={"condition": condition, "schema": "item.returned.v1"},
    )
    _movement_audit(
        ctx,
        "item.return",
        movement,
        origin,
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
    account.session_version += 1
    account.save(update_fields=["is_active", "session_version"])
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
    account.session_version += 1
    account.save(update_fields=["is_active", "revoked_at", "password", "session_version"])
    revoked_grants = account.grants.filter(is_active=True, revoked_at__isnull=True).update(
        is_active=False, revoked_at=now, updated_at=now
    )
    _audit_account_status(
        ctx, "account.revoke", account, previous, reason, {"revoked_grants": revoked_grants}
    )
    return account


@transaction.atomic
def end_account_sessions(ctx, *, account_id, confirmed, reason=""):
    """Invalidate every open session of the account without changing its status."""
    _require_identity_manager(ctx)
    _require_confirmation(confirmed)
    account = _account_for_update(ctx, account_id)
    account.session_version += 1
    account.save(update_fields=["session_version"])
    audit(ctx, "account.end_sessions", account, {}, reason=reason.strip())
    return account


# Grants (SIGAB-022, decision 0002): explicit, scoped, time-bound and conflict-checked.


def _scopes_overlap(scope_type, unit_id, other):
    return (
        scope_type == Grant.Scope.ORGANIZATION
        or other.scope_type == Grant.Scope.ORGANIZATION
        or other.unit_id == unit_id
    )


def _check_grant_conflicts(account, role, scope_type, unit_id):
    """Independent auditor: audit.export never coexists with mutation in the same scope."""
    permissions = set(role.permissions)
    now = timezone.now()
    current = (
        account.grants.filter(is_active=True, revoked_at__isnull=True)
        .exclude(valid_until__lte=now)
        .select_related("role")
    )
    for grant in current:
        if not _scopes_overlap(scope_type, unit_id, grant):
            continue
        other = set(grant.role.permissions)
        if (AUDIT_EXPORT in permissions and other & MUTATING_PERMISSIONS) or (
            AUDIT_EXPORT in other and permissions & MUTATING_PERMISSIONS
        ):
            raise ConflictError(
                "Conflito de funções: auditor independente não acumula papel que altera dados "
                "no mesmo escopo."
            )


@transaction.atomic
def create_grant(
    ctx,
    *,
    account_id,
    role_id,
    scope_type,
    unit_id=None,
    valid_from=None,
    valid_until=None,
    reason,
):
    _require_identity_manager(ctx)
    reason = reason.strip()
    if not reason:
        raise ValidationError({"reason": "Informe o motivo da alteração de perfil."})
    account = (
        Account.objects.select_for_update()
        .filter(id=account_id, organization=ctx.organization, is_superuser=False)
        .first()
    )
    if not account:
        raise NotFoundError
    if account.pk == ctx.actor.pk:
        raise ConflictError("Uma conta não pode conceder papel a si mesma.")
    if account.status == "revoked":
        raise ConflictError("Conta revogada não recebe concessões.")
    role = Role.objects.filter(id=role_id, organization=ctx.organization).first()
    if not role:
        raise ValidationError({"role_id": "Papel inválido."})
    unit = None
    if unit_id:
        unit = Unit.objects.filter(
            id=unit_id, organization=ctx.organization, is_active=True
        ).first()
        if not unit:
            raise ValidationError({"unit_id": "Unidade inválida."})
    grant = Grant(
        organization=ctx.organization,
        account=account,
        role=role,
        scope_type=scope_type,
        unit=unit,
        valid_from=valid_from,
        valid_until=valid_until,
        granted_by=ctx.actor,
    )
    grant.full_clean()
    _check_grant_conflicts(account, role, scope_type, unit.id if unit else None)
    grant.save()
    audit(
        ctx,
        "grant.create",
        grant,
        {
            "account_id": str(account.id),
            "role_id": str(role.id),
            "scope_type": scope_type,
            "unit_id": str(unit.id) if unit else None,
        },
        reason=reason,
    )
    return grant


@transaction.atomic
def revoke_grant(ctx, *, grant_id, confirmed, reason):
    _require_identity_manager(ctx)
    _require_confirmation(confirmed)
    reason = reason.strip()
    if not reason:
        raise ValidationError({"reason": "Informe o motivo da alteração de perfil."})
    grant = (
        Grant.objects.select_for_update().filter(id=grant_id, organization=ctx.organization).first()
    )
    if not grant:
        raise NotFoundError
    if grant.account_id == ctx.actor.pk:
        raise ConflictError("Uma conta não pode revogar a própria concessão.")
    if grant.revoked_at or not grant.is_active:
        raise ConflictError("A concessão já está revogada.")
    now = timezone.now()
    grant.is_active = False
    grant.revoked_at = now
    grant.save(update_fields=["is_active", "revoked_at", "updated_at"])
    audit(ctx, "grant.revoke", grant, {"account_id": str(grant.account_id)}, reason=reason)
    return grant


# Organization structure and catalog (SIGAB-024/026): catalog.manage at organization scope.


def _require_catalog_manager(ctx):
    if not has_permission(ctx.actor, CATALOG_MANAGE, ctx.organization):
        raise PermissionDenied


def _set_active(ctx, instance, is_active, confirmed, reason, label):
    _require_confirmation(confirmed)
    if instance.is_active == is_active:
        raise ConflictError(f"{label} já está nessa situação.")
    instance.is_active = is_active
    instance.save(update_fields=["is_active", "updated_at"])
    action = "activate" if is_active else "deactivate"
    audit(
        ctx,
        f"{instance._meta.model_name}.{action}",
        instance,
        {"is_active": {"from": not is_active, "to": is_active}},
        reason=reason.strip(),
    )
    return instance


def _locked(model, ctx, pk):
    instance = (
        model.objects.select_for_update().filter(id=pk, organization=ctx.organization).first()
    )
    if not instance:
        raise NotFoundError
    return instance


@transaction.atomic
def create_unit(ctx, *, code, name):
    _require_catalog_manager(ctx)
    unit = Unit(organization=ctx.organization, code=code.strip(), name=name.strip())
    unit.full_clean()
    unit.save()
    audit(ctx, "unit.create", unit, {"code": unit.code})
    return unit


@transaction.atomic
def update_unit(ctx, *, unit_id, name):
    _require_catalog_manager(ctx)
    unit = _locked(Unit, ctx, unit_id)
    previous = unit.name
    unit.name = name.strip()
    unit.full_clean()
    if unit.name != previous:
        unit.save(update_fields=["name", "updated_at"])
        audit(ctx, "unit.update", unit, {"name": {"from": previous, "to": unit.name}})
    return unit


@transaction.atomic
def set_unit_active(ctx, *, unit_id, is_active, confirmed, reason=""):
    """Deactivation blocks new links to the unit; items, people and history remain."""
    _require_catalog_manager(ctx)
    return _set_active(ctx, _locked(Unit, ctx, unit_id), is_active, confirmed, reason, "A unidade")


@transaction.atomic
def create_storage_location(ctx, *, unit_id, code, name):
    _require_catalog_manager(ctx)
    unit = Unit.objects.filter(id=unit_id, organization=ctx.organization, is_active=True).first()
    if not unit:
        raise ValidationError({"unit_id": "Unidade inválida."})
    location = StorageLocation(
        organization=ctx.organization, unit=unit, code=code.strip(), name=name.strip()
    )
    location.full_clean()
    location.save()
    audit(ctx, "storagelocation.create", location, {"unit_id": str(unit.id), "code": location.code})
    return location


@transaction.atomic
def set_storage_location_active(ctx, *, location_id, is_active, confirmed, reason=""):
    _require_catalog_manager(ctx)
    location = _locked(StorageLocation, ctx, location_id)
    return _set_active(ctx, location, is_active, confirmed, reason, "O local de guarda")


@transaction.atomic
def create_equipment_type(ctx, *, name, classification, description=""):
    _require_catalog_manager(ctx)
    equipment_type = EquipmentType(
        organization=ctx.organization,
        name=name.strip(),
        classification=classification,
        description=description.strip(),
    )
    equipment_type.full_clean()
    equipment_type.save()
    audit(ctx, "equipmenttype.create", equipment_type, {"classification": classification})
    return equipment_type


@transaction.atomic
def update_equipment_type(ctx, *, type_id, name, description):
    """Name and description only: the classification is immutable (RN-03, RF-16)."""
    _require_catalog_manager(ctx)
    equipment_type = _locked(EquipmentType, ctx, type_id)
    changed = {}
    for field, value in (("name", name.strip()), ("description", description.strip())):
        if getattr(equipment_type, field) != value:
            changed[field] = {"from": getattr(equipment_type, field), "to": value}
            setattr(equipment_type, field, value)
    if changed:
        equipment_type.full_clean()
        equipment_type.save(update_fields=[*changed, "updated_at"])
        audit(ctx, "equipmenttype.update", equipment_type, changed)
    return equipment_type


@transaction.atomic
def set_equipment_type_active(ctx, *, type_id, is_active, confirmed, reason=""):
    _require_catalog_manager(ctx)
    equipment_type = _locked(EquipmentType, ctx, type_id)
    return _set_active(ctx, equipment_type, is_active, confirmed, reason, "O tipo")


# Individual item (SIGAB-027): T01 of decision 0004.


@transaction.atomic
def incorporate_item(
    ctx,
    *,
    equipment_type_id,
    unit_id,
    storage_location_id,
    confirmed,
    serial_number="",
    asset_number="",
    official_identifier="",
    condition=Item.Condition.FIT,
    condition_reason="",
):
    """Register an individual item in the reserve with its declared condition."""
    _require_confirmation(confirmed)
    unit = Unit.objects.filter(id=unit_id, organization=ctx.organization, is_active=True).first()
    if not unit:
        raise ValidationError({"unit_id": "Unidade inválida."})
    if not has_permission(ctx.actor, ITEM_CREATE, ctx.organization, unit):
        raise PermissionDenied
    equipment_type = EquipmentType.objects.filter(
        id=equipment_type_id, organization=ctx.organization, is_active=True
    ).first()
    if not equipment_type:
        raise ValidationError({"equipment_type_id": "Tipo inválido."})
    location = StorageLocation.objects.filter(
        id=storage_location_id, organization=ctx.organization, unit=unit, is_active=True
    ).first()
    if not location:
        raise ValidationError({"storage_location_id": "Local de guarda inválido para a unidade."})
    serial_number, asset_number = serial_number.strip(), asset_number.strip()
    if not serial_number and not asset_number:
        # RF-12/RN-02: the item is identified by a number unique in the organization.
        raise ValidationError("Informe o número de série ou o patrimônio.")
    reason = _condition_reason(condition, condition_reason)
    item = Item(
        organization=ctx.organization,
        equipment_type=equipment_type,
        unit=unit,
        storage_location=location,
        serial_number=serial_number,
        asset_number=asset_number,
        official_identifier=official_identifier.strip(),
        condition=condition,
        condition_reason=reason if condition == Item.Condition.UNFIT else "",
        availability=(
            Item.Availability.AVAILABLE
            if condition == Item.Condition.FIT
            else Item.Availability.UNAVAILABLE
        ),
    )
    item.full_clean()
    item.save()
    record_incorporation(ctx, item)
    return item


# Reversal (SIGAB-034, ADR 0006 section 4): corrects a registration error by compensation.

REVERSIBLE_TYPES = (
    Movement.Type.CHECKOUT,
    Movement.Type.RETURN,
    Movement.Type.CONDITION_CHANGE,
)


def latest_movement_in_force(item):
    """Most recent movement of the item that is neither a reversal nor reversed."""
    return (
        Movement.objects.filter(item=item, reversal__isnull=True)
        .exclude(movement_type=Movement.Type.REVERSAL)
        .order_by("-confirmed_at", "-created_at")
        .first()
    )


def _reason_before(item, movement):
    """Unfit reason in force before `movement`, from the last earlier fact that stated one."""
    earlier = (
        Movement.objects.filter(
            item=item, reversal__isnull=True, confirmed_at__lt=movement.confirmed_at
        )
        .exclude(movement_type=Movement.Type.REVERSAL)
        .exclude(condition_reason="")
        .order_by("-confirmed_at")
        .first()
    )
    return earlier.condition_reason if earlier else "Condição restaurada por estorno."


def _restored_state(item, original):
    """Projection the item had before `original`, after checking it still shows its effect."""
    if original.movement_type == Movement.Type.CHECKOUT:
        if item.availability != Item.Availability.IN_CUSTODY or (
            item.current_holder_id != original.recipient_id
        ):
            raise ConflictError("O item não está mais no estado produzido pela saída.")
        return {"availability": Item.Availability.AVAILABLE, "current_holder": None}
    if original.movement_type == Movement.Type.RETURN:
        if (
            item.availability == Item.Availability.IN_CUSTODY
            or item.condition != original.condition_on_return
        ):
            raise ConflictError("O item não está mais no estado produzido pela devolução.")
        # The checkout required a fit item, so the item goes back to custody fit.
        return {
            "availability": Item.Availability.IN_CUSTODY,
            "current_holder": original.related_movement.recipient,
            "condition": Item.Condition.FIT,
            "condition_reason": "",
        }
    if (
        item.availability == Item.Availability.IN_CUSTODY
        or item.condition != original.new_condition
    ):
        raise ConflictError("O item não está mais no estado produzido pela alteração de condição.")
    previous = original.events.get().metadata["previous_condition"]
    fit = previous == Item.Condition.FIT
    return {
        "condition": previous,
        "condition_reason": "" if fit else _reason_before(item, original),
        "availability": Item.Availability.AVAILABLE if fit else Item.Availability.UNAVAILABLE,
    }


@transaction.atomic
def reverse_movement(ctx, *, movement_id, idempotency_key, confirmed, reason):
    _require_confirmation(confirmed)
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Informe o motivo do estorno."})
    existing = _existing(ctx, idempotency_key, Movement.Type.REVERSAL, reverses_id=movement_id)
    if existing:
        return existing, False
    original = (
        Movement.objects.filter(id=movement_id, organization=ctx.organization)
        .select_related("item__unit", "related_movement__recipient")
        .first()
    )
    if not original:
        raise NotFoundError
    item = Item.objects.select_for_update().get(pk=original.item_id)
    if not has_permission(ctx.actor, MOVEMENT_REVERSE, ctx.organization, item.unit):
        raise PermissionDenied
    if original.movement_type not in REVERSIBLE_TYPES:
        raise ConflictError(
            "Somente saída, devolução e alteração de condição podem ser estornadas."
        )
    if Movement.objects.filter(reverses=original).exists():
        raise ConflictError("A movimentação já foi estornada.")
    if latest_movement_in_force(item) != original:
        raise ConflictError("Estorne primeiro a movimentação mais recente do item.")
    before = {
        "availability": item.availability,
        "condition": item.condition,
        "holder_id": str(item.current_holder_id) if item.current_holder_id else None,
    }
    restored = _restored_state(item, original)
    now = timezone.now()
    reversal = Movement.objects.create(
        organization=ctx.organization,
        movement_type=Movement.Type.REVERSAL,
        item=item,
        operator=ctx.actor,
        reverses=original,
        reason=reason,
        idempotency_key=idempotency_key,
        confirmed_at=now,
    )
    updated = Item.objects.filter(
        pk=item.pk, availability=item.availability, condition=item.condition
    ).update(**restored, updated_at=now)
    if updated != 1:
        raise ConflictError("O item foi movimentado por outra operação.")
    item.refresh_from_db()
    MovementEvent.objects.create(
        organization=ctx.organization,
        movement=reversal,
        item=item,
        event_type="item.movement_reversed",
        actor=ctx.actor,
        occurred_at=now,
        compensates=original.events.get(),
        metadata={
            "reversed_type": original.movement_type,
            "schema": "item.movement_reversed.v1",
        },
    )
    after = {
        "availability": item.availability,
        "condition": item.condition,
        "holder_id": str(item.current_holder_id) if item.current_holder_id else None,
    }
    audit(
        ctx,
        "movement.reverse",
        reversal,
        {
            "reversed_movement_id": str(original.id),
            "reversed_type": original.movement_type,
            **{
                key: {"from": before[key], "to": after[key]}
                for key in before
                if before[key] != after[key]
            },
        },
        reason=reason,
    )
    return reversal, True
