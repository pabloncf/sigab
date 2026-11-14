from django.db import migrations

# Decision 0002, matrix 1.4.0 (ADR 0008): the inventory administrator manages facial
# biometrics and approves the signed-term exception. Roles created from the template before
# this revision did not receive the new codes; new installations already do.
ROLE_NAME = "Gestor de acervo"
NEW_CODES = ["biometric.manage", "movement.exception.approve"]


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
    dependencies = [("sigab", "0014_facial_biometrics")]

    operations = [migrations.RunPython(forward, backward)]
