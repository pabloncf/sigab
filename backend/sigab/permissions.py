"""Server-side authorization (decision 0002, matrix 1.2.0).

Default deny. A permission is granted only by an active, unrevoked grant that is in force
now, whose role lists the permission explicitly, in the account's own active organization,
at organization scope or at the unit of the object. Superusers and other platform
identities receive no tenant permission here: they belong to the control plane.
"""

from django.db.models import Q
from django.utils import timezone

IDENTITY_MANAGE = "identity.manage"
PERSON_VIEW_MINIMAL = "person.view_minimal"
CATALOG_MANAGE = "catalog.manage"
ITEM_VIEW = "item.view"
ITEM_CREATE = "item.create"
ITEM_CONDITION_SET = "item.condition.set"
MOVEMENT_CHECKOUT = "movement.checkout"
MOVEMENT_RETURN = "movement.return"
AUDIT_VIEW = "audit.view"
AUDIT_EXPORT = "audit.export"

# Backwards-compatible names used across views and services.
MANAGE_IDENTITY = IDENTITY_MANAGE
VIEW_ITEM = ITEM_VIEW
SET_ITEM_CONDITION = ITEM_CONDITION_SET

# Codes of the approved matrix that a tenant role may carry. Platform permissions
# (platform.*, support.*) are global and never stored in a tenant role.
TENANT_PERMISSIONS = frozenset(
    {
        IDENTITY_MANAGE,
        PERSON_VIEW_MINIMAL,
        CATALOG_MANAGE,
        ITEM_VIEW,
        ITEM_CREATE,
        ITEM_CONDITION_SET,
        MOVEMENT_CHECKOUT,
        MOVEMENT_RETURN,
        "inventory.adjust.request",
        "inventory.adjust.approve",
        "item.retire.request",
        "item.retire.approve",
        "restriction.view_decision",
        "restriction.manage",
        "restriction.exception.approve",
        AUDIT_VIEW,
        AUDIT_EXPORT,
        "support.session.approve",
    }
)

# Permissions that change data. An independent auditor (marked by audit.export) cannot
# hold any of them in an overlapping scope (separation rule "independent_auditor").
MUTATING_PERMISSIONS = frozenset(
    {
        IDENTITY_MANAGE,
        CATALOG_MANAGE,
        ITEM_CREATE,
        ITEM_CONDITION_SET,
        MOVEMENT_CHECKOUT,
        MOVEMENT_RETURN,
        "inventory.adjust.request",
        "inventory.adjust.approve",
        "item.retire.request",
        "item.retire.approve",
        "restriction.manage",
        "restriction.exception.approve",
    }
)

ALL_UNITS = object()


def _effective_grants(account, organization):
    if not account.is_authenticated or not account.is_active or account.is_superuser:
        return None
    if account.organization_id != organization.id or organization.status != "active":
        return None
    now = timezone.now()
    return (
        account.grants.filter(organization=organization, is_active=True, revoked_at__isnull=True)
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=now))
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
        .select_related("role")
    )


def permitted_unit_ids(account, permission, organization):
    """Return ALL_UNITS for organization-wide access, else the set of unit ids granted."""
    grants = _effective_grants(account, organization)
    if grants is None:
        return set()
    unit_ids = set()
    for grant in grants:
        if permission not in grant.role.permissions:
            continue
        if grant.scope_type == "organization":
            return ALL_UNITS
        if grant.unit_id:
            unit_ids.add(grant.unit_id)
    return unit_ids


def has_permission(account, permission, organization, unit=None):
    unit_ids = permitted_unit_ids(account, permission, organization)
    if unit_ids is ALL_UNITS:
        return True
    return unit is not None and unit.id in unit_ids


def has_any_scope(account, permission, organization):
    """True when the permission is granted somewhere in the organization (for UI flags)."""
    return bool(permitted_unit_ids(account, permission, organization))
