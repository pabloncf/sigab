import pytest

from sigab.models import (
    Account,
    EquipmentType,
    Grant,
    Item,
    Membership,
    Organization,
    Person,
    Role,
    StorageLocation,
    Unit,
)
from sigab.permissions import MOVEMENT_CHECKOUT, MOVEMENT_RETURN, SET_ITEM_CONDITION, VIEW_ITEM
from sigab.services import CommandContext, record_incorporation


@pytest.fixture(autouse=True)
def identity_check_off_by_default(request, settings):
    """Movement-rule tests run without the ADR 0008 identity requirement.

    Tests of the requirement itself use the ``identity_check`` marker to turn it on.
    """
    settings.SIGAB_REQUIRE_IDENTITY_CHECK = bool(request.node.get_closest_marker("identity_check"))


@pytest.fixture
def api_world(db):
    organization = Organization.objects.create(name="Organização API")
    unit = Unit.objects.create(organization=organization, name="Unidade API", code="U-API")
    location = StorageLocation.objects.create(
        organization=organization, unit=unit, name="Reserva", code="R-API"
    )
    person = Person.objects.create(organization=organization, name="Pessoa API")
    Membership.objects.create(
        organization=organization,
        person=person,
        registration="API-1",
        main_unit=unit,
    )
    account = Account.objects.create_user(
        username="operador-api", password="Senha-forte-123", organization=organization
    )
    role = Role.objects.create(
        organization=organization,
        name="Operador API",
        permissions=[MOVEMENT_CHECKOUT, MOVEMENT_RETURN, SET_ITEM_CONDITION, VIEW_ITEM],
    )
    Grant.objects.create(
        organization=organization,
        account=account,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
        granted_by=account,
    )
    equipment_type = EquipmentType.objects.create(
        organization=organization,
        name="Equipamento API",
        classification=EquipmentType.Classification.INDIVIDUAL,
    )
    item = Item.objects.create(
        organization=organization,
        equipment_type=equipment_type,
        unit=unit,
        storage_location=location,
        serial_number="API-001",
    )
    return {
        "organization": organization,
        "unit": unit,
        "person": person,
        "account": account,
        "item": item,
    }


@pytest.fixture
def world(db):
    org = Organization.objects.create(name="Organização A")
    unit = Unit.objects.create(organization=org, name="Unidade A", code="UA")
    location = StorageLocation.objects.create(
        organization=org, unit=unit, name="Reserva", code="R1"
    )
    person = Person.objects.create(organization=org, name="Pessoa Sintética")
    Membership.objects.create(organization=org, person=person, registration="MAT-1", main_unit=unit)
    account = Account.objects.create_user(
        username="operador", password="Senha-forte-123", organization=org
    )
    role = Role.objects.create(
        organization=org,
        name="Operador",
        permissions=[MOVEMENT_CHECKOUT, MOVEMENT_RETURN, SET_ITEM_CONDITION, VIEW_ITEM],
    )
    Grant.objects.create(
        organization=org,
        account=account,
        role=role,
        scope_type=Grant.Scope.ORGANIZATION,
        granted_by=account,
    )
    equipment_type = EquipmentType.objects.create(
        organization=org,
        name="Equipamento sintético",
        classification=EquipmentType.Classification.INDIVIDUAL,
    )
    item = Item.objects.create(
        organization=org,
        equipment_type=equipment_type,
        unit=unit,
        storage_location=location,
        serial_number="SYN-001",
    )
    ctx = CommandContext(account, org, "test-correlation")
    record_incorporation(ctx, item)
    return {
        "org": org,
        "unit": unit,
        "location": location,
        "person": person,
        "account": account,
        "type": equipment_type,
        "item": item,
        "ctx": ctx,
    }
