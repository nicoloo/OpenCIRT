"""Unit tests for report_generators.py helpers."""
import pytest
from unittest.mock import MagicMock, patch
from opencirt.report_generators import (
    ALL_SECTIONS,
    DEFAULT_SECTIONS,
    parse_sections,
    parse_tlp,
    generate_markdown,
    generate_deep_json,
)


# ── parse_sections ──────────────────────────────────────────────

def test_parse_sections_empty_returns_defaults():
    result = parse_sections({'sections': ''})
    assert result == DEFAULT_SECTIONS


def test_parse_sections_missing_key_returns_defaults():
    result = parse_sections({})
    assert result == DEFAULT_SECTIONS


def test_parse_sections_valid_subset():
    result = parse_sections({'sections': 'executive_summary,iocs'})
    assert result == frozenset({'executive_summary', 'iocs'})


def test_parse_sections_ignores_unknown_keys():
    result = parse_sections({'sections': 'executive_summary,UNKNOWN_KEY,iocs'})
    assert result == frozenset({'executive_summary', 'iocs'})


def test_parse_sections_all_invalid_returns_defaults():
    result = parse_sections({'sections': 'INVALID,ALSO_BAD'})
    assert result == DEFAULT_SECTIONS


# ── parse_tlp ───────────────────────────────────────────────────

def test_parse_tlp_valid_values():
    assert parse_tlp({'tlp': 'WHITE'}) == 'WHITE'
    assert parse_tlp({'tlp': 'GREEN'}) == 'GREEN'
    assert parse_tlp({'tlp': 'AMBER'}) == 'AMBER'
    assert parse_tlp({'tlp': 'RED'}) == 'RED'


def test_parse_tlp_lowercase_is_uppercased():
    assert parse_tlp({'tlp': 'amber'}) == 'AMBER'


def test_parse_tlp_invalid_returns_amber():
    assert parse_tlp({'tlp': 'PURPLE'}) == 'AMBER'


def test_parse_tlp_missing_returns_amber():
    assert parse_tlp({}) == 'AMBER'


# ── generate_markdown ───────────────────────────────────────────

def _make_incident():
    """Build a minimal mock incident for testing."""
    ioc = MagicMock()
    ioc.get_type_display.return_value = 'IP Address'
    ioc.value = '192.0.2.1'
    ioc.get_status_display.return_value = 'Compromised'
    ioc.description = 'Bad actor C2'

    incident = MagicMock()
    incident.name = 'Test Incident'
    incident.executive_summary = 'Brief summary.'
    incident.lessons_learned = 'Lesson 1.'
    incident.technical_details = 'Detail 1.'
    incident.get_status_display.return_value = 'Open'
    incident.severity = 'HIGH'
    incident.starting_time = '2026-01-01 08:00'
    incident.ending_time = '2026-01-01 10:00'
    incident.duration = '2:00:00'
    incident.time_to_detect = '0:15:00'
    incident.time_to_respond = '0:30:00'
    incident.created_by = MagicMock(username='admin')
    incident.is_public = False
    incident.genericiocs.all.return_value = [ioc]
    incident.genericiocs.exists.return_value = True
    incident.actions.all.return_value = []
    incident.actions.exists.return_value = False
    incident.tasks.all.return_value = []
    incident.tasks.exists.return_value = False
    incident.notes.all.return_value = []
    incident.notes.exists.return_value = False
    incident.incident_roles.all.return_value = []
    return incident


def test_generate_markdown_tlp_header():
    md = generate_markdown(_make_incident(), frozenset({'executive_summary'}), 'AMBER', 'test_user')
    assert '> **TLP:AMBER**' in md


def test_generate_markdown_includes_incident_name():
    md = generate_markdown(_make_incident(), frozenset({'executive_summary'}), 'AMBER', 'test_user')
    assert 'Test Incident' in md


def test_generate_markdown_executive_summary_present():
    md = generate_markdown(_make_incident(), frozenset({'executive_summary'}), 'GREEN', 'u')
    assert '## Executive Summary' in md
    assert 'Brief summary.' in md


def test_generate_markdown_executive_summary_absent():
    md = generate_markdown(_make_incident(), frozenset({'iocs'}), 'AMBER', 'u')
    assert '## Executive Summary' not in md


def test_generate_markdown_iocs_table():
    md = generate_markdown(_make_incident(), frozenset({'iocs'}), 'AMBER', 'u')
    assert '## IoC / Evidence' in md
    assert '192.0.2.1' in md
    assert 'Compromised' in md


def test_generate_markdown_pipe_in_value_is_escaped():
    ioc = MagicMock()
    ioc.get_type_display.return_value = 'Other'
    ioc.value = 'a|b'
    ioc.get_status_display.return_value = 'Safe'
    ioc.description = None

    incident = _make_incident()
    incident.genericiocs.all.return_value = [ioc]
    incident.genericiocs.exists.return_value = True

    md = generate_markdown(incident, frozenset({'iocs'}), 'AMBER', 'u')
    assert 'a\\|b' in md


# ── generate_deep_json ──────────────────────────────────────────

def _make_deep_incident():
    """Mock incident for generate_deep_json tests."""
    # Mock UserRole
    ur = MagicMock()
    ur.user.username = 'responder1'
    ur.user.displayname = 'Responder One'
    ur.user.email = 'r1@example.com'
    ur.role = 'RESPONDER'
    ur.display_role = 'IR Lead'

    # Mock IoC
    ioc = MagicMock()
    ioc.id = 1
    ioc.type = 'IPADRESS'
    ioc.get_type_display.return_value = 'IP Address'
    ioc.value = '10.0.0.1'
    ioc.status = 'COMPROMISED'
    ioc.description = 'Attacker C2'
    ioc.created_at = None
    ioc.created_by = MagicMock(username='analyst')
    ioc.actions.values_list.return_value = [42]

    # Mock Action
    action = MagicMock()
    action.id = 5
    action.type = 'MALICIOUS'
    action.get_type_display.return_value = 'Malicious'
    action.title = 'Lateral move'
    action.description = 'Attacker moved laterally'
    action.observed_at = None
    action.starting_time = None
    action.ending_time = None
    action.created_at = None
    action.created_by = MagicMock(username='lead')
    action.iocs.values_list.return_value = [1]
    action.tags.all.return_value = []

    # Mock Task
    task = MagicMock()
    task.id = 10
    task.title = 'Patch server'
    task.description = 'Apply patches'
    task.status = 'OPEN'
    task.priority = 'HIGH'
    task.assignee = MagicMock(username='engineer')
    task.external_reference = 'JIRA-123'
    task.created_at = None

    # Mock Impact
    impact = MagicMock()
    impact.id = 20
    impact.title = 'Data exposure'
    impact.description = 'PII data exposed'
    impact.severity = 'HIGH'
    impact.status = 'IN_PROGRESS'
    impact.type = 'DATA_LOSS'

    # Mock Note
    note = MagicMock()
    note.id = 7
    note.name = 'Initial findings'
    note.text = 'Found malicious traffic'
    note.created_at = None
    note.created_by = MagicMock(username='analyst')

    incident = MagicMock()
    incident.id = 99
    incident.name = 'Test Incident'
    incident.description = 'A test'
    incident.status = 'OPEN'
    incident.severity = 'HIGH'
    incident.executive_summary = 'Summary'
    incident.lessons_learned = 'Lessons'
    incident.technical_details = 'Details'
    incident.starting_time = None
    incident.ending_time = None
    incident.duration = None
    incident.time_to_detect = None
    incident.time_to_respond = None
    incident.created_at = None
    incident.is_public = False
    incident.created_by = MagicMock(username='admin')

    incident.incident_roles.all.return_value.select_related.return_value = [ur]
    incident.genericiocs.all.return_value.prefetch_related.return_value.select_related.return_value = [ioc]
    incident.actions.all.return_value.order_by.return_value.prefetch_related.return_value.select_related.return_value = [action]
    incident.notes.all.return_value.select_related.return_value = [note]
    incident.tasks.all.return_value.select_related.return_value = [task]
    incident.impacts.all.return_value = [impact]

    return incident


def test_generate_deep_json_top_level_keys():
    result = generate_deep_json(_make_deep_incident(), 'test_user')
    assert 'exported_at' in result
    assert 'exported_by' in result
    assert 'tlp' in result
    assert 'incident' in result
    assert 'responders' in result
    assert 'iocs' in result
    assert 'timeline' in result
    assert 'notes' in result
    assert 'tasks' in result
    assert 'impacts' in result


def test_generate_deep_json_exported_by():
    result = generate_deep_json(_make_deep_incident(), 'my_user')
    assert result['exported_by'] == 'my_user'


def test_generate_deep_json_tlp_default_amber():
    result = generate_deep_json(_make_deep_incident(), 'u')
    assert result['tlp'] == 'AMBER'


def test_generate_deep_json_tlp_custom():
    result = generate_deep_json(_make_deep_incident(), 'u', tlp='RED')
    assert result['tlp'] == 'RED'


def test_generate_deep_json_incident_fields():
    result = generate_deep_json(_make_deep_incident(), 'u')
    inc = result['incident']
    assert inc['id'] == 99
    assert inc['name'] == 'Test Incident'
    assert inc['severity'] == 'HIGH'
    assert inc['is_public'] is False


def test_generate_deep_json_responders():
    result = generate_deep_json(_make_deep_incident(), 'u')
    assert len(result['responders']) == 1
    assert result['responders'][0]['username'] == 'responder1'
    assert result['responders'][0]['role'] == 'RESPONDER'


def test_generate_deep_json_iocs():
    result = generate_deep_json(_make_deep_incident(), 'u')
    assert len(result['iocs']) == 1
    assert result['iocs'][0]['value'] == '10.0.0.1'
    assert result['iocs'][0]['type'] == 'IPADRESS'
    assert 42 in result['iocs'][0]['linked_actions']


def test_generate_deep_json_tasks():
    result = generate_deep_json(_make_deep_incident(), 'u')
    assert len(result['tasks']) == 1
    assert result['tasks'][0]['title'] == 'Patch server'
    assert result['tasks'][0]['assignee'] == 'engineer'
