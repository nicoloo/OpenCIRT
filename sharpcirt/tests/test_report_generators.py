"""Unit tests for report_generators.py helpers."""
import pytest
from unittest.mock import MagicMock, patch
from sharpcirt.report_generators import (
    ALL_SECTIONS,
    DEFAULT_SECTIONS,
    parse_sections,
    parse_tlp,
    generate_markdown,
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
    incident.created_by = MagicMock(username='lead_admin')
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
