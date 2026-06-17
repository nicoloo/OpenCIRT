"""Regression guard: demo fixture must load without error and produce expected data."""
import pytest
from django.core.management import call_command
from opencirt.models import Action, GenericIoc, Impact, Incident, Note, Task


FIXTURE = 'opencirt/fixtures/incidents_demo.json'


@pytest.fixture
def demo_data(db):
    call_command('loaddata', FIXTURE, verbosity=0)


def test_fixture_loads_without_error(demo_data):
    pass


def test_fixture_incident_count(demo_data):
    assert Incident.objects.count() == 3


def test_fixture_incident_categories_assigned(demo_data):
    assert Incident.objects.get(pk=1).categories.count() == 2
    assert Incident.objects.get(pk=2).categories.count() == 2
    assert Incident.objects.get(pk=3).categories.count() == 2


def test_fixture_required_datetime_fields_not_null(demo_data):
    for inc in Incident.objects.all():
        assert inc.starting_time is not None, f"Incident {inc.pk} has null starting_time"
        assert inc.ending_time is not None, f"Incident {inc.pk} has null ending_time"


def test_fixture_action_count(demo_data):
    assert Action.objects.count() == 15


def test_fixture_ioc_count(demo_data):
    assert GenericIoc.objects.count() == 10


def test_fixture_task_count(demo_data):
    assert Task.objects.count() == 7


def test_fixture_impact_count(demo_data):
    assert Impact.objects.count() == 6


def test_fixture_note_count(demo_data):
    assert Note.objects.count() == 6


def test_fixture_impact_status_valid(demo_data):
    valid = {'CONTINUOUS', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'}
    for impact in Impact.objects.all():
        assert impact.status in valid, f"Impact {impact.pk} has invalid status '{impact.status}'"


def test_fixture_task_status_valid(demo_data):
    valid = {'OPEN', 'IN_PROGRESS', 'DONE'}
    for task in Task.objects.all():
        assert task.status in valid, f"Task {task.pk} has invalid status '{task.status}'"
