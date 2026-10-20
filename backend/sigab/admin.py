import uuid

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
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
from .services import CommandContext, record_incorporation


@admin.register(Account)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("SIGAB", {"fields": ("organization", "person", "session_version")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (("SIGAB", {"fields": ("organization", "person")}),)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        AuditEvent.objects.create(
            organization=obj.organization,
            actor=request.user,
            action=f"account.{'update' if change else 'create'}",
            object_type=obj._meta.label_lower,
            object_id=str(obj.pk),
            occurred_at=timezone.now(),
            correlation_id=getattr(request, "correlation_id", str(uuid.uuid4())),
            changes={"fields": sorted(form.changed_data)},
        )


class AuditedAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        if self.model is Organization:
            return queryset.filter(pk=request.user.organization_id)
        return queryset.filter(organization_id=request.user.organization_id)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        related = db_field.remote_field.model
        if not request.user.is_superuser and request.user.organization_id:
            if related is Organization:
                kwargs["queryset"] = Organization.objects.filter(pk=request.user.organization_id)
            elif any(field.name == "organization" for field in related._meta.fields):
                kwargs["queryset"] = related.objects.filter(
                    organization_id=request.user.organization_id
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        organization = obj if isinstance(obj, Organization) else getattr(obj, "organization", None)
        AuditEvent.objects.create(
            organization=organization,
            actor=request.user,
            action=f"{obj._meta.label_lower}.{'update' if change else 'create'}",
            object_type=obj._meta.label_lower,
            object_id=str(obj.pk),
            occurred_at=timezone.now(),
            correlation_id=getattr(request, "correlation_id", str(uuid.uuid4())),
            changes={"fields": sorted(form.changed_data)},
        )


for model in [Unit, StorageLocation, Person, Membership, Role, Grant, EquipmentType]:
    admin.site.register(model, AuditedAdmin)


@admin.register(Organization)
class OrganizationAdmin(AuditedAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Item)
class ItemAdmin(AuditedAdmin):
    # Lifecycle state changes only through services (decision 0004).
    state_fields = ["administrative_status", "availability", "current_holder"]
    condition_fields = ["condition", "condition_reason"]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return self.state_fields
        return self.state_fields + self.condition_fields

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return
        obj.availability = (
            Item.Availability.AVAILABLE
            if obj.condition == Item.Condition.FIT
            else Item.Availability.UNAVAILABLE
        )
        admin.ModelAdmin.save_model(self, request, obj, form, change)
        record_incorporation(
            CommandContext(
                actor=request.user,
                organization=obj.organization,
                correlation_id=getattr(request, "correlation_id", str(uuid.uuid4())),
            ),
            obj,
        )


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in Movement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "organization", "actor", "action", "object_type", "result")

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovementEvent)
class MovementEventAdmin(AuditEventAdmin):
    list_display = ("occurred_at", "organization", "actor", "event_type", "item")
