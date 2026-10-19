import uuid
from getpass import getpass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from sigab.models import Account, AuditEvent, Organization, Person


class Command(BaseCommand):
    help = "Cria uma conta separada para uma pessoa já cadastrada."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", required=True)
        parser.add_argument("--person-id", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", help="Se omitida, será solicitada sem eco no terminal.")

    @transaction.atomic
    def handle(self, *args, **options):
        organization = Organization.objects.filter(pk=options["organization_id"]).first()
        person = Person.objects.filter(
            pk=options["person_id"], organization=organization, is_active=True
        ).first()
        if not organization or not person:
            raise CommandError("Organização ou pessoa ativa não encontrada no mesmo tenant.")
        if Account.objects.filter(username=options["username"]).exists():
            raise CommandError("O identificador de login já existe.")
        password = options["password"] or getpass("Senha inicial: ")
        if not password:
            raise CommandError("A senha inicial é obrigatória.")
        account = Account.objects.create_user(
            username=options["username"],
            email=options["email"],
            password=password,
            organization=organization,
            person=person,
        )
        AuditEvent.objects.create(
            organization=organization,
            actor=None,
            action="account.create.controlled_command",
            object_type=account._meta.label_lower,
            object_id=str(account.pk),
            occurred_at=timezone.now(),
            correlation_id=str(uuid.uuid4()),
            changes={"person_id": str(person.id)},
        )
        self.stdout.write(self.style.SUCCESS(f"Conta criada: {account.id}"))
