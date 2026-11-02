from django.db import migrations

# Decision 0002: the aggregated codes are replaced by the atomic codes of the matrix.
FORWARD = {
    "inventory.manage": ["catalog.manage", "item.create"],
    "movement.execute": ["movement.checkout", "movement.return"],
}


def _rewrite(apps, mapping):
    Role = apps.get_model("sigab", "Role")
    for role in Role.objects.all():
        permissions = []
        for code in role.permissions:
            for new_code in mapping.get(code, [code]):
                if new_code not in permissions:
                    permissions.append(new_code)
        if permissions != role.permissions:
            role.permissions = permissions
            role.save(update_fields=["permissions"])


def forward(apps, schema_editor):
    _rewrite(apps, FORWARD)


def backward(apps, schema_editor):
    reverse = {}
    for old, new_codes in FORWARD.items():
        for new_code in new_codes:
            reverse[new_code] = [old]
    _rewrite(apps, reverse)


class Migration(migrations.Migration):
    dependencies = [("sigab", "0004_authorization_matrix_and_login_throttle")]

    operations = [migrations.RunPython(forward, backward)]
