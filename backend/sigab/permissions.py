MANAGE_IDENTITY = "identity.manage"
MANAGE_INVENTORY = "inventory.manage"
MOVE_ITEM = "movement.execute"
VIEW_ITEM = "item.view"
VIEW_AUDIT = "audit.view"
SET_ITEM_CONDITION = "item.condition.set"

OPERATOR_PERMISSIONS = [MANAGE_INVENTORY, MOVE_ITEM, SET_ITEM_CONDITION, VIEW_ITEM]
ADMIN_PERMISSIONS = [
    MANAGE_IDENTITY,
    MANAGE_INVENTORY,
    MOVE_ITEM,
    SET_ITEM_CONDITION,
    VIEW_ITEM,
    VIEW_AUDIT,
]


ALL_UNITS = object()


def permitted_unit_ids(account, permission, organization):
    """Return ALL_UNITS for organization-wide access, else the set of unit ids granted."""
    if not account.is_authenticated or not account.is_active:
        return set()
    if account.is_superuser:
        return ALL_UNITS
    if account.organization_id != organization.id:
        return set()
    unit_ids = set()
    grants = account.grants.filter(
        organization=organization,
        is_active=True,
        revoked_at__isnull=True,
    ).select_related("role")
    for grant in grants:
        if permission not in grant.role.permissions:
            continue
        if grant.scope_type == "organization":
            return ALL_UNITS
        if grant.unit_id:
            unit_ids.add(grant.unit_id)
    return unit_ids


def has_permission(account, permission, organization, unit=None):
    if not account.is_authenticated or not account.is_active:
        return False
    if account.is_superuser:
        return True
    if account.organization_id != organization.id:
        return False
    grants = account.grants.filter(
        organization=organization,
        is_active=True,
        revoked_at__isnull=True,
    ).select_related("role")
    if unit is None:
        return any(
            g.scope_type == "organization" and permission in g.role.permissions for g in grants
        )
    return any(
        permission in g.role.permissions
        and (g.scope_type == "organization" or (g.scope_type == "unit" and g.unit_id == unit.id))
        for g in grants
    )
