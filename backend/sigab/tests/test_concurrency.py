"""Real concurrency on PostgreSQL (SIGAB-031). Each attempt uses its own connection."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import IntegrityError, close_old_connections, connection, connections
from django.utils import timezone

from sigab.domain.operations import StockRequest, checkout_basket
from sigab.domain.restrictions import create_restriction
from sigab.management.commands.verify_audit_chain import verify_chain
from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Item,
    Movement,
    MovementEvent,
    Organization,
    PersonRestriction,
    ServiceBatch,
    StockBalance,
    StockLedgerEntry,
    StockLoan,
)
from sigab.services import (
    CommandContext,
    ConflictError,
    Contingency,
    checkout_item,
    return_item,
)

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def postgresql_only():
    if connection.vendor != "postgresql":
        pytest.skip("Concorrência transacional é validada no PostgreSQL.")


def _race(world, operation, keys):
    """Run `operation(ctx, key)` once per key, all released at the same instant."""
    barrier = threading.Barrier(len(keys))

    def attempt(key):
        close_old_connections()
        ctx = CommandContext(
            Account.objects.get(pk=world["account"].pk),
            Organization.objects.get(pk=world["org"].pk),
            f"race-{key}",
        )
        barrier.wait()
        try:
            _, created = operation(ctx, key)
            return "accepted" if created else "replayed"
        except (ConflictError, IntegrityError):
            return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        return sorted(pool.map(attempt, keys))


def _checkout(world):
    return lambda ctx, key: checkout_item(
        ctx,
        item_id=world["item"].id,
        recipient_id=world["person"].id,
        idempotency_key=key,
        confirmed=True,
    )


def _assert_single_checkout(world):
    item = Item.objects.get(pk=world["item"].pk)
    assert item.availability == Item.Availability.IN_CUSTODY
    assert item.current_holder_id == world["person"].id
    checkouts = Movement.objects.filter(item=item, movement_type="checkout")
    assert checkouts.count() == 1
    assert MovementEvent.objects.filter(item=item, event_type="item.checked_out").count() == 1
    assert AuditEvent.objects.filter(action="item.checkout", result="success").count() == 1
    assert verify_chain(world["org"]) is None


def test_two_simultaneous_checkouts_accept_exactly_one(world):
    outcomes = _race(world, _checkout(world), [uuid.uuid4() for _ in range(4)])
    assert outcomes == ["accepted", "conflict", "conflict", "conflict"]
    _assert_single_checkout(world)


def test_simultaneous_retries_with_same_key_record_once(world):
    key = uuid.uuid4()
    outcomes = _race(world, _checkout(world), [key, key, key])
    assert outcomes.count("accepted") == 1
    assert set(outcomes) <= {"accepted", "replayed", "conflict"}
    _assert_single_checkout(world)


def test_two_simultaneous_returns_close_the_checkout_once(world):
    _race(world, _checkout(world), [uuid.uuid4()])
    outcomes = _race(
        world,
        lambda ctx, key: return_item(
            ctx, item_id=world["item"].id, condition="fit", idempotency_key=key, confirmed=True
        ),
        [uuid.uuid4(), uuid.uuid4()],
    )
    assert outcomes == ["accepted", "conflict"]
    item = Item.objects.get(pk=world["item"].pk)
    assert item.availability == Item.Availability.AVAILABLE and item.current_holder is None
    assert Movement.objects.filter(item=item, movement_type="return").count() == 1
    assert verify_chain(world["org"]) is None


def test_live_checkout_racing_a_contingency_entry_accepts_exactly_one(world):
    """Mixing paper and system in one reserve is forbidden (ADR 0004); the bank still holds."""
    fact = timezone.now()
    live_key, paper_key = uuid.uuid4(), uuid.uuid4()

    def operation(ctx, key):
        contingency = Contingency(fact, "F01/L01") if key == paper_key else None
        return checkout_item(
            ctx,
            item_id=world["item"].id,
            recipient_id=world["person"].id,
            idempotency_key=key,
            confirmed=True,
            contingency=contingency,
        )

    outcomes = _race(world, operation, [live_key, paper_key])

    assert outcomes == ["accepted", "conflict"]
    item = Item.objects.get(pk=world["item"].pk)
    assert item.availability == Item.Availability.IN_CUSTODY
    assert Movement.objects.filter(item=item, movement_type="checkout").count() == 1
    assert verify_chain(world["org"]) is None


def test_quantitative_baskets_never_make_stock_negative(world):
    equipment_type = EquipmentType.objects.create(
        organization=world["org"],
        name="Munição concorrente",
        classification=EquipmentType.Classification.QUANTITATIVE,
    )
    balance = StockBalance.objects.create(
        organization=world["org"],
        equipment_type=equipment_type,
        unit=world["unit"],
        storage_location=world["location"],
        quantity=Decimal("5"),
    )

    def operation(ctx, key):
        return checkout_basket(
            ctx,
            recipient_id=world["person"].id,
            item_ids=[],
            stock=[
                StockRequest(
                    equipment_type_id=equipment_type.id,
                    unit_id=world["unit"].id,
                    storage_location_id=world["location"].id,
                    quantity=Decimal("4"),
                )
            ],
            idempotency_key=key,
            custody_mode=ServiceBatch.CustodyMode.INDEFINITE,
            due_at=None,
            confirmed=True,
        )

    outcomes = _race(world, operation, [uuid.uuid4(), uuid.uuid4()])
    assert outcomes == ["accepted", "conflict"]
    balance.refresh_from_db()
    assert balance.quantity == Decimal("1")
    assert StockLoan.objects.filter(balance=balance).count() == 1
    assert (
        StockLedgerEntry.objects.filter(
            balance=balance, entry_type=StockLedgerEntry.Type.CHECKOUT
        ).count()
        == 1
    )


def test_restriction_and_checkout_serialize_on_person(world):
    role = world["account"].grants.get().role
    role.permissions = [*role.permissions, "restriction.manage"]
    role.save()
    registration_key = uuid.uuid4()

    def operation(ctx, key):
        if key == registration_key:
            return create_restriction(
                ctx,
                person_id=world["person"].pk,
                category="administrativa",
                summary="Restrição concorrente",
                source="Comando",
                reference="R1",
                starts_at=timezone.now(),
                ends_at=None,
                equipment_type_ids=[],
                confirmed=True,
            ), True
        return _checkout(world)(ctx, key)

    outcomes = _race(world, operation, [registration_key, uuid.uuid4()])
    assert outcomes in (["accepted", "accepted"], ["accepted", "conflict"])
    restriction = PersonRestriction.objects.get(person=world["person"])
    checkout = Movement.objects.filter(item=world["item"], movement_type="checkout").first()
    if checkout:
        assert checkout.confirmed_at <= restriction.created_at
