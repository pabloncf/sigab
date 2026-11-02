from django.core.management.base import BaseCommand, CommandError

from sigab.models import AuditEvent, Organization, audit_record_hash


def verify_chain(organization):
    """Return None when the chain is intact, else a description of the first break."""
    expected_sequence, previous = 1, ""
    for event in AuditEvent.objects.filter(organization=organization).order_by("sequence"):
        if event.sequence != expected_sequence:
            return f"sequência {expected_sequence} ausente (encontrada {event.sequence})"
        if event.previous_hash != previous:
            return f"sequência {event.sequence}: elo com o registro anterior não confere"
        if audit_record_hash(event) != event.record_hash:
            return f"sequência {event.sequence}: conteúdo alterado"
        expected_sequence, previous = expected_sequence + 1, event.record_hash
    return None


class Command(BaseCommand):
    help = (
        "Verifica a cadeia de hashes da auditoria de uma organização (ou de todas) e aponta "
        "o primeiro registro alterado, removido ou fora de ordem."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization-id")

    def handle(self, *args, **options):
        organizations = Organization.objects.all()
        if options["organization_id"]:
            organizations = organizations.filter(pk=options["organization_id"])
            if not organizations.exists():
                raise CommandError("Organização não encontrada.")
        broken = []
        for organization in organizations.order_by("name"):
            problem = verify_chain(organization)
            if problem:
                broken.append(f"{organization.id}: {problem}")
        if broken:
            raise CommandError("Cadeia de auditoria violada:\n" + "\n".join(broken))
        self.stdout.write(self.style.SUCCESS("Cadeia de auditoria íntegra."))
