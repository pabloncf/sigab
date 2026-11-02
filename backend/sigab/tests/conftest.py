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
from sigab.permissions import MOVE_ITEM, SET_ITEM_CONDITION, VIEW_ITEM


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
        permissions=[MOVE_ITEM, SET_ITEM_CONDITION, VIEW_ITEM],
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
