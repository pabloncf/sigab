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

from sigab.models import (
    EquipmentType,
    Item,
    Person,
    ServiceBatch,
    ServiceBatchItem,
    StockBalance,
    StockLedgerEntry,
    StockLoan,
    StorageLocation,
    Unit,
)
from sigab.permissions import MOVEMENT_CHECKOUT, MOVEMENT_RETURN, has_permission
from sigab.services import CommandContext, ConflictError, NotFoundError, audit, checkout_item


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
):
    """Atomically deliver a mixed basket; every retry returns the same batch."""
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
