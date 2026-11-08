import uuid

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from sigab import services
from sigab.models import Account, EquipmentType, Item, Movement, Organization, Role
from sigab.services import CommandContext, Contingency

DEMO_PASSWORD = "Demo-sigab-2026"

# Entirely synthetic data. The second organization exists to show tenant isolation.
ORGANIZATIONS = [
    {
        "name": "Batalhão Demonstração Alfa",
        "prefix": "alfa",
        "units": [
            ("ALFA-1CIA", "1ª Companhia", [("ALFA-R1", "Reserva da 1ª Cia")]),
            ("ALFA-2CIA", "2ª Companhia", [("ALFA-R2", "Reserva da 2ª Cia")]),
        ],
        "types": [
            ("Pistola 9mm", "Pistola semiautomática de dotação."),
            ("Carabina 5.56", "Carabina de uso coletivo."),
            ("Colete balístico", "Colete de proteção nível III-A."),
            ("Rádio portátil", "Rádio transceptor portátil."),
        ],
        "people": [
            ("Ana Souza Lima", "Sd Ana", "Soldado", "1001"),
            ("Bruno Carvalho Melo", "Cb Bruno", "Cabo", "1002"),
            ("Carla Nunes Rocha", "Sgt Carla", "Sargento", "1003"),
            ("Diego Pires Araújo", "Sd Diego", "Soldado", "1004"),
            ("Elisa Ramos Teixeira", "Ten Elisa", "Tenente", "1005"),
            ("Fábio Gomes Castro", "Sd Fábio", "Soldado", "1006"),
        ],
        "items_per_type": 4,
    },
    {
        "name": "Batalhão Demonstração Bravo",
        "prefix": "bravo",
        "units": [("BRAVO-SEDE", "Sede", [("BRAVO-R1", "Reserva da Sede")])],
        "types": [("Pistola 9mm", "Pistola semiautomática de dotação.")],
        "people": [
            ("Gustavo Lopes Dias", "Sd Gustavo", "Soldado", "2001"),
            ("Helena Batista Prado", "Cb Helena", "Cabo", "2002"),
        ],
        "items_per_type": 3,
    },
]


def _key():
    return uuid.uuid4()


class Command(BaseCommand):
    help = "Popula o banco local com organizações e movimentações sintéticas para demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEMO_PASSWORD)

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Dados de demonstração só podem ser criados com DEBUG ligado.")
        names = [spec["name"] for spec in ORGANIZATIONS]
        if Organization.objects.filter(name__in=names).exists():
            raise CommandError("Os dados de demonstração já existem neste banco.")
        password = options["password"]
        with transaction.atomic():
            for spec in ORGANIZATIONS:
                self._seed(spec, password)
        self.stdout.write(self.style.SUCCESS(f"Dados de demonstração criados. Senha: {password}"))
        for spec in ORGANIZATIONS:
            prefix = spec["prefix"]
            self.stdout.write(
                f"  {spec['name']}: {prefix}.admin (gestor/acesso), "
                f"{prefix}.operador (operador de reserva)"
            )

    def _seed(self, spec, password):
        prefix = spec["prefix"]
        call_command(
            "bootstrap_sigab",
            organization=spec["name"],
            username=f"{prefix}.admin",
            email=f"{prefix}.admin@example.invalid",
            password=password,
            stdout=self.stdout,
        )
        admin = Account.objects.get(username=f"{prefix}.admin")
        organization = admin.organization
        admin_ctx = CommandContext(admin, organization, str(uuid.uuid4()))

        units, locations = [], {}
        for code, name, unit_locations in spec["units"]:
            unit = services.create_unit(admin_ctx, code=code, name=name)
            units.append(unit)
            locations[unit.id] = [
                services.create_storage_location(
                    admin_ctx, unit_id=unit.id, code=loc_code, name=loc_name
                )
                for loc_code, loc_name in unit_locations
            ]
        types = [
            services.create_equipment_type(
                admin_ctx,
                name=name,
                description=description,
                classification=EquipmentType.Classification.INDIVIDUAL,
            )
            for name, description in spec["types"]
        ]

        people = []
        for index, (name, functional_name, rank, registration) in enumerate(spec["people"]):
            person = services.create_person(admin_ctx, name=name, functional_name=functional_name)
            services.create_membership(
                admin_ctx,
                person_id=person.id,
                registration=registration,
                main_unit_id=units[index % len(units)].id,
                rank=rank,
            )
            people.append(person)

        operator = services.create_account(
            admin_ctx,
            person_id=people[0].id,
            username=f"{prefix}.operador",
            password=password,
            email=f"{prefix}.operador@example.invalid",
        )
        operator_role = Role.objects.get(organization=organization, name="Operador de reserva")
        for unit in units:
            services.create_grant(
                admin_ctx,
                account_id=operator.id,
                role_id=operator_role.id,
                scope_type="unit",
                unit_id=unit.id,
                reason="Operador da reserva (dados de demonstração).",
            )
        operator_ctx = CommandContext(operator, organization, str(uuid.uuid4()))

        items = []
        for type_index, equipment_type in enumerate(types):
            for number in range(1, spec["items_per_type"] + 1):
                unit = units[number % len(units)]
                items.append(
                    services.incorporate_item(
                        admin_ctx,
                        equipment_type_id=equipment_type.id,
                        unit_id=unit.id,
                        storage_location_id=locations[unit.id][0].id,
                        serial_number=f"{prefix.upper()}-{type_index + 1}{number:03d}",
                        asset_number=f"PAT-{prefix.upper()}-{type_index + 1}{number:03d}",
                        confirmed=True,
                    )
                )

        self._movements(operator_ctx, admin_ctx, items, people)

    def _movements(self, operator_ctx, admin_ctx, items, people):
        """Leave items in every state the flow supports, with history behind them."""

        def checkout(item, person, contingency=None):
            services.checkout_item(
                operator_ctx,
                item_id=item.id,
                recipient_id=person.id,
                idempotency_key=_key(),
                confirmed=True,
                contingency=contingency,
            )

        def give_back(item, condition=Item.Condition.FIT, reason=""):
            services.return_item(
                operator_ctx,
                item_id=item.id,
                condition=condition,
                reason=reason,
                idempotency_key=_key(),
                confirmed=True,
            )

        # Items currently in custody.
        for item, person in zip(items[0:3], people[1:], strict=False):
            checkout(item, person)
        if len(items) < 8:
            return

        # Checkout and fit return: available again, with history.
        checkout(items[3], people[2 % len(people)])
        give_back(items[3])
        # Unfit return: unavailable until released.
        checkout(items[4], people[3 % len(people)])
        give_back(items[4], Item.Condition.UNFIT, "Ferrolho com folga excessiva.")
        # Declared unfit in the reserve, then released after inspection.
        services.set_item_condition(
            operator_ctx,
            item_id=items[5].id,
            condition=Item.Condition.UNFIT,
            reason="Aguardando revisão do armeiro.",
            idempotency_key=_key(),
            confirmed=True,
        )
        services.set_item_condition(
            operator_ctx,
            item_id=items[5].id,
            condition=Item.Condition.FIT,
            reason="Conferência nº 12/2026 liberou o item.",
            idempotency_key=_key(),
            confirmed=True,
        )
        # Checkout registered by mistake and reversed by the manager.
        services.checkout_item(
            operator_ctx,
            item_id=items[6].id,
            recipient_id=people[4 % len(people)].id,
            idempotency_key=(wrong := _key()),
            confirmed=True,
        )
        services.reverse_movement(
            admin_ctx,
            movement_id=Movement.objects.get(idempotency_key=wrong).id,
            idempotency_key=_key(),
            confirmed=True,
            reason="Saída lançada para o item errado.",
        )
        # Checkout recorded on paper while the system was down.
        checkout(
            items[7],
            people[5 % len(people)],
            Contingency(occurred_at=timezone.now(), paper_reference="Livro 1, folha 3, linha 7"),
        )
