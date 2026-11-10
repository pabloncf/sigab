from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied

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
from .permissions import ALL_UNITS, has_any_scope, has_permission, permitted_unit_ids


class TenantReadOnlyAdmin:
    """Tenant data is maintained by confirmed services, including for platform users."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        user = request.user
        if user.is_superuser or not user.organization_id:
            return False
        permission = self.tenant_permission()
        if (
            obj is not None
            and getattr(obj, "organization_id", user.organization_id) != user.organization_id
        ):
            return False
        unit = getattr(obj, "unit", None) if obj is not None else None
        if unit:
            return has_permission(user, permission, user.organization, unit)
        return has_any_scope(user, permission, user.organization)

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def tenant_permission(self):
        if self.model in (Movement, MovementEvent, AuditEvent):
            return "audit.view"
        if self.model is Item:
            return "item.view"
        if self.model in (Unit, StorageLocation, EquipmentType):
            return "catalog.manage"
        return "identity.manage"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not self.has_view_permission(request):
            return queryset.none()
        if self.model is Organization:
            return queryset.filter(pk=request.user.organization_id)
        queryset = queryset.filter(organization_id=request.user.organization_id)
        units = permitted_unit_ids(
            request.user, self.tenant_permission(), request.user.organization
        )
        if units is not ALL_UNITS:
            if self.model is Item:
                queryset = queryset.filter(unit_id__in=units)
            elif self.model in (Movement, MovementEvent):
                queryset = queryset.filter(item__unit_id__in=units)
            elif self.model is AuditEvent:
                # Generic audit objects cannot safely be scoped to units.
                return queryset.none()
        return queryset

    def save_model(self, request, obj, form, change):
        raise PermissionDenied

    def delete_model(self, request, obj):
        raise PermissionDenied


@admin.register(Account)
class AccountAdmin(TenantReadOnlyAdmin, UserAdmin):
    fieldsets = (
        ("SIGAB", {"fields": ("username", "organization", "person", "is_active", "revoked_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (("SIGAB", {"fields": ("organization", "person")}),)


class AuditedAdmin(TenantReadOnlyAdmin, admin.ModelAdmin):
    def get_exclude(self, request, obj=None):
        return ["cpf"] if self.model is Person else super().get_exclude(request, obj)

    def get_readonly_fields(self, request, obj=None):
        excluded = self.get_exclude(request, obj) or []
        return [field.name for field in self.model._meta.fields if field.name not in excluded]


for model in [Unit, StorageLocation, Person, Membership, Role, Grant, EquipmentType]:
    admin.site.register(model, AuditedAdmin)


@admin.register(Organization)
class OrganizationAdmin(AuditedAdmin):
    pass


@admin.register(Item)
class ItemAdmin(AuditedAdmin):
    pass


@admin.register(Movement)
class MovementAdmin(TenantReadOnlyAdmin, admin.ModelAdmin):
    readonly_fields = [field.name for field in Movement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(TenantReadOnlyAdmin, admin.ModelAdmin):
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
