import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from sigab.models import Account, AuditEvent, Organization


class Command(BaseCommand):
    help = (
        "Suspende ou reativa uma organização pelo plano de controle. Organização suspensa "
        "não autentica nem recebe permissões; dados e histórico são preservados."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", required=True)
        parser.add_argument("--status", required=True, choices=Organization.Status.values)
        parser.add_argument("--reason", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        reason = options["reason"].strip()
        if not reason:
            raise CommandError("O motivo é obrigatório.")
        organization = (
            Organization.objects.select_for_update().filter(pk=options["organization_id"]).first()
        )
        if not organization:
            raise CommandError("Organização não encontrada.")
        previous, status = organization.status, options["status"]
        if previous == status:
            raise CommandError("A organização já está nessa situação.")
        organization.status = status
        organization.save(update_fields=["status", "updated_at"])
        # Sessions of a suspended organization end because authentication re-checks the status.
        if status != Organization.Status.ACTIVE:
            for account in Account.objects.filter(organization=organization):
                account.session_version += 1
                account.save(update_fields=["session_version"])
        AuditEvent.objects.create(
            organization=organization,
            actor=None,
            action="organization.status_change",
            object_type=organization._meta.label_lower,
            object_id=str(organization.pk),
            occurred_at=timezone.now(),
            correlation_id=str(uuid.uuid4()),
            changes={"status": {"from": previous, "to": status}},
            reason=reason,
        )
        self.stdout.write(self.style.SUCCESS(f"Situação da organização: {status}"))
