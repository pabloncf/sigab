from django.db import migrations

# Decision 0002, matrix 1.5.0: the inventory administrator also registers checkout and return
# of any material. Roles created from the template before this revision did not receive the
# codes; new installations already do.
ROLE_NAME = "Gestor de acervo"
NEW_CODES = ["movement.checkout", "movement.return"]


def forward(apps, schema_editor):
    Role = apps.get_model("sigab", "Role")
    for role in Role.objects.filter(name=ROLE_NAME):
        missing = [code for code in NEW_CODES if code not in role.permissions]
        if missing:
            role.permissions = [*role.permissions, *missing]
            role.save(update_fields=["permissions"])


def backward(apps, schema_editor):
    Role = apps.get_model("sigab", "Role")
    for role in Role.objects.filter(name=ROLE_NAME):
        kept = [code for code in role.permissions if code not in NEW_CODES]
        if kept != role.permissions:
            role.permissions = kept
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [("sigab", "0015_inventory_manager_identity_permissions")]

    operations = [migrations.RunPython(forward, backward)]
