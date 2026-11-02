import json
import os
import statistics
import time
import uuid

import pytest
from django.test import Client

from sigab.models import (
    Account,
    EquipmentType,
    Grant,
    Item,
    Membership,
    Movement,
    Person,
    Role,
    StorageLocation,
    Unit,
)
from sigab.permissions import ITEM_VIEW, MOVEMENT_CHECKOUT, PERSON_VIEW_MINIMAL

PASSWORD = "Senha-forte-123"


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _checkout(client, item, person):
    return _post(
        client,
        f"/api/v1/items/{item.id}/checkout/",
        {"recipient_id": str(person.id), "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    )


@pytest.fixture
def two_units(api_world):
    organization = api_world["organization"]
    unit_b = Unit.objects.create(organization=organization, name="Unidade B", code="U-B")
    location_b = StorageLocation.objects.create(
        organization=organization, unit=unit_b, name="Reserva B", code="R-B"
    )
    item_b = Item.objects.create(
        organization=organization,
        equipment_type=api_world["item"].equipment_type,
        unit=unit_b,
        storage_location=location_b,
        serial_number="B-001",
    )
    reader = Account.objects.create_user(
        username="leitor-a", password=PASSWORD, organization=organization
    )
    Grant.objects.create(
        organization=organization,
        account=reader,
        role=Role.objects.create(organization=organization, name="Leitor", permissions=[ITEM_VIEW]),
        scope_type="unit",
        unit=api_world["unit"],
    )
    client = Client()
    client.force_login(api_world["account"])
    reader_client = Client()
    reader_client.force_login(reader)
    return {**api_world, "item_b": item_b, "client": client, "reader": reader_client}


# SIGAB-036: activity feed


@pytest.mark.django_db
def test_feed_is_paginated_and_filterable(two_units):
    c, person = two_units["client"], two_units["person"]
    _checkout(c, two_units["item"], person)
    _post(
        c,
        f"/api/v1/items/{two_units['item'].id}/return/",
        {"condition": "fit", "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    )
    _checkout(c, two_units["item_b"], person)
    page = c.get("/api/v1/activity/?limit=2").json()
    assert page["meta"]["count"] == 3 and len(page["data"]) == 2
    assert page["data"][0]["type"] == "item.checked_out"
    assert page["data"][0]["item"]["identifier"] == "B-001"
    by_item = c.get(f"/api/v1/activity/?item={two_units['item'].id}").json()["data"]
    assert {e["item"]["id"] for e in by_item} == {str(two_units["item"].id)}
    by_action = c.get("/api/v1/activity/?action=item.returned").json()["data"]
    assert [e["type"] for e in by_action] == ["item.returned"]
    by_person = c.get(f"/api/v1/activity/?person={person.id}").json()["meta"]["count"]
    assert by_person == 3
    assert c.get("/api/v1/activity/?from=2000-01-01&to=2000-01-02").json()["data"] == []
    assert c.get("/api/v1/activity/?from=ontem").status_code == 400


@pytest.mark.django_db
def test_feed_respects_unit_scope_and_is_not_the_audit(two_units, client):
    _checkout(two_units["client"], two_units["item_b"], two_units["person"])
    rows = two_units["reader"].get("/api/v1/activity/").json()["data"]
    assert rows == []
    client.force_login(
        Account.objects.create_user(
            username="sem-papel", password=PASSWORD, organization=two_units["organization"]
        )
    )
    assert client.get("/api/v1/activity/").status_code == 403
    types = {e["type"] for e in two_units["client"].get("/api/v1/activity/").json()["data"]}
    assert not {t for t in types if t.startswith(("auth.", "account.", "grant."))}


# SIGAB-037: current possession of a person


@pytest.mark.django_db
def test_possession_matches_confirmed_movements(two_units):
    c, person = two_units["client"], two_units["person"]
    _checkout(c, two_units["item"], person)
    _checkout(c, two_units["item_b"], person)
    _post(
        c,
        f"/api/v1/items/{two_units['item_b'].id}/return/",
        {"condition": "fit", "idempotency_key": str(uuid.uuid4()), "confirmed": True},
    )
    listed = {row["id"] for row in c.get(f"/api/v1/items/?holder={person.id}").json()["data"]}
    # Derivation from confirmed facts only: checkouts in force without a return in force.
    derived = {
        str(m.item_id)
        for m in Movement.objects.filter(
            movement_type="checkout", recipient=person, reversal__isnull=True
        )
        if not m.responses.filter(reversal__isnull=True).exists()
    }
    assert listed == derived == {str(two_units["item"].id)}
    scoped = two_units["reader"].get(f"/api/v1/items/?holder={person.id}").json()["data"]
    assert {row["id"] for row in scoped} == {str(two_units["item"].id)}


# SIGAB-038: search


@pytest.mark.django_db
def test_search_finds_items_and_people_within_scope(two_units):
    organization = two_units["organization"]
    Person.objects.filter(pk=two_units["person"].pk).update(cpf="52998224725", phone="85999990000")
    operator_role = Role.objects.create(
        organization=organization,
        name="Operador busca",
        permissions=[ITEM_VIEW, PERSON_VIEW_MINIMAL, MOVEMENT_CHECKOUT],
    )
    Grant.objects.create(
        organization=organization,
        account=two_units["account"],
        role=operator_role,
        scope_type="organization",
    )
    c = two_units["client"]
    by_serial = c.get("/api/v1/search/?q=B-00").json()
    assert [i["identifier"] for i in by_serial["data"]["items"]] == ["B-001"]
    by_unit = c.get("/api/v1/search/?q=U-B").json()["data"]["items"]
    assert [i["identifier"] for i in by_unit] == ["B-001"]
    by_registration = c.get("/api/v1/search/?q=API-1")
    people = by_registration.json()["data"]["people"]
    assert [p["id"] for p in people] == [str(two_units["person"].id)]
    assert set(people[0]) == {"id", "name", "is_active", "registrations"}
    assert "52998224725" not in by_registration.content.decode()
    filtered = c.get(
        f"/api/v1/search/?q=Equipamento&availability=available&unit={two_units['unit'].id}"
    ).json()["data"]["items"]
    assert [i["identifier"] for i in filtered] == ["API-001"]
    assert c.get("/api/v1/search/?q=a").status_code == 400
    assert c.get("/api/v1/search/?q=Equip&availability=sumido").status_code == 400


@pytest.mark.django_db
def test_search_hides_other_units_and_people_without_permission(two_units):
    reader = two_units["reader"].get("/api/v1/search/?q=001").json()["data"]
    assert [i["identifier"] for i in reader["items"]] == ["API-001"]
    assert reader["people"] == []


@pytest.mark.django_db
@pytest.mark.skipif(not os.getenv("SIGAB_PERF"), reason="medição de volume: SIGAB_PERF=1")
def test_search_response_time_with_test_volume(api_world):
    """Volume documented in docs/busca.md: 10 units, 5,000 items, 2,000 people."""
    organization = api_world["organization"]
    equipment_type = EquipmentType.objects.create(
        organization=organization, name="Pistola volume", classification="individual"
    )
    units, locations = [], []
    for index in range(10):
        unit = Unit.objects.create(organization=organization, name=f"Vol {index}", code=f"V{index}")
        units.append(unit)
        locations.append(
            StorageLocation.objects.create(
                organization=organization, unit=unit, name="R", code=f"RV{index}"
            )
        )
    Item.objects.bulk_create(
        Item(
            organization=organization,
            equipment_type=equipment_type,
            unit=units[index % 10],
            storage_location=locations[index % 10],
            serial_number=f"VOL-{index:05d}",
            asset_number=f"PAT-{index:05d}",
        )
        for index in range(5000)
    )
    people = Person.objects.bulk_create(
        Person(organization=organization, name=f"Pessoa Volume {index:04d}")
        for index in range(2000)
    )
    Membership.objects.bulk_create(
        Membership(
            organization=organization,
            person=person,
            registration=f"VM-{index:04d}",
            main_unit=units[index % 10],
        )
        for index, person in enumerate(people)
    )
    Grant.objects.create(
        organization=organization,
        account=api_world["account"],
        role=Role.objects.create(
            organization=organization, name="Busca", permissions=[ITEM_VIEW, PERSON_VIEW_MINIMAL]
        ),
        scope_type="organization",
    )
    client = Client()
    client.force_login(api_world["account"])
    timings = []
    for query in ["VOL-0", "PAT-04", "Pessoa Volume 1", "VM-19", "V3", "Pistola"] * 5:
        started = time.perf_counter()
        response = client.get(f"/api/v1/search/?q={query}&limit=50")
        timings.append((time.perf_counter() - started) * 1000)
        assert response.status_code == 200
    timings.sort()
    p95 = timings[int(len(timings) * 0.95) - 1]
    median = statistics.median(timings)
    print(f"\nbusca: mediana={median:.1f} ms p95={p95:.1f} ms n={len(timings)}")
    assert p95 < 1000
