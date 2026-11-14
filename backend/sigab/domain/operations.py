import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid5

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from sigab.domain.biometrics import pending_return_lines, resolve_identity
from sigab.models import (
    EquipmentType,
    IdentityOperation,
    Item,
    Person,
    ReturnBatch,
    ReturnBatchItem,
    ReturnBatchStock,
    ServiceBatch,
    ServiceBatchItem,
    StockBalance,
    StockLedgerEntry,
    StockLoan,
    StorageLocation,
    Unit,
)
from sigab.permissions import MOVEMENT_CHECKOUT, MOVEMENT_RETURN, has_permission
from sigab.services import (
    CommandContext,
    ConflictError,
    NotFoundError,
    audit,
    checkout_item,
    ensure_not_own_operation,
    return_item,
)


@dataclass(frozen=True)
class StockRequest:
    equipment_type_id: UUID
    unit_id: UUID
    storage_location_id: UUID
    quantity: Decimal


def positive_quantity(value, field="quantity"):
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({field: "Informe uma quantidade válida."}) from exc
    if (
        not quantity.is_finite()
        or quantity <= 0
        or quantity > Decimal("99999999999.999")
        or quantity.as_tuple().exponent < -3
    ):
        raise ValidationError({field: "Use quantidade positiva com até três casas decimais."})
    return quantity


def _request_hash(*, recipient_id, pickup_person_id, custody_mode, due_at, item_ids, stock):
    payload = {
        "recipient_id": str(recipient_id),
        "pickup_person_id": str(pickup_person_id) if pickup_person_id else None,
        "custody_mode": custody_mode,
        "due_at": due_at.isoformat() if due_at else None,
        "item_ids": sorted(str(value) for value in item_ids),
        "stock": sorted(
            (
                str(line.equipment_type_id),
                str(line.unit_id),
                str(line.storage_location_id),
                str(line.quantity),
            )
            for line in stock
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _validate_mode(custody_mode, due_at):
    if custody_mode not in ServiceBatch.CustodyMode.values:
        raise ValidationError({"custody_mode": "Modalidade inválida."})
    if custody_mode == ServiceBatch.CustodyMode.FIXED_TERM:
        if not isinstance(due_at, datetime) or timezone.is_naive(due_at):
            raise ValidationError({"due_at": "Prazo determinado exige data e hora com fuso."})
        if due_at <= timezone.now():
            raise ValidationError({"due_at": "O prazo deve estar no futuro."})
    elif due_at is not None:
        raise ValidationError({"due_at": "Esta modalidade não aceita prazo."})


def _authorize_batch_replay(ctx, batch):
    if batch.operator_id != ctx.actor.id:
        raise PermissionDenied
    unit_ids = set(batch.items.values_list("item__unit_id", flat=True))
    unit_ids.update(batch.stock_loans.values_list("balance__unit_id", flat=True))
    for unit in Unit.objects.filter(pk__in=unit_ids):
        if not has_permission(ctx.actor, MOVEMENT_CHECKOUT, ctx.organization, unit):
            raise PermissionDenied


@transaction.atomic
def checkout_basket(
    ctx: CommandContext,
    *,
    recipient_id: UUID,
    item_ids: list[UUID],
    stock: list[StockRequest],
    idempotency_key: UUID,
    custody_mode: str,
    due_at: datetime | None,
    confirmed: bool,
    pickup_person_id: UUID | None = None,
    face_verification_id: UUID | None = None,
    identity_exception=None,
):
    """Atomically deliver a mixed basket; every retry returns the same batch.

    The recipient's identity must be proven by an approved facial verification or by an
    approved signed term (ADR 0008); a retry with the same key returns the batch first.
    """
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    item_ids = list(dict.fromkeys(item_ids))
    if not item_ids and not stock:
        raise ValidationError("Inclua ao menos um item ou material quantitativo.")
    if len(item_ids) > 100 or len(stock) > 100:
        raise ValidationError("Uma cesta aceita no máximo 100 linhas de cada modalidade.")
    request_hash = _request_hash(
        recipient_id=recipient_id,
        pickup_person_id=pickup_person_id,
        custody_mode=custody_mode,
        due_at=due_at,
        item_ids=item_ids,
        stock=stock,
    )
    existing = ServiceBatch.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.request_hash != request_hash:
            raise ConflictError("A chave de idempotência já foi usada em outro atendimento.")
        _authorize_batch_replay(ctx, existing)
        return existing, False

    _validate_mode(custody_mode, due_at)
    recipient = (
        Person.objects.select_for_update()
        .filter(id=recipient_id, organization=ctx.organization, is_active=True)
        .first()
    )
    if not recipient or not recipient.memberships.filter(is_active=True).exists():
        raise ValidationError("Destinatário inválido ou sem vínculo ativo.")
    ensure_not_own_operation(ctx, recipient.id)
    # Another request with this key may have committed while we waited for the person.
    existing = ServiceBatch.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.request_hash != request_hash:
            raise ConflictError("A chave de idempotência já foi usada em outro atendimento.")
        _authorize_batch_replay(ctx, existing)
        return existing, False
    pickup_person = None
    if pickup_person_id:
        raise ValidationError(
            {"pickup_person_id": "Retirada por terceiro não foi autorizada neste incremento."}
        )

    items = list(
        Item.objects.select_for_update()
        .filter(id__in=item_ids, organization=ctx.organization)
        .select_related("unit")
        .order_by("id")
    )
    if len(items) != len(item_ids):
        raise ValidationError("A cesta contém item inválido.")
    for item in items:
        if not has_permission(ctx.actor, MOVEMENT_CHECKOUT, ctx.organization, item.unit):
            raise PermissionDenied

    locked_balances = {}
    for line in sorted(stock, key=lambda value: str(value.storage_location_id)):
        line_quantity = positive_quantity(line.quantity)
        position_key = (
            line.equipment_type_id,
            line.unit_id,
            line.storage_location_id,
        )
        if position_key in locked_balances:
            raise ValidationError({"stock": "Cada posição quantitativa deve aparecer uma vez."})
        balance = (
            StockBalance.objects.select_for_update()
            .filter(
                organization=ctx.organization,
                equipment_type_id=line.equipment_type_id,
                unit_id=line.unit_id,
                storage_location_id=line.storage_location_id,
            )
            .select_related("equipment_type", "unit")
            .first()
        )
        if not balance:
            raise ValidationError("Posição de estoque quantitativo inexistente.")
        if not has_permission(ctx.actor, MOVEMENT_CHECKOUT, ctx.organization, balance.unit):
            raise PermissionDenied
        from sigab.domain.restrictions import assert_eligible

        assert_eligible(ctx, recipient, balance.equipment_type_id)
        if balance.quantity < line_quantity:
            raise ConflictError("Saldo quantitativo insuficiente.")
        locked_balances[position_key] = (balance, line_quantity)

    # Consume the verification only after every authorization and availability check.
    identity = resolve_identity(
        ctx,
        person=recipient,
        operation=IdentityOperation.CHECKOUT,
        face_verification_id=face_verification_id,
        identity_exception=identity_exception,
    )
    now = timezone.now()
    batch = ServiceBatch.objects.create(
        organization=ctx.organization,
        recipient=recipient,
        pickup_person=pickup_person,
        operator=ctx.actor,
        custody_mode=custody_mode,
        due_at=due_at,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        confirmed_at=now,
        receipt_code=f"AT-{idempotency_key.hex[:16].upper()}",
        **identity,
    )
    for item in items:
        movement, _ = checkout_item(
            ctx,
            item_id=item.id,
            recipient_id=recipient.id,
            idempotency_key=uuid5(idempotency_key, str(item.id)),
            confirmed=True,
        )
        ServiceBatchItem.objects.create(batch=batch, item=item, movement=movement)

    for key, (balance, quantity) in locked_balances.items():
        updated = StockBalance.objects.filter(pk=balance.pk, quantity__gte=quantity).update(
            quantity=F("quantity") - quantity,
            updated_at=now,
        )
        if updated != 1:
            raise ConflictError("Saldo quantitativo foi alterado por outro atendimento.")
        loan = StockLoan.objects.create(
            organization=ctx.organization,
            batch=batch,
            balance=balance,
            recipient=recipient,
            original_quantity=quantity,
            open_quantity=quantity,
            due_at=due_at,
        )
        StockLedgerEntry.objects.create(
            organization=ctx.organization,
            balance=balance,
            loan=loan,
            entry_type=StockLedgerEntry.Type.CHECKOUT,
            quantity=quantity,
            balance_delta=-quantity,
            operator=ctx.actor,
            recipient=recipient,
            idempotency_key=uuid5(idempotency_key, ":".join(str(value) for value in key)),
            occurred_at=now,
        )
    audit(
        ctx,
        "service_batch.checkout",
        batch,
        {
            "recipient_id": str(recipient.id),
            "individual_items": len(items),
            "stock_lines": len(stock),
            "receipt_code": batch.receipt_code,
        },
    )
    return batch, True


@transaction.atomic
def settle_stock_loan(
    ctx,
    *,
    loan_id,
    quantity,
    disposition,
    idempotency_key,
    confirmed,
    reason="",
):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    if disposition not in (StockLedgerEntry.Type.RETURN, StockLedgerEntry.Type.CONSUME):
        raise ValidationError({"disposition": "Use return ou consume."})
    quantity = positive_quantity(quantity)
    existing = StockLedgerEntry.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        if (
            existing.loan_id != loan_id
            or existing.entry_type != disposition
            or existing.quantity != quantity
        ):
            raise ConflictError("A chave de idempotência já foi usada em outra operação.")
        if not has_permission(ctx.actor, MOVEMENT_RETURN, ctx.organization, existing.balance.unit):
            raise PermissionDenied
        if existing.operator_id != ctx.actor.id or existing.reason != (reason or "").strip():
            raise ConflictError("A chave de idempotência já foi usada em outra operação.")
        return existing, False
    loan = (
        StockLoan.objects.select_for_update(of=("self",))
        .filter(pk=loan_id, organization=ctx.organization)
        .select_related("balance__unit", "recipient")
        .first()
    )
    if not loan:
        raise NotFoundError
    permission = MOVEMENT_RETURN
    if not has_permission(ctx.actor, permission, ctx.organization, loan.balance.unit):
        raise PermissionDenied
    if quantity > loan.open_quantity:
        raise ConflictError("A quantidade excede a pendência aberta.")
    reason = (reason or "").strip()
    if disposition == StockLedgerEntry.Type.CONSUME and not reason:
        raise ValidationError({"reason": "Consumo exige justificativa."})
    if len(reason) > 500:
        raise ValidationError({"reason": "Use no máximo 500 caracteres."})
    now = timezone.now()
    balance_delta = quantity if disposition == StockLedgerEntry.Type.RETURN else Decimal("0")
    if balance_delta:
        StockBalance.objects.filter(pk=loan.balance_id).update(
            quantity=F("quantity") + quantity, updated_at=now
        )
    loan.open_quantity -= quantity
    loan.status = StockLoan.Status.CLOSED if loan.open_quantity == 0 else StockLoan.Status.OPEN
    loan.save(update_fields=["open_quantity", "status", "updated_at"])
    entry = StockLedgerEntry.objects.create(
        organization=ctx.organization,
        balance=loan.balance,
        loan=loan,
        entry_type=disposition,
        quantity=quantity,
        balance_delta=balance_delta,
        operator=ctx.actor,
        recipient=loan.recipient,
        idempotency_key=idempotency_key,
        occurred_at=now,
        reason=reason,
    )
    audit(
        ctx,
        f"stock.{disposition}",
        entry,
        {"loan_id": str(loan.id), "quantity": str(quantity)},
        reason=reason,
    )
    return entry, True


@transaction.atomic
def adjust_stock(ctx, *, balance_id, quantity_delta, idempotency_key, reason, confirmed):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    try:
        delta = Decimal(str(quantity_delta))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({"quantity_delta": "Informe uma quantidade válida."}) from exc
    if delta == 0 or delta.as_tuple().exponent < -3:
        raise ValidationError({"quantity_delta": "O ajuste deve ser não nulo."})
    existing = StockLedgerEntry.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.balance_id != balance_id or existing.balance_delta != delta:
            raise ConflictError("A chave de idempotência já foi usada em outra operação.")
        return existing, False
    balance = (
        StockBalance.objects.select_for_update()
        .filter(pk=balance_id, organization=ctx.organization)
        .select_related("unit")
        .first()
    )
    if not balance:
        raise ValidationError("Posição de estoque inválida.")
    if not has_permission(ctx.actor, "inventory.adjust.approve", ctx.organization, balance.unit):
        raise PermissionDenied
    if balance.quantity + delta < 0:
        raise ConflictError("O ajuste não pode produzir saldo negativo.")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Ajuste exige justificativa."})
    now = timezone.now()
    StockBalance.objects.filter(pk=balance.pk).update(
        quantity=F("quantity") + delta, updated_at=now
    )
    entry = StockLedgerEntry.objects.create(
        organization=ctx.organization,
        balance=balance,
        entry_type=StockLedgerEntry.Type.ADJUST,
        quantity=abs(delta),
        balance_delta=delta,
        operator=ctx.actor,
        idempotency_key=idempotency_key,
        occurred_at=now,
        reason=reason,
    )
    audit(
        ctx,
        "stock.adjust",
        entry,
        {"balance_id": str(balance.id), "delta": str(delta)},
        reason=reason,
    )
    return entry, True


@transaction.atomic
def receive_stock(
    ctx,
    *,
    equipment_type_id,
    unit_id,
    storage_location_id,
    quantity,
    idempotency_key,
    reason,
    confirmed,
):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    quantity = positive_quantity(quantity)
    existing = StockLedgerEntry.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        if (
            existing.entry_type != StockLedgerEntry.Type.RECEIPT
            or existing.quantity != quantity
            or existing.balance.equipment_type_id != equipment_type_id
            or existing.balance.unit_id != unit_id
            or existing.balance.storage_location_id != storage_location_id
        ):
            raise ConflictError("A chave de idempotência já foi usada em outra operação.")
        if not has_permission(
            ctx.actor, "inventory.adjust.approve", ctx.organization, existing.balance.unit
        ):
            raise PermissionDenied
        if existing.operator_id != ctx.actor.id or existing.reason != (reason or "").strip():
            raise ConflictError("A chave de idempotência já foi usada em outra operação.")
        return existing, False
    equipment_type = EquipmentType.objects.filter(
        pk=equipment_type_id,
        organization=ctx.organization,
        classification=EquipmentType.Classification.QUANTITATIVE,
        is_active=True,
    ).first()
    unit = Unit.objects.filter(pk=unit_id, organization=ctx.organization, is_active=True).first()
    location = StorageLocation.objects.filter(
        pk=storage_location_id,
        organization=ctx.organization,
        unit_id=unit_id,
        is_active=True,
    ).first()
    if not equipment_type or not unit or not location:
        raise ValidationError("Tipo, unidade ou local quantitativo inválido.")
    if not has_permission(ctx.actor, "inventory.adjust.approve", ctx.organization, unit):
        raise PermissionDenied
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Entrada exige referência ou justificativa."})
    balance, _ = StockBalance.objects.select_for_update().get_or_create(
        organization=ctx.organization,
        equipment_type=equipment_type,
        unit=unit,
        storage_location=location,
        defaults={"quantity": 0},
    )
    now = timezone.now()
    StockBalance.objects.filter(pk=balance.pk).update(
        quantity=F("quantity") + quantity, updated_at=now
    )
    entry = StockLedgerEntry.objects.create(
        organization=ctx.organization,
        balance=balance,
        entry_type=StockLedgerEntry.Type.RECEIPT,
        quantity=quantity,
        balance_delta=quantity,
        operator=ctx.actor,
        idempotency_key=idempotency_key,
        occurred_at=now,
        reason=reason,
    )
    audit(
        ctx,
        "stock.receipt",
        entry,
        {"balance_id": str(balance.id), "quantity": str(quantity)},
        reason=reason,
    )
    return entry, True


@transaction.atomic
def reverse_stock_entry(ctx, *, entry_id, idempotency_key, reason, confirmed):
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    existing = StockLedgerEntry.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        if (
            existing.entry_type != StockLedgerEntry.Type.REVERSAL
            or existing.reverses_id != entry_id
        ):
            raise ConflictError("A chave de idempotência já foi usada em outra operação.")
        return existing, False
    original = (
        StockLedgerEntry.objects.select_for_update(of=("self",))
        .filter(pk=entry_id, organization=ctx.organization)
        .select_related("balance__unit")
        .first()
    )
    if not original:
        raise NotFoundError
    if original.entry_type == StockLedgerEntry.Type.REVERSAL or hasattr(original, "reversal"):
        raise ConflictError("O lançamento não pode ser estornado novamente.")
    if not has_permission(ctx.actor, "movement.reverse", ctx.organization, original.balance.unit):
        raise PermissionDenied
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Estorno exige justificativa."})
    loan = None
    if original.loan_id:
        loan = StockLoan.objects.select_for_update().get(pk=original.loan_id)
    balance = StockBalance.objects.select_for_update().get(pk=original.balance_id)
    reverse_delta = -original.balance_delta
    if balance.quantity + reverse_delta < 0:
        raise ConflictError("O estorno produziria saldo negativo.")
    if original.entry_type == StockLedgerEntry.Type.CHECKOUT:
        if not loan or loan.open_quantity != loan.original_quantity:
            raise ConflictError(
                "Saída com devolução ou consumo não pode ser estornada integralmente."
            )
        loan.open_quantity = Decimal("0")
        loan.status = StockLoan.Status.CLOSED
    elif original.entry_type in (StockLedgerEntry.Type.RETURN, StockLedgerEntry.Type.CONSUME):
        if not loan or loan.open_quantity + original.quantity > loan.original_quantity:
            raise ConflictError("A pendência não comporta este estorno.")
        loan.open_quantity += original.quantity
        loan.status = StockLoan.Status.OPEN
    now = timezone.now()
    if reverse_delta:
        StockBalance.objects.filter(pk=balance.pk).update(
            quantity=F("quantity") + reverse_delta, updated_at=now
        )
    if loan:
        loan.save(update_fields=["open_quantity", "status", "updated_at"])
    reversal = StockLedgerEntry.objects.create(
        organization=ctx.organization,
        balance=balance,
        loan=loan,
        entry_type=StockLedgerEntry.Type.REVERSAL,
        quantity=original.quantity,
        balance_delta=reverse_delta,
        operator=ctx.actor,
        recipient=original.recipient,
        idempotency_key=idempotency_key,
        occurred_at=now,
        reason=reason,
        reverses=original,
    )
    audit(
        ctx,
        "stock.reverse",
        reversal,
        {"original_entry_id": str(original.id), "balance_delta": str(reverse_delta)},
        reason=reason,
    )
    return reversal, True


# Counter return of several materials of one person (SIGAB-082, RF-20 to RF-23).


@dataclass(frozen=True)
class ItemReturnLine:
    item_id: UUID
    condition: str
    reason: str = ""


@dataclass(frozen=True)
class StockReturnLine:
    loan_id: UUID
    quantity: Decimal


def _return_hash(*, person_id, items, stock):
    payload = {
        "person_id": str(person_id),
        "items": sorted(
            (str(line.item_id), line.condition, (line.reason or "").strip()) for line in items
        ),
        "stock": sorted((str(line.loan_id), str(line.quantity)) for line in stock),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _replay_return(ctx, batch, request_hash):
    if batch.request_hash != request_hash:
        raise ConflictError("A chave de idempotência já foi usada em outra devolução.")
    if batch.operator_id != ctx.actor.id:
        raise PermissionDenied
    unit_ids = set(batch.items.values_list("movement__item__unit_id", flat=True))
    unit_ids.update(batch.stock_lines.values_list("entry__balance__unit_id", flat=True))
    for unit in Unit.objects.filter(pk__in=unit_ids):
        if not has_permission(ctx.actor, MOVEMENT_RETURN, ctx.organization, unit):
            raise PermissionDenied
    return batch, False


@transaction.atomic
def return_basket(
    ctx: CommandContext,
    *,
    person_id: UUID,
    items: list[ItemReturnLine],
    stock: list[StockReturnLine],
    idempotency_key: UUID,
    confirmed: bool,
    face_verification_id: UUID | None = None,
    identity_exception=None,
):
    """Atomically return several materials held by one person.

    Every line is checked item by item (fit or unfit for registered items; fit return
    of an open quantity for material without registration). Concurrent confirmations
    for the same person serialize on the person row: exactly one is accepted and a
    retry with the same key returns the same batch.
    """
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    if not items and not stock:
        raise ValidationError("Inclua ao menos um item ou material sem registro.")
    if len(items) > 100 or len(stock) > 100:
        raise ValidationError("Uma devolução aceita no máximo 100 linhas de cada modalidade.")
    if len({line.item_id for line in items}) != len(items):
        raise ValidationError({"items": "Cada item deve aparecer uma vez."})
    if len({line.loan_id for line in stock}) != len(stock):
        raise ValidationError({"stock": "Cada pendência deve aparecer uma vez."})
    for line in items:
        if line.condition not in Item.Condition.values:
            raise ValidationError({"items": "Informe apto ou inapto para cada item."})
    stock = [StockReturnLine(line.loan_id, positive_quantity(line.quantity)) for line in stock]
    request_hash = _return_hash(person_id=person_id, items=items, stock=stock)

    existing = ReturnBatch.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        return _replay_return(ctx, existing, request_hash)
    # Returns are never blocked by an inactive person or membership (RN-07).
    person = (
        Person.objects.select_for_update()
        .filter(id=person_id, organization=ctx.organization)
        .first()
    )
    if not person:
        raise ValidationError("Pessoa inválida.")
    ensure_not_own_operation(ctx, person.id)
    existing = ReturnBatch.objects.filter(
        organization=ctx.organization, idempotency_key=idempotency_key
    ).first()
    if existing:
        return _replay_return(ctx, existing, request_hash)

    locked_items = {
        item.id: item
        for item in Item.objects.select_for_update()
        .filter(id__in=[line.item_id for line in items], organization=ctx.organization)
        .select_related("unit")
    }
    if len(locked_items) != len(items):
        raise ValidationError("A devolução contém item inválido.")
    for item in locked_items.values():
        if not has_permission(ctx.actor, MOVEMENT_RETURN, ctx.organization, item.unit):
            raise PermissionDenied
        if item.availability != Item.Availability.IN_CUSTODY or item.current_holder_id != person.id:
            raise ConflictError(f"O item {item.display_identifier} não está em posse desta pessoa.")
    loans = {
        loan.id: loan
        for loan in StockLoan.objects.select_for_update(of=("self",))
        .filter(id__in=[line.loan_id for line in stock], organization=ctx.organization)
        .select_related("balance__unit")
    }
    if len(loans) != len(stock):
        raise ValidationError("A devolução contém pendência inválida.")
    if identity_exception is None:
        # Material covered by an open signed term waits for the administrator's decision.
        pending_items, pending_loans = pending_return_lines(ctx.organization, person.id)
        if {str(line.item_id) for line in items} & pending_items or {
            str(line.loan_id) for line in stock
        } & pending_loans:
            raise ConflictError("Há material desta devolução em termo aguardando aprovação.")
    for line in stock:
        loan = loans[line.loan_id]
        if not has_permission(ctx.actor, MOVEMENT_RETURN, ctx.organization, loan.balance.unit):
            raise PermissionDenied
        if loan.recipient_id != person.id:
            raise ConflictError("A pendência não pertence a esta pessoa.")
        if line.quantity > loan.open_quantity:
            raise ConflictError("A quantidade excede a pendência aberta.")

    identity = resolve_identity(
        ctx,
        person=person,
        operation=IdentityOperation.RETURN,
        face_verification_id=face_verification_id,
        identity_exception=identity_exception,
    )
    now = timezone.now()
    batch = ReturnBatch.objects.create(
        organization=ctx.organization,
        person=person,
        operator=ctx.actor,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        confirmed_at=now,
        receipt_code=f"DV-{idempotency_key.hex[:16].upper()}",
        **identity,
    )
    for line in sorted(items, key=lambda value: str(value.item_id)):
        movement, _ = return_item(
            ctx,
            item_id=line.item_id,
            condition=line.condition,
            reason=line.reason,
            idempotency_key=uuid5(idempotency_key, f"item:{line.item_id}"),
            confirmed=True,
        )
        ReturnBatchItem.objects.create(batch=batch, movement=movement)
    for line in sorted(stock, key=lambda value: str(value.loan_id)):
        entry, _ = settle_stock_loan(
            ctx,
            loan_id=line.loan_id,
            quantity=line.quantity,
            disposition=StockLedgerEntry.Type.RETURN,
            idempotency_key=uuid5(idempotency_key, f"loan:{line.loan_id}"),
            confirmed=True,
        )
        ReturnBatchStock.objects.create(batch=batch, entry=entry)
    audit(
        ctx,
        "return_batch.confirmed",
        batch,
        {
            "person_id": str(person.id),
            "individual_items": len(items),
            "unfit_items": sum(1 for line in items if line.condition == Item.Condition.UNFIT),
            "stock_lines": len(stock),
            "receipt_code": batch.receipt_code,
        },
    )
    return batch, True
