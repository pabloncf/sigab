import json

import pytest
from django.core.exceptions import ValidationError
from django.test import Client

from sigab.models import (
    Account,
    AuditEvent,
    EquipmentType,
    Grant,
    Item,
    Role,
    StorageLocation,
    Unit,
)
from sigab.permissions import CATALOG_MANAGE, ITEM_CREATE, ITEM_VIEW

PASSWORD = "Senha-forte-123"


def _json(client, method, url, payload=None):
    return getattr(client, method)(
        url, data=json.dumps(payload or {}), content_type="application/json"
    )


@pytest.fixture
def catalog(api_world):
    organization = api_world["organization"]
    manager = Account.objects.create_user(
        username="gestor-acervo", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(
        organization=organization, name="Gestor", permissions=[CATALOG_MANAGE, ITEM_VIEW]
    )
    Grant.objects.create(
        organization=organization, account=manager, role=role, scope_type="organization"
    )
    client = Client()
    client.force_login(manager)
    return {**api_world, "manager": manager, "client": client}


# SIGAB-024: units and storage locations


@pytest.mark.django_db
def test_unit_lifecycle(catalog):
    client = catalog["client"]
    created = _json(client, "post", "/api/v1/units/", {"code": "U-NOVA", "name": "Unidade nova"})
    assert created.status_code == 201
    unit_id = created.json()["data"]["id"]
    duplicate = _json(client, "post", "/api/v1/units/", {"code": "U-NOVA", "name": "Outra"})
    assert duplicate.status_code == 400

    renamed = _json(client, "patch", f"/api/v1/units/{unit_id}/", {"name": "Unidade renomeada"})
    assert renamed.json()["data"]["name"] == "Unidade renomeada"

    location = _json(
        client, "post", f"/api/v1/units/{unit_id}/locations/", {"code": "R-NOVA", "name": "Reserva"}
    )
    assert location.status_code == 201
    assert [loc["code"] for loc in location.json()["data"]["locations"]] == ["R-NOVA"]

    deactivated = _json(
        client,
        "post",
        f"/api/v1/units/{unit_id}/status/",
        {"is_active": False, "confirmed": True, "reason": "Unidade extinta"},
    )
    assert deactivated.json()["data"]["is_active"] is False
    assert Unit.objects.filter(pk=unit_id).exists()
    blocked = _json(
        client, "post", f"/api/v1/units/{unit_id}/locations/", {"code": "R-2", "name": "R"}
    )
    assert blocked.status_code == 400
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {"unit.create", "unit.update", "storagelocation.create", "unit.deactivate"} <= actions


@pytest.mark.django_db
def test_deactivating_unit_keeps_its_items(catalog):
    unit = catalog["unit"]
    response = _json(
        catalog["client"],
        "post",
        f"/api/v1/units/{unit.id}/status/",
        {"is_active": False, "confirmed": True},
    )
    assert response.status_code == 200
    assert Item.objects.filter(unit=unit).count() == 1


@pytest.mark.django_db
def test_location_deactivation_requires_confirmation(catalog):
    location = catalog["item"].storage_location
    url = f"/api/v1/locations/{location.id}/status/"
    assert _json(catalog["client"], "post", url, {"is_active": False}).status_code == 400
    assert (
        _json(catalog["client"], "post", url, {"is_active": False, "confirmed": True}).status_code
        == 200
    )
    assert StorageLocation.objects.get(pk=location.pk).is_active is False


@pytest.mark.django_db
def test_structure_requires_catalog_permission(client, api_world):
    client.force_login(api_world["account"])
    assert _json(client, "post", "/api/v1/units/", {"code": "X", "name": "X"}).status_code == 403
    assert client.get("/api/v1/units/").status_code == 403
    assert (
        _json(
            client,
            "post",
            "/api/v1/equipment-types/",
            {"name": "X", "classification": "individual"},
        ).status_code
        == 403
    )


# SIGAB-026: equipment types


@pytest.mark.django_db
def test_equipment_type_lifecycle(catalog):
    client = catalog["client"]
    created = _json(
        client,
        "post",
        "/api/v1/equipment-types/",
        {"name": "Pistola sintética", "classification": "individual"},
    )
    assert created.status_code == 201
    type_id = created.json()["data"]["id"]
    invalid = _json(
        client, "post", "/api/v1/equipment-types/", {"name": "X", "classification": "outro"}
    )
    assert invalid.status_code == 400
    edited = _json(
        client, "patch", f"/api/v1/equipment-types/{type_id}/", {"description": "Calibre fictício"}
    )
    assert edited.json()["data"]["description"] == "Calibre fictício"
    reclassified = _json(
        client,
        "patch",
        f"/api/v1/equipment-types/{type_id}/",
        {"classification": "quantitative"},
    )
    assert reclassified.status_code == 400
    assert EquipmentType.objects.get(pk=type_id).classification == "individual"


@pytest.mark.django_db
def test_classification_never_changes_even_unused(catalog):
    equipment_type = EquipmentType.objects.create(
        organization=catalog["organization"], name="Sem uso", classification="individual"
    )
    equipment_type.classification = "quantitative"
    with pytest.raises(ValidationError):
        equipment_type.save()


@pytest.mark.django_db
def test_type_deactivation_keeps_history_and_blocks_new_items(catalog):
    equipment_type = catalog["item"].equipment_type
    events_before = catalog["item"].events.count()
    response = _json(
        catalog["client"],
        "post",
        f"/api/v1/equipment-types/{equipment_type.id}/status/",
        {"is_active": False, "confirmed": True, "reason": "Fora de uso"},
    )
    assert response.status_code == 200
    assert catalog["item"].events.count() == events_before
    assert Item.objects.filter(equipment_type=equipment_type).count() == 1

    organization = catalog["organization"]
    creator = Account.objects.create_user(
        username="criador", password=PASSWORD, organization=organization
    )
    role = Role.objects.create(organization=organization, name="Cria", permissions=[ITEM_CREATE])
    Grant.objects.create(
        organization=organization, account=creator, role=role, scope_type="organization"
    )
    client = Client()
    client.force_login(creator)
    created = _json(
        client,
        "post",
        "/api/v1/items/",
        {
            "equipment_type_id": str(equipment_type.id),
            "unit_id": str(catalog["unit"].id),
            "storage_location_id": str(catalog["item"].storage_location_id),
            "serial_number": "NOVO-1",
            "confirmed": True,
        },
    )
    assert created.status_code == 400
    assert created.json()["details"] == {"equipment_type_id": ["Tipo inválido."]}
