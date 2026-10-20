import uuid
from getpass import getpass

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from sigab.models import Account, AuditEvent, Grant, Organization, Role
from sigab.permissions import ADMIN_PERMISSIONS


class Command(BaseCommand):
    help = "Cria uma organização e seu primeiro administrador de forma atômica."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", help="Se omitida, será solicitada sem eco no terminal.")

    @transaction.atomic
    def handle(self, *args, **options):
        if Account.objects.filter(username=options["username"]).exists():
            raise CommandError("O identificador de login já existe.")
        password = options["password"] or getpass("Senha inicial: ")
        if not password:
            raise CommandError("A senha inicial é obrigatória.")
        now = timezone.now()
        organization = Organization.objects.create(name=options["organization"])
        account = Account.objects.create_user(
            username=options["username"],
            email=options["email"],
            password=password,
            organization=organization,
            is_staff=True,
        )
        account.user_permissions.set(
            Permission.objects.filter(content_type__app_label="sigab").exclude(
                codename__startswith="delete_"
            )
        )
        role = Role.objects.create(
            organization=organization, name="Administrador inicial", permissions=ADMIN_PERMISSIONS
        )
        Grant.objects.create(
            organization=organization,
            account=account,
            role=role,
            scope_type=Grant.Scope.ORGANIZATION,
            granted_by=account,
        )
        correlation_id = str(uuid.uuid4())
        for action, instance in [
            ("organization.create", organization),
            ("account.create", account),
            ("grant.create", role),
        ]:
            AuditEvent.objects.create(
                organization=organization,
                actor=account,
                action=action,
                object_type=instance._meta.label_lower,
                object_id=str(instance.pk),
                occurred_at=now,
                correlation_id=correlation_id,
                changes={},
            )
        self.stdout.write(self.style.SUCCESS(f"Organização criada: {organization.id}"))
