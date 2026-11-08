import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from sigab.models import Item, Movement, Organization


@pytest.mark.django_db
def test_seed_demo_creates_items_in_every_state(settings):
    settings.DEBUG = True
    call_command("seed_demo")

    alfa = Organization.objects.get(name="Batalhão Demonstração Alfa")
    items = Item.objects.filter(organization=alfa)
    assert items.filter(availability=Item.Availability.IN_CUSTODY).count() == 4
    assert items.filter(availability=Item.Availability.UNAVAILABLE).count() == 1
    assert Movement.objects.filter(organization=alfa, movement_type="reversal").count() == 1
    assert Movement.objects.filter(organization=alfa, origin="contingency").count() == 1
    bravo = Organization.objects.get(name="Batalhão Demonstração Bravo")
    assert not Movement.objects.filter(organization=bravo, item__organization=alfa).exists()


@pytest.mark.django_db
def test_seed_demo_refuses_without_debug_or_twice(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo")
    settings.DEBUG = True
    call_command("seed_demo")
    with pytest.raises(CommandError):
        call_command("seed_demo")
