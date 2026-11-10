import hashlib
import json
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        INACTIVE = "inactive", "Inativa"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    timezone = models.CharField(max_length=64, default="America/Fortaleza")
    status = models.CharField(max_length=16, choices=Status, default=Status.ACTIVE)

    def __str__(self):
        return self.name


class Unit(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="units")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_unit_code_org")
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class StorageLocation(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="locations"
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="locations")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_location_code_org")
        ]

    def clean(self):
        if self.unit_id and self.organization_id != self.unit.organization_id:
            raise ValidationError("O local e a unidade devem pertencer à mesma organização.")

    def __str__(self):
        return f"{self.code} — {self.name}"


def validate_cpf(value):
    """Check the 11-digit form and both verification digits; the value is never echoed."""
    if not (len(value) == 11 and value.isdigit()) or value == value[0] * 11:
        raise ValidationError({"cpf": "CPF inválido."})
    for size in (9, 10):
        total = sum(int(digit) * (size + 1 - index) for index, digit in enumerate(value[:size]))
        if (total * 10 % 11) % 10 != int(value[size]):
            raise ValidationError({"cpf": "CPF inválido."})


class Person(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="people")
    name = models.CharField(max_length=180)
    functional_name = models.CharField(max_length=120, blank=True)
    cpf = models.CharField(max_length=11, blank=True)
    phone = models.CharField(max_length=24, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # RN-01: one registration per person in each organization, when CPF is known.
            models.UniqueConstraint(
                fields=["organization", "cpf"],
                condition=~Q(cpf=""),
                name="uniq_person_cpf_org",
                violation_error_message="Já existe pessoa com este CPF nesta organização.",
            )
        ]

    def clean(self):
        if self.cpf:
            validate_cpf(self.cpf)

    def __str__(self):
        return self.functional_name or self.name


class Membership(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="memberships"
    )
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="memberships")
    registration = models.CharField(max_length=64)
    main_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="memberships")
    rank = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "registration"],
                name="uniq_registration_org",
                violation_error_message="Matrícula já cadastrada nesta organização.",
            )
        ]

    def clean(self):
        ids = {self.organization_id, self.person.organization_id, self.main_unit.organization_id}
        if len(ids) != 1:
            raise ValidationError("Pessoa, vínculo e unidade devem pertencer à mesma organização.")


class Account(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.PROTECT, related_name="accounts"
    )
    # A person keeps revoked accounts in history and may receive a new one afterwards;
    # at most one account per person is not revoked.
    person = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="accounts"
    )
    session_version = models.PositiveIntegerField(default=1)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["person"],
                condition=Q(revoked_at__isnull=True),
                name="uniq_open_account_per_person",
                violation_error_message="A pessoa já possui conta não revogada.",
            ),
            models.CheckConstraint(
                condition=Q(revoked_at__isnull=True) | Q(is_active=False),
                name="revoked_account_is_inactive",
            ),
        ]

    @property
    def status(self):
        if self.revoked_at:
            return "revoked"
        return "active" if self.is_active else "suspended"

    def clean(self):
        super().clean()
        if self.person_id and self.organization_id != self.person.organization_id:
            raise ValidationError("Conta e pessoa devem pertencer à mesma organização.")


def default_allowed_scopes():
    return ["organization", "unit"]


class Role(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.PROTECT, related_name="roles"
    )
    name = models.CharField(max_length=80)
    permissions = models.JSONField(default=list)
    # Scopes in which the role may be granted (decision 0002, "Escopo permitido").
    allowed_scopes = models.JSONField(default=default_allowed_scopes)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_role_name_org")
        ]

    def clean(self):
        from .permissions import TENANT_PERMISSIONS

        if (
            not isinstance(self.permissions, list)
            or not set(self.permissions) <= TENANT_PERMISSIONS
        ):
            raise ValidationError({"permissions": "Papel contém permissão fora da matriz."})
        scopes = set(self.allowed_scopes or [])
        if not scopes or not scopes <= {"organization", "unit"}:
            raise ValidationError({"allowed_scopes": "Escopo permitido inválido."})


class Grant(TimestampedModel):
    class Scope(models.TextChoices):
        ORGANIZATION = "organization", "Organização"
        UNIT = "unit", "Unidade"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="grants")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="grants")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="grants")
    scope_type = models.CharField(max_length=20, choices=Scope)
    unit = models.ForeignKey(
        Unit, null=True, blank=True, on_delete=models.PROTECT, related_name="grants"
    )
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        Account, null=True, on_delete=models.PROTECT, related_name="grants_made"
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(scope_type="organization") & Q(unit__isnull=True))
                | (Q(scope_type="unit") & Q(unit__isnull=False)),
                name="grant_scope_matches_unit",
            ),
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True)
                | Q(valid_until__isnull=True)
                | Q(valid_until__gt=models.F("valid_from")),
                name="grant_validity_window",
            ),
        ]

    def clean(self):
        related = [self.account.organization_id, self.role.organization_id]
        if self.unit_id:
            related.append(self.unit.organization_id)
        if any(org_id != self.organization_id for org_id in related):
            raise ValidationError("Concessão contém referência de outra organização.")
        if self.scope_type == self.Scope.UNIT and not self.unit_id:
            raise ValidationError({"unit": "Escopo de unidade exige uma unidade."})
        if self.scope_type == self.Scope.ORGANIZATION and self.unit_id:
            raise ValidationError({"unit": "Escopo de organização não aceita unidade."})
        if self.scope_type not in (self.role.allowed_scopes or []):
            raise ValidationError({"scope_type": "O papel não pode ser concedido neste escopo."})
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValidationError(
                {"valid_until": "O fim da vigência deve ser posterior ao início."}
            )


class EquipmentType(TimestampedModel):
    class Classification(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        QUANTITATIVE = "quantitative", "Quantitativo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="equipment_types"
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    classification = models.CharField(max_length=16, choices=Classification)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_equipment_type_org")
        ]

    def save(self, *args, **kwargs):
        # RN-03/RF-16: the classification never changes after creation (in use or not).
        if (
            self.pk
            and EquipmentType.objects.filter(pk=self.pk)
            .exclude(classification=self.classification)
            .exists()
        ):
            raise ValidationError("A classificação de um tipo não pode ser alterada.")
        super().save(*args, **kwargs)


class Item(TimestampedModel):
    class AdministrativeStatus(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"

    class Condition(models.TextChoices):
        FIT = "fit", "Apto"
        UNFIT = "unfit", "Inapto"

    class Availability(models.TextChoices):
        AVAILABLE = "available", "Disponível"
        IN_CUSTODY = "in_custody", "Em posse"
        UNAVAILABLE = "unavailable", "Indisponível"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="items")
    equipment_type = models.ForeignKey(
        EquipmentType, on_delete=models.PROTECT, related_name="items"
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="items")
    storage_location = models.ForeignKey(
        StorageLocation, on_delete=models.PROTECT, related_name="items"
    )
    serial_number = models.CharField(max_length=100, blank=True)
    asset_number = models.CharField(max_length=100, blank=True)
    official_identifier = models.CharField(max_length=100, blank=True)
    administrative_status = models.CharField(
        max_length=16, choices=AdministrativeStatus, default=AdministrativeStatus.ACTIVE
    )
    condition = models.CharField(max_length=16, choices=Condition, default=Condition.FIT)
    condition_reason = models.CharField(max_length=200, blank=True)
    availability = models.CharField(
        max_length=16, choices=Availability, default=Availability.AVAILABLE
    )
    current_holder = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="held_items"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "serial_number"],
                condition=~Q(serial_number=""),
                name="uniq_item_serial_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "asset_number"],
                condition=~Q(asset_number=""),
                name="uniq_item_asset_org",
            ),
            models.CheckConstraint(
                condition=(Q(condition="fit") & Q(condition_reason=""))
                | (Q(condition="unfit") & ~Q(condition_reason="")),
                name="item_unfit_requires_reason",
            ),
        ]

    def clean(self):
        refs = [
            self.equipment_type.organization_id,
            self.unit.organization_id,
            self.storage_location.organization_id,
        ]
        if self.current_holder_id:
            refs.append(self.current_holder.organization_id)
        if any(org_id != self.organization_id for org_id in refs):
            raise ValidationError("Item contém referência de outra organização.")
        if self.storage_location.unit_id != self.unit_id:
            raise ValidationError("O local de guarda deve pertencer à unidade informada.")
        if self.equipment_type.classification != EquipmentType.Classification.INDIVIDUAL:
            raise ValidationError("Este fluxo aceita somente tipo individual.")
        if self.condition == self.Condition.UNFIT and not self.condition_reason.strip():
            raise ValidationError("Item inapto exige motivo.")
        if self.condition == self.Condition.FIT and self.condition_reason:
            raise ValidationError("Motivo de inapto só se aplica a item inapto.")

    @property
    def display_identifier(self):
        return self.serial_number or self.asset_number or str(self.id)


class AppendOnlyQuerySet(models.QuerySet):
    """Block bulk writes that bypass the per-instance immutability guards."""

    def update(self, **kwargs):
        raise ValidationError("Registros confirmados são imutáveis.")

    def delete(self):
        raise ValidationError("Registros confirmados não podem ser apagados.")


class Movement(TimestampedModel):
    class Type(models.TextChoices):
        INCORPORATION = "incorporation", "Incorporação"
        CHECKOUT = "checkout", "Saída"
        RETURN = "return", "Devolução"
        CONDITION_CHANGE = "condition_change", "Alteração de condição"
        REVERSAL = "reversal", "Estorno"

    class Origin(models.TextChoices):
        SYSTEM = "system", "Sistema"
        CONTINGENCY = "contingency", "Contingência"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.CharField(max_length=16, choices=Type)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    operator = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="operated_movements"
    )
    recipient = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="movements"
    )
    related_movement = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="responses"
    )
    idempotency_key = models.UUIDField()
    confirmed_at = models.DateTimeField()
    condition_on_return = models.CharField(max_length=16, choices=Item.Condition, blank=True)
    new_condition = models.CharField(max_length=16, choices=Item.Condition, blank=True)
    condition_reason = models.CharField(max_length=200, blank=True)
    # Reversal (ADR 0006, section 4): a compensating movement, at most one per original.
    reverses = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal"
    )
    reason = models.CharField(max_length=500, blank=True)
    # Contingency (SIGAB-046, ADR 0004): a fact recorded on paper while the system was down.
    # `declared_occurred_at` is when it happened; `confirmed_at` stays the registration instant.
    origin = models.CharField(max_length=16, choices=Origin, default=Origin.SYSTEM)
    declared_occurred_at = models.DateTimeField(null=True, blank=True)
    paper_reference = models.CharField(max_length=64, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"], name="uniq_movement_idempotency_org"
            ),
            models.CheckConstraint(
                condition=(
                    Q(origin="system")
                    & Q(declared_occurred_at__isnull=True)
                    & Q(paper_reference="")
                )
                | (
                    Q(origin="contingency")
                    & Q(movement_type__in=["checkout", "return"])
                    & Q(declared_occurred_at__isnull=False)
                    & Q(declared_occurred_at__lte=models.F("confirmed_at"))
                    & ~Q(paper_reference="")
                ),
                name="contingency_has_fact_instant_and_reference",
            ),
            models.CheckConstraint(
                condition=(Q(movement_type="reversal") & Q(reverses__isnull=False) & ~Q(reason=""))
                | (~Q(movement_type="reversal") & Q(reverses__isnull=True)),
                name="reversal_has_original_and_reason",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and Movement.objects.filter(pk=self.pk).exists():
            raise ValidationError("Movimentações confirmadas são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Movimentações confirmadas não podem ser apagadas.")


class ImmutableModel(models.Model):
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Eventos confirmados são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Eventos confirmados não podem ser apagados.")


class MovementEvent(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="movement_events"
    )
    movement = models.ForeignKey(Movement, on_delete=models.PROTECT, related_name="events")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="events")
    event_type = models.CharField(max_length=32)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="movement_events")
    occurred_at = models.DateTimeField()
    schema_version = models.PositiveSmallIntegerField(default=1)
    metadata = models.JSONField(default=dict)
    compensates = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="compensation"
    )

    class Meta:
        ordering = ["occurred_at", "id"]


class AuditEvent(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, null=True, on_delete=models.PROTECT, related_name="audit_events"
    )
    actor = models.ForeignKey(
        Account, null=True, on_delete=models.PROTECT, related_name="audit_events"
    )
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=64)
    occurred_at = models.DateTimeField()
    correlation_id = models.CharField(max_length=64)
    result = models.CharField(max_length=32, default="success")
    changes = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    # Hash chain per organization (SIGAB-035): detects edits or deletions made outside the
    # application, e.g. by direct SQL. Events without organization are not chained.
    sequence = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    previous_hash = models.CharField(max_length=64, blank=True, editable=False)
    record_hash = models.CharField(max_length=64, blank=True, editable=False)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [models.Index(fields=["organization", "occurred_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "sequence"], name="uniq_audit_sequence_org"
            )
        ]

    def save(self, *args, **kwargs):
        if self.organization_id and not self.record_hash:
            with transaction.atomic():
                # Serialize appends per organization so the chain never forks. NO KEY UPDATE
                # does not conflict with the KEY SHARE locks taken by foreign-key inserts.
                Organization.objects.select_for_update(no_key=True).filter(
                    pk=self.organization_id
                ).first()
                last = (
                    AuditEvent.objects.filter(organization_id=self.organization_id)
                    .order_by("-sequence")
                    .first()
                )
                self.sequence = (last.sequence if last else 0) + 1
                self.previous_hash = last.record_hash if last else ""
                self.record_hash = audit_record_hash(self)
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)


def audit_record_hash(event):
    """SHA-256 over the canonical content of an audit event and the previous hash."""
    payload = {
        "sequence": event.sequence,
        "previous_hash": event.previous_hash,
        "id": str(event.id),
        "organization_id": str(event.organization_id) if event.organization_id else None,
        "actor_id": str(event.actor_id) if event.actor_id else None,
        "action": event.action,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "occurred_at": event.occurred_at.isoformat(),
        "correlation_id": event.correlation_id,
        "result": event.result,
        "changes": event.changes,
        "reason": event.reason,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class ServiceBatch(TimestampedModel):
    """One confirmed counter service containing individual and quantitative materials."""

    class CustodyMode(models.TextChoices):
        SHIFT = "shift", "Por turno"
        FIXED_TERM = "fixed_term", "Prazo determinado"
        INDEFINITE = "indefinite", "Prazo indeterminado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="service_batches"
    )
    recipient = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="service_batches")
    # Kept separate from the authenticated operator. It is populated only when an
    # explicitly authorized workflow supplies a third-party pickup person.
    pickup_person = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="picked_up_service_batches",
    )
    operator = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="operated_service_batches"
    )
    custody_mode = models.CharField(max_length=16, choices=CustodyMode)
    due_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.UUIDField()
    request_hash = models.CharField(max_length=64)
    confirmed_at = models.DateTimeField()
    receipt_code = models.CharField(max_length=24)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                name="uniq_service_batch_idempotency_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "receipt_code"], name="uniq_service_receipt_org"
            ),
            models.CheckConstraint(
                condition=(Q(custody_mode="fixed_term") & Q(due_at__isnull=False))
                | (~Q(custody_mode="fixed_term") & Q(due_at__isnull=True)),
                name="service_due_matches_mode",
            ),
        ]


class ServiceBatchItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ServiceBatch, on_delete=models.PROTECT, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="service_lines")
    movement = models.OneToOneField(
        Movement, on_delete=models.PROTECT, related_name="service_batch_line"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "item"], name="uniq_item_per_service_batch")
        ]


class StockBalance(TimestampedModel):
    """Current quantitative stock, locked before every write."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="stock_balances"
    )
    equipment_type = models.ForeignKey(
        EquipmentType, on_delete=models.PROTECT, related_name="stock_balances"
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="stock_balances")
    storage_location = models.ForeignKey(
        StorageLocation, on_delete=models.PROTECT, related_name="stock_balances"
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "equipment_type", "unit", "storage_location"],
                name="uniq_stock_position",
            ),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_quantity_nonnegative"),
        ]

    def clean(self):
        refs = {
            self.equipment_type.organization_id,
            self.unit.organization_id,
            self.storage_location.organization_id,
            self.organization_id,
        }
        if len(refs) != 1 or self.storage_location.unit_id != self.unit_id:
            raise ValidationError("Posição de estoque contém referências incompatíveis.")
        if self.equipment_type.classification != EquipmentType.Classification.QUANTITATIVE:
            raise ValidationError("Posição de estoque exige tipo quantitativo.")


class StockLoan(TimestampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        CLOSED = "closed", "Encerrada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="stock_loans"
    )
    batch = models.ForeignKey(ServiceBatch, on_delete=models.PROTECT, related_name="stock_loans")
    balance = models.ForeignKey(StockBalance, on_delete=models.PROTECT, related_name="loans")
    recipient = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="stock_loans")
    original_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    open_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.OPEN)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "balance"], name="uniq_stock_line_per_batch"),
            models.CheckConstraint(
                condition=Q(original_quantity__gt=0), name="stock_loan_original_positive"
            ),
            models.CheckConstraint(
                condition=Q(open_quantity__gte=0), name="stock_loan_open_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(open_quantity__lte=models.F("original_quantity")),
                name="stock_loan_open_lte_original",
            ),
        ]


class StockLedgerEntry(ImmutableModel):
    class Type(models.TextChoices):
        RECEIPT = "receipt", "Entrada"
        CHECKOUT = "checkout", "Saída"
        RETURN = "return", "Devolução"
        CONSUME = "consume", "Consumo"
        ADJUST = "adjust", "Ajuste"
        REVERSAL = "reversal", "Estorno"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="stock_entries"
    )
    balance = models.ForeignKey(StockBalance, on_delete=models.PROTECT, related_name="entries")
    loan = models.ForeignKey(
        StockLoan, null=True, blank=True, on_delete=models.PROTECT, related_name="entries"
    )
    entry_type = models.CharField(max_length=12, choices=Type)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    balance_delta = models.DecimalField(max_digits=14, decimal_places=3)
    operator = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="operated_stock_entries"
    )
    recipient = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="stock_entries"
    )
    idempotency_key = models.UUIDField()
    occurred_at = models.DateTimeField()
    reason = models.CharField(max_length=500, blank=True)
    reverses = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal"
    )

    class Meta:
        ordering = ["occurred_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                name="uniq_stock_entry_idempotency_org",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="stock_entry_quantity_positive"
            ),
        ]


class InventorySession(TimestampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        CLOSED = "closed", "Fechada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="inventory_sessions"
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="inventory_sessions")
    opened_by = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="opened_inventory_sessions"
    )
    opened_at = models.DateTimeField()
    reference_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.OPEN)


class InventoryCount(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(InventorySession, on_delete=models.PROTECT, related_name="counts")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="inventory_counts")
    expected_state = models.CharField(max_length=24)
    counted_state = models.CharField(max_length=24, blank=True)
    counted_at = models.DateTimeField(null=True, blank=True)
    counted_by = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.PROTECT, related_name="inventory_counts"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "item"], name="uniq_inventory_count_item")
        ]


class InventoryDivergence(TimestampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        INVESTIGATING = "investigating", "Em investigação"
        RESOLVED = "resolved", "Resolvida"
        DISMISSED = "dismissed", "Justificada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        InventorySession, on_delete=models.PROTECT, related_name="divergences"
    )
    count = models.OneToOneField(
        InventoryCount, on_delete=models.PROTECT, related_name="divergence"
    )
    expected_state = models.CharField(max_length=24)
    counted_state = models.CharField(max_length=24)
    status = models.CharField(max_length=16, choices=Status, default=Status.OPEN)
    assignee = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assigned_inventory_divergences",
    )
    reason = models.CharField(max_length=500, blank=True)
    resolution = models.CharField(max_length=500, blank=True)
    resolved_by = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="resolved_inventory_divergences",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)


class AuthenticationFailure(models.Model):
    """Failed login attempt, kept only to rate-limit authentication (SIGAB-021).

    Technical throttling data, not audit: the username is stored as a keyed hash because
    people sometimes type a password into the username field.
    """

    id = models.BigAutoField(primary_key=True)
    username_digest = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    occurred_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["username_digest", "occurred_at"]),
            models.Index(fields=["ip_address", "occurred_at"]),
        ]


class PersonRestriction(TimestampedModel):
    class Category(models.TextChoices):
        JUDICIAL = "judicial", "Judicial"
        HEALTH = "saude", "Saúde"
        ADMINISTRATIVE = "administrativa", "Administrativa"
        OTHER = "outra", "Outra"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="restrictions")
    category = models.CharField(max_length=16, choices=Category)
    summary = models.CharField(max_length=200)
    source = models.CharField(max_length=160)
    reference = models.CharField(max_length=160, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    # Empty means all types. Classification-specific grouping is deliberately not inferred.
    equipment_types = models.ManyToManyField(EquipmentType, blank=True)
    created_by = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="restrictions_created"
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True, related_name="restrictions_closed"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gt=models.F("starts_at")),
                name="restriction_valid_window",
            )
        ]


class RestrictionEvent(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restriction = models.ForeignKey(
        PersonRestriction, on_delete=models.PROTECT, related_name="history"
    )
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    occurred_at = models.DateTimeField()
    action = models.CharField(max_length=16)
    reason = models.CharField(max_length=200)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
