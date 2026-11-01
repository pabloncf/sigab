import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
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


class Person(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="people")
    name = models.CharField(max_length=180)
    functional_name = models.CharField(max_length=120, blank=True)
    cpf = models.CharField(max_length=11, blank=True)
    phone = models.CharField(max_length=24, blank=True)
    is_active = models.BooleanField(default=True)

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
                fields=["organization", "registration"], name="uniq_registration_org"
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
    person = models.OneToOneField(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="account"
    )
    session_version = models.PositiveIntegerField(default=1)

    def clean(self):
        if self.person_id and self.organization_id != self.person.organization_id:
            raise ValidationError("Conta e pessoa devem pertencer à mesma organização.")


class Role(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.PROTECT, related_name="roles"
    )
    name = models.CharField(max_length=80)
    permissions = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_role_name_org")
        ]


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

    def clean(self):
        related = [self.account.organization_id, self.role.organization_id or self.organization_id]
        if self.unit_id:
            related.append(self.unit.organization_id)
        if any(org_id != self.organization_id for org_id in related):
            raise ValidationError("Concessão contém referência de outra organização.")
        if self.scope_type == self.Scope.UNIT and not self.unit_id:
            raise ValidationError("Escopo de unidade exige uma unidade.")


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
        if (
            self.pk
            and EquipmentType.objects.filter(pk=self.pk, items__isnull=False)
            .exclude(classification=self.classification)
            .exists()
        ):
            raise ValidationError("A classificação de um tipo em uso não pode ser alterada.")
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

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"], name="uniq_movement_idempotency_org"
            )
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

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [models.Index(fields=["organization", "occurred_at"])]
