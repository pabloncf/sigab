"""Adversarial pre-single-tenant rows, only inside isolated, rollback-only tests.

Production enforces one organization. Retaining these fixtures verifies that historical
foreign references still cannot escape the application's authorization checks. This is
not a supported provisioning path and is never imported by application code.
"""

from django.db import connection
from django.db.models import Max

from sigab.models import Organization


def legacy_organization(**kwargs):
    if not Organization.objects.exists():
        return Organization.objects.create(**kwargs)
    slot = Organization.objects.aggregate(value=Max("installation_key"))["value"] + 1
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA ignore_check_constraints = ON")
        try:
            return Organization.objects.create(installation_key=slot, **kwargs)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA ignore_check_constraints = OFF")
    assert connection.vendor == "postgresql"
    assert connection.in_atomic_block, "Legacy fixtures require a rollback-only test transaction."
    with connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE sigab_organization DROP CONSTRAINT single_organization_installation"
        )
        try:
            org = Organization.objects.create(installation_key=slot, **kwargs)
        finally:
            cursor.execute(
                "ALTER TABLE sigab_organization ADD CONSTRAINT single_organization_installation "
                "CHECK (installation_key = 1) NOT VALID"
            )
    return org
