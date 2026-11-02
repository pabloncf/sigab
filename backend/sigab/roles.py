"""Tenant role templates of decision 0002 (matrix 1.3.0).

Global roles (platform administrator, support analyst) are control-plane identities and are
never created inside an organization. `test_roles.py` keeps this list equal to the matrix.
"""

ROLE_TEMPLATES = [
    {
        "key": "organization_access_administrator",
        "name": "Administrador de acesso",
        "allowed_scopes": ["organization"],
        "permissions": [
            "identity.manage",
            "person.view_minimal",
            "audit.view",
            "support.session.approve",
        ],
    },
    {
        "key": "organization_inventory_manager",
        "name": "Gestor de acervo",
        "allowed_scopes": ["organization"],
        "permissions": [
            "item.view",
            "person.view_minimal",
            "catalog.manage",
            "item.create",
            "item.condition.set",
            "movement.reverse",
            "inventory.adjust.approve",
            "item.retire.approve",
            "restriction.view_decision",
            "restriction.exception.approve",
            "audit.view",
        ],
    },
    {
        "key": "organization_restriction_manager",
        "name": "Gestor de restrições",
        "allowed_scopes": ["organization"],
        "permissions": [
            "person.view_minimal",
            "restriction.view_decision",
            "restriction.manage",
            "audit.view",
        ],
    },
    {
        "key": "auditor",
        "name": "Auditor",
        "allowed_scopes": ["organization", "unit"],
        "permissions": [
            "item.view",
            "person.view_minimal",
            "restriction.view_decision",
            "audit.view",
            "audit.export",
        ],
    },
    {
        "key": "unit_reserve_operator",
        "name": "Operador de reserva",
        "allowed_scopes": ["unit"],
        "permissions": [
            "item.view",
            "person.view_minimal",
            "item.create",
            "item.condition.set",
            "movement.checkout",
            "movement.return",
            "inventory.adjust.request",
            "item.retire.request",
            "restriction.view_decision",
            "audit.view",
        ],
    },
    {
        "key": "unit_inventory_approver",
        "name": "Aprovador de acervo",
        "allowed_scopes": ["unit"],
        "permissions": [
            "item.view",
            "person.view_minimal",
            "inventory.adjust.approve",
            "item.retire.approve",
            "restriction.view_decision",
            "restriction.exception.approve",
            "audit.view",
        ],
    },
    {
        "key": "unit_reader",
        "name": "Leitor",
        "allowed_scopes": ["unit"],
        "permissions": ["item.view"],
    },
]

INITIAL_ADMINISTRATOR_ROLES = (
    "organization_access_administrator",
    "organization_inventory_manager",
)


def create_tenant_roles(organization):
    """Create the approved tenant roles for a new organization; return them by key."""
    from .models import Role

    return {
        template["key"]: Role.objects.create(
            organization=organization,
            name=template["name"],
            permissions=list(template["permissions"]),
            allowed_scopes=list(template["allowed_scopes"]),
        )
        for template in ROLE_TEMPLATES
    }
