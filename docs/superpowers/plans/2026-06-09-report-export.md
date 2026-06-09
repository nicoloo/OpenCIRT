# Report & Export System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dead report page with a professional two-panel report hub — section picker + live preview — and implement six export formats (PDF, Word, Markdown, JSON, CSV, HTML).

**Architecture:** A shared `report_generators.py` module holds constants and generator functions; views stay thin (parse request → call generator → return response). A single `reports/report_template.html` with inline CSS powers the browser preview, PDF, and HTML archive; Word and Markdown are generated programmatically from the same incident data.

**Tech stack:** Django 4.0.3 · xhtml2pdf (already installed) · python-docx (new) · Python stdlib csv/json · Chart.js (not needed here) · vanilla JS fetch + debounce for live preview.

**Spec:** `docs/superpowers/specs/2026-06-09-report-export-design.md`

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `sharpcirt/report_generators.py` | **Create** | Constants, `parse_sections`, `parse_tlp`, `generate_markdown`, `generate_deep_json` |
| `sharpcirt/tests/test_report_generators.py` | **Create** | Unit tests for generator helpers |
| `sharpcirt/templates/reports/report_template.html` | **Create** | Self-contained HTML report (no external CSS). Used by preview, PDF, HTML archive |
| `sharpcirt/views.py` | **Modify** | Remove pdfkit import; replace pdf/md/json views; add report_preview, download_word, download_csv, download_html |
| `sharpcirt/urls.py` | **Modify** | Add 4 new endpoints (preview, word, csv, html) |
| `sharpcirt/templates/incidents/report.html` | **Rewrite** | Two-panel page: section picker left, iframe preview right |
| `sharpcirt/static/css/report.css` | **Rewrite** | Two-panel layout, export buttons, section picker styles |

---

## Task 1: Install python-docx and create template directory

**Files:**
- No code files — setup only

- [ ] **Step 1: Install python-docx**

```bash
pip install python-docx
```

Expected output: `Successfully installed python-docx-...`

- [ ] **Step 2: Verify install**

```bash
python -c "from docx import Document; print('python-docx OK')"
```

Expected: `python-docx OK`

- [ ] **Step 3: Create the reports template directory**

```bash
mkdir -p sharpcirt/templates/reports
```

- [ ] **Step 4: Remove dead pdfkit import from views.py**

In `sharpcirt/views.py`, find and remove line 19:
```python
import pdfkit
```

The file should keep `from xhtml2pdf import pisa` (line 17) and `from io import BytesIO` (line 18).

- [ ] **Step 5: Commit**

```bash
git add sharpcirt/views.py
git commit -m "chore: install python-docx, remove pdfkit import"
```

---

## Task 2: Create `sharpcirt/report_generators.py`

**Files:**
- Create: `sharpcirt/report_generators.py`
- Create: `sharpcirt/tests/__init__.py` (empty)
- Create: `sharpcirt/tests/test_report_generators.py`

- [ ] **Step 1: Write the tests first**

Create `sharpcirt/tests/__init__.py` (empty file) then create `sharpcirt/tests/test_report_generators.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect ImportError (module doesn't exist yet)**

```bash
python -m pytest sharpcirt/tests/test_report_generators.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'parse_sections' from 'sharpcirt.report_generators'` (or ModuleNotFoundError)

- [ ] **Step 3: Create `sharpcirt/report_generators.py`**

```python
"""
Report generation helpers for OpenCIRT.

Keeps views.py thin: views parse the request and delegate to these functions.
All functions are pure (no Django request objects) so they're easy to test.
"""
from django.utils import timezone

# ── Section constants ────────────────────────────────────────────────────────

ALL_SECTIONS = frozenset([
    'executive_summary',
    'metadata',
    'responders',
    'timeline',
    'iocs',
    'tasks',
    'notes',
    'lessons_learned',
    'technical_details',
])

# Tasks and Notes are off by default per spec
DEFAULT_SECTIONS = frozenset([
    'executive_summary',
    'metadata',
    'responders',
    'timeline',
    'iocs',
    'lessons_learned',
    'technical_details',
])

VALID_TLP = ('WHITE', 'GREEN', 'AMBER', 'RED')

TLP_STYLES = {
    'WHITE': {'bg': '#e8e8e8', 'text': '#333333'},
    'GREEN': {'bg': '#28a745', 'text': '#ffffff'},
    'AMBER': {'bg': '#fd7e14', 'text': '#ffffff'},
    'RED':   {'bg': '#dc3545', 'text': '#ffffff'},
}

# ── Parsers ──────────────────────────────────────────────────────────────────

def parse_sections(data):
    """
    Parse section selection from a GET/POST data dict.
    'sections' should be a comma-separated string of section keys.
    Returns a frozenset. Falls back to DEFAULT_SECTIONS when empty or all invalid.
    """
    raw = data.get('sections', '')
    if not raw:
        return DEFAULT_SECTIONS
    parts = frozenset(s.strip() for s in raw.split(',') if s.strip() in ALL_SECTIONS)
    return parts if parts else DEFAULT_SECTIONS


def parse_tlp(data):
    """
    Parse TLP from a GET/POST data dict.
    Returns an uppercase string, defaulting to 'AMBER' if missing or invalid.
    """
    tlp = data.get('tlp', 'AMBER').upper()
    return tlp if tlp in VALID_TLP else 'AMBER'


# ── Markdown generator ───────────────────────────────────────────────────────

def generate_markdown(incident, sections, tlp, generated_by):
    """
    Build a Markdown report string for the given incident.
    sections: frozenset of section keys to include.
    tlp: one of 'WHITE', 'GREEN', 'AMBER', 'RED'.
    generated_by: username string shown in the header.
    """
    lines = []

    # Header
    lines += [
        f'> **TLP:{tlp}**',
        '',
        f'# Incident Report: {incident.name}',
        '',
        f'*Generated {timezone.now().strftime("%d %B %Y, %H:%M")} by {generated_by}*',
        '',
    ]

    if 'executive_summary' in sections:
        lines += [
            '## Executive Summary',
            '',
            incident.executive_summary or '_No executive summary provided._',
            '',
        ]

    if 'metadata' in sections:
        lines += [
            '## Incident Metadata',
            '',
            '| Field | Value |',
            '|-------|-------|',
            f'| Severity | {incident.severity} |',
            f'| Status | {incident.get_status_display()} |',
            f'| Start | {incident.starting_time} |',
            f'| End | {incident.ending_time} |',
            f'| Duration | {incident.duration} |',
            f'| Time to Detect | {incident.time_to_detect} |',
            f'| Time to Respond | {incident.time_to_respond} |',
            f'| Created by | {incident.created_by.username if incident.created_by else "Unknown"} |',
            f'| Public | {"Yes" if incident.is_public else "No"} |',
            '',
        ]

    if 'responders' in sections:
        lines += [
            '## Responders',
            '',
            '| Username | Display Name | Role | Display Role |',
            '|----------|--------------|------|--------------|',
        ]
        for ur in incident.incident_roles.all().select_related('user'):
            dn = ur.user.displayname or '-'
            dr = ur.display_role or '-'
            lines.append(f'| {ur.user.username} | {dn} | {ur.get_role_display()} | {dr} |')
        lines.append('')

    if 'timeline' in sections:
        lines += ['## Timeline', '']
        qs = incident.actions.all().order_by('observed_at').select_related('created_by')
        if not qs.exists():
            lines += ['_No timeline events recorded._', '']
        else:
            for action in qs:
                if action.observed_at:
                    time_str = action.observed_at.strftime('%Y-%m-%d %H:%M')
                elif action.starting_time:
                    time_str = action.starting_time.strftime('%Y-%m-%d %H:%M')
                else:
                    time_str = ''
                lines.append(f'### [{action.get_type_display()}] {action.title}')
                if time_str:
                    lines.append(f'*{time_str}*')
                lines.append('')
                if action.description:
                    lines += [action.description, '']

    if 'iocs' in sections:
        lines += [
            '## IoC / Evidence',
            '',
            '| Type | Value | Status | Description |',
            '|------|-------|--------|-------------|',
        ]
        iocs_qs = incident.genericiocs.all()
        if not iocs_qs.exists():
            lines.append('| — | _No IoCs recorded._ | — | — |')
        else:
            for ioc in iocs_qs:
                val = ioc.value.replace('|', '\\|')
                desc = (ioc.description or '-').replace('|', '\\|')
                lines.append(
                    f'| {ioc.get_type_display()} | `{val}` | {ioc.get_status_display()} | {desc} |'
                )
        lines.append('')

    if 'tasks' in sections:
        lines += [
            '## Tasks',
            '',
            '| Priority | Title | Status | Assignee |',
            '|----------|-------|--------|----------|',
        ]
        tasks_qs = incident.tasks.all().select_related('assignee')
        if not tasks_qs.exists():
            lines.append('| — | _No tasks recorded._ | — | — |')
        else:
            for task in tasks_qs:
                assignee = task.assignee.username if task.assignee else '-'
                lines.append(f'| {task.priority} | {task.title} | {task.status} | {assignee} |')
        lines.append('')

    if 'notes' in sections:
        lines += ['## Notes', '']
        notes_qs = incident.notes.all().select_related('created_by')
        if not notes_qs.exists():
            lines += ['_No notes recorded._', '']
        else:
            for note in notes_qs:
                author = note.created_by.username if note.created_by else 'Unknown'
                lines += [
                    f'### {note.name}',
                    f'*{author} — {note.created_at.strftime("%Y-%m-%d %H:%M")}*',
                    '',
                    note.text,
                    '',
                ]

    if 'lessons_learned' in sections:
        lines += [
            '## Lessons Learned',
            '',
            incident.lessons_learned or '_No lessons learned recorded._',
            '',
        ]

    if 'technical_details' in sections:
        lines += [
            '## Technical Details',
            '',
            incident.technical_details or '_No technical details recorded._',
            '',
        ]

    return '\n'.join(lines)


# ── Deep JSON serialiser ─────────────────────────────────────────────────────

def generate_deep_json(incident, generated_by):
    """
    Build a deep JSON-serialisable dict for the incident.
    Always exports all sections — the section picker does not apply.
    """

    def fmt_dt(dt):
        return dt.isoformat() if dt else None

    def fmt_td(td):
        return str(td) if td else None

    return {
        'exported_at': timezone.now().isoformat(),
        'exported_by': generated_by,
        'tlp': 'AMBER',
        'incident': {
            'id': incident.id,
            'name': incident.name,
            'description': incident.description,
            'status': incident.status,
            'severity': incident.severity,
            'executive_summary': incident.executive_summary,
            'lessons_learned': incident.lessons_learned,
            'technical_details': incident.technical_details,
            'starting_time': fmt_dt(incident.starting_time),
            'ending_time': fmt_dt(incident.ending_time),
            'duration': fmt_td(incident.duration),
            'time_to_detect': fmt_td(incident.time_to_detect),
            'time_to_respond': fmt_td(incident.time_to_respond),
            'created_at': fmt_dt(incident.created_at),
            'is_public': incident.is_public,
            'created_by': incident.created_by.username if incident.created_by else None,
        },
        'responders': [
            {
                'username': ur.user.username,
                'display_name': ur.user.displayname,
                'email': ur.user.email,
                'role': ur.role,
                'display_role': ur.display_role,
            }
            for ur in incident.incident_roles.all().select_related('user')
        ],
        'iocs': [
            {
                'id': ioc.id,
                'type': ioc.type,
                'type_display': ioc.get_type_display(),
                'value': ioc.value,
                'status': ioc.status,
                'description': ioc.description,
                'created_at': fmt_dt(ioc.created_at),
                'created_by': ioc.created_by.username if ioc.created_by else None,
                'linked_actions': list(ioc.actions.values_list('id', flat=True)),
            }
            for ioc in (
                incident.genericiocs.all()
                .prefetch_related('actions')
                .select_related('created_by')
            )
        ],
        'timeline': [
            {
                'id': action.id,
                'type': action.type,
                'type_display': action.get_type_display(),
                'title': action.title,
                'description': action.description,
                'observed_at': fmt_dt(action.observed_at),
                'starting_time': fmt_dt(action.starting_time),
                'ending_time': fmt_dt(action.ending_time),
                'created_at': fmt_dt(action.created_at),
                'created_by': action.created_by.username if action.created_by else None,
                'iocs': list(action.iocs.values_list('id', flat=True)),
                'tags': [{'name': t.name, 'color': t.color} for t in action.tags.all()],
            }
            for action in (
                incident.actions.all()
                .order_by('observed_at')
                .prefetch_related('iocs', 'tags')
                .select_related('created_by')
            )
        ],
        'notes': [
            {
                'id': note.id,
                'name': note.name,
                'text': note.text,
                'created_at': fmt_dt(note.created_at),
                'created_by': note.created_by.username if note.created_by else None,
            }
            for note in incident.notes.all().select_related('created_by')
        ],
        'tasks': [
            {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'assignee': task.assignee.username if task.assignee else None,
                'external_reference': task.external_reference,
                'created_at': fmt_dt(task.created_at),
            }
            for task in incident.tasks.all().select_related('assignee')
        ],
        'impacts': [
            {
                'id': impact.id,
                'title': impact.title,
                'description': impact.description,
                'severity': impact.severity,
                'status': impact.status,
                'type': impact.type,
            }
            for impact in incident.impacts.all()
        ],
    }
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python -m pytest sharpcirt/tests/test_report_generators.py -v
```

Expected: all 18 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sharpcirt/report_generators.py sharpcirt/tests/
git commit -m "feat: add report_generators module with parse_sections, parse_tlp, generate_markdown, generate_deep_json"
```

---

## Task 3: Create unified HTML report template

**Files:**
- Create: `sharpcirt/templates/reports/report_template.html`

This template is self-contained (all CSS inline, no external dependencies). It is used by:
- `report_preview` → returned as HTML for the iframe `srcdoc`
- `download_incident_pdf` → fed to xhtml2pdf
- `download_incident_html` → sent as an HTML archive attachment

Context variables it expects:
- `incident` — Incident model instance
- `sections` — frozenset of section keys
- `tlp` — one of WHITE / GREEN / AMBER / RED
- `tlp_style` — dict with keys `bg` and `text` (precomputed in view from TLP_STYLES)
- `is_pdf` — bool; if True, renders a PDF footer via xhtml2pdf fixed positioning
- `generated_at` — formatted datetime string
- `generated_by` — username string

- [ ] **Step 1: Create `sharpcirt/templates/reports/report_template.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{{ incident.name }} — Incident Report</title>
<style>
/* ── Reset ── */
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: Arial, Helvetica, sans-serif;
    background: #fff;
    color: #1a1a1a;
    font-size: 11pt;
    line-height: 1.6;
    padding: 28px 36px;
}

/* ── TLP ── */
.tlp-white { background: #e8e8e8; color: #333; }
.tlp-green { background: #28a745; color: #fff; }
.tlp-amber { background: #fd7e14; color: #fff; }
.tlp-red   { background: #dc3545; color: #fff; }

/* ── TLP banner (HTML preview / archive only) ── */
.tlp-banner {
    padding: 7px 16px;
    font-size: 9pt;
    font-weight: 700;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: -28px -36px 28px -36px;
}

/* ── PDF footer (xhtml2pdf fixed positioning) ── */
.pdf-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 5px 12px;
    font-size: 8pt;
    text-align: center;
    font-family: Arial;
    border-top: 1px solid #ddd;
}

/* ── Cover ── */
.cover {
    border-bottom: 3px solid #c49840;
    padding-bottom: 24px;
    margin-bottom: 32px;
}
.cover-tlp {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 16px;
}
.cover h1 {
    font-size: 20pt;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 14px;
}
.cover-badges { margin-bottom: 12px; }
.sev-badge, .status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 8.5pt;
    font-weight: 700;
    text-transform: uppercase;
    margin-right: 6px;
}
.sev-critical { background: #dc2626; color: #fff; }
.sev-high     { background: #ea580c; color: #fff; }
.sev-medium   { background: #d97706; color: #fff; }
.sev-low      { background: #65a30d; color: #fff; }
.status-badge { background: #e8e8e8; color: #555; }
.cover-footer { font-size: 8.5pt; color: #888; margin-top: 14px; }
.cover-id { font-size: 8pt; color: #aaa; }

/* ── Sections ── */
.report-section { margin-bottom: 32px; page-break-inside: avoid; }
.section-title {
    font-size: 13pt;
    font-weight: 700;
    color: #1a1a1a;
    border-bottom: 1px solid #e5d0a0;
    padding-bottom: 7px;
    margin-bottom: 14px;
}
.section-prose { font-size: 10pt; color: #333; white-space: pre-wrap; }
.section-prose-mono { font-family: 'Courier New', monospace; font-size: 9pt; color: #333; background: #faf4e5; padding: 12px; border: 1px solid #e5d0a0; border-radius: 4px; white-space: pre-wrap; }

/* ── Tables ── */
.report-table { width: 100%; border-collapse: collapse; font-size: 9pt; margin-top: 4px; }
.report-table th {
    background: #f5e8cc;
    color: #1a1a1a;
    font-weight: 700;
    padding: 6px 10px;
    border: 1px solid #e5d0a0;
    text-align: left;
}
.report-table td {
    padding: 5px 10px;
    border: 1px solid #e5d0a0;
    vertical-align: top;
}
.report-table tr:nth-child(even) td { background: #fdfaf3; }
.mono { font-family: 'Courier New', monospace; font-size: 8pt; word-break: break-all; }

/* ── Metadata key-value table ── */
.meta-table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
.meta-table td { padding: 5px 10px; border: 1px solid #e5d0a0; }
.meta-table td:first-child {
    font-weight: 700;
    background: #faf4e5;
    width: 38%;
    color: #666;
}

/* ── Timeline ── */
.tl-entry {
    border-left: 3px solid #c49840;
    padding-left: 14px;
    margin-bottom: 14px;
}
.tl-time { font-size: 8pt; color: #999; margin-bottom: 3px; }
.tl-type {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 5px;
}
.tl-malicious    { background: #fee2e2; color: #991b1b; }
.tl-defensive    { background: #dcfce7; color: #166534; }
.tl-mitigation   { background: #fef9c3; color: #854d0e; }
.tl-communication{ background: #dbeafe; color: #1e40af; }
.tl-alert        { background: #ffe4e6; color: #9f1239; }
.tl-other        { background: #f3f4f6; color: #374151; }
.tl-title        { font-weight: 700; font-size: 10pt; margin-bottom: 5px; }
.tl-desc         { font-size: 9pt; color: #444; }

/* ── Notes ── */
.note-block { border: 1px solid #e5d0a0; border-radius: 5px; margin-bottom: 14px; }
.note-header {
    background: #faf4e5;
    padding: 7px 12px;
    border-bottom: 1px solid #e5d0a0;
}
.note-title { font-weight: 700; font-size: 10pt; }
.note-meta  { font-size: 8pt; color: #999; margin-top: 2px; }
.note-body  { padding: 10px 12px; font-size: 9.5pt; white-space: pre-wrap; }

/* ── Utilities ── */
.empty-msg { color: #aaa; font-style: italic; font-size: 9pt; }
</style>
</head>
<body>

{% if not is_pdf %}
<!-- TLP banner shown in HTML preview and archive, not in PDF (footer handles it there) -->
<div class="tlp-banner tlp-{{ tlp|lower }}"
     style="background:{{ tlp_style.bg }};color:{{ tlp_style.text }};">
    TLP:{{ tlp }} — Handle according to TLP guidelines
</div>
{% endif %}

<!-- ── Cover (always rendered) ── -->
<div class="cover">
    <div class="cover-tlp tlp-{{ tlp|lower }}"
         style="background:{{ tlp_style.bg }};color:{{ tlp_style.text }};">
        TLP:{{ tlp }}
    </div>
    <h1>{{ incident.name }}</h1>
    <div class="cover-badges">
        <span class="sev-badge sev-{{ incident.severity|lower }}">{{ incident.severity }}</span>
        <span class="status-badge">{{ incident.get_status_display }}</span>
    </div>
    <div class="cover-footer">
        Generated {{ generated_at }} &nbsp;·&nbsp; by {{ generated_by }}
    </div>
    <div class="cover-id">Incident #{{ incident.id }}</div>
</div>

<!-- ── Executive Summary ── -->
{% if 'executive_summary' in sections %}
<div class="report-section">
    <div class="section-title">Executive Summary</div>
    {% if incident.executive_summary %}
    <div class="section-prose">{{ incident.executive_summary }}</div>
    {% else %}
    <div class="empty-msg">No executive summary provided.</div>
    {% endif %}
</div>
{% endif %}

<!-- ── Incident Metadata ── -->
{% if 'metadata' in sections %}
<div class="report-section">
    <div class="section-title">Incident Metadata</div>
    <table class="meta-table">
        <tr><td>Severity</td><td>{{ incident.severity }}</td></tr>
        <tr><td>Status</td><td>{{ incident.get_status_display }}</td></tr>
        <tr><td>Start time</td><td>{{ incident.starting_time }}</td></tr>
        <tr><td>End time</td><td>{{ incident.ending_time }}</td></tr>
        <tr><td>Duration</td><td>{{ incident.duration }}</td></tr>
        <tr><td>Time to detect (TTD)</td><td>{{ incident.time_to_detect }}</td></tr>
        <tr><td>Time to respond (TTR)</td><td>{{ incident.time_to_respond }}</td></tr>
        <tr><td>Public</td><td>{% if incident.is_public %}Yes{% else %}No{% endif %}</td></tr>
        <tr><td>Created by</td><td>{{ incident.created_by.username|default:"Unknown" }}</td></tr>
        <tr><td>Created at</td><td>{{ incident.created_at }}</td></tr>
    </table>
</div>
{% endif %}

<!-- ── Responders ── -->
{% if 'responders' in sections %}
<div class="report-section">
    <div class="section-title">Responders</div>
    {% with roles=incident.incident_roles.all %}
    {% if roles %}
    <table class="report-table">
        <thead>
            <tr><th>Username</th><th>Display Name</th><th>Role</th><th>Display Role</th></tr>
        </thead>
        <tbody>
            {% for ur in roles %}
            <tr>
                <td>{{ ur.user.username }}</td>
                <td>{{ ur.user.displayname|default:"-" }}</td>
                <td>{{ ur.get_role_display }}</td>
                <td>{{ ur.display_role|default:"-" }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty-msg">No responders recorded.</div>
    {% endif %}
    {% endwith %}
</div>
{% endif %}

<!-- ── Timeline ── -->
{% if 'timeline' in sections %}
<div class="report-section">
    <div class="section-title">Timeline</div>
    {% with actions=incident.sorted_actions %}
    {% if actions %}
        {% for action in actions %}
        <div class="tl-entry">
            <div class="tl-time">
                {% if action.observed_at %}{{ action.observed_at|date:"d M Y · H:i" }}
                {% elif action.starting_time %}{{ action.starting_time|date:"d M Y · H:i" }} → {{ action.ending_time|date:"H:i" }}
                {% endif %}
            </div>
            <span class="tl-type tl-{{ action.type|lower }}">{{ action.get_type_display }}</span>
            <div class="tl-title">{{ action.title }}</div>
            {% if action.description %}
            <div class="tl-desc">{{ action.description }}</div>
            {% endif %}
        </div>
        {% endfor %}
    {% else %}
    <div class="empty-msg">No timeline events recorded.</div>
    {% endif %}
    {% endwith %}
</div>
{% endif %}

<!-- ── IoC / Evidence ── -->
{% if 'iocs' in sections %}
<div class="report-section">
    <div class="section-title">IoC / Evidence</div>
    {% with iocs=incident.genericiocs.all %}
    {% if iocs %}
    <table class="report-table">
        <thead>
            <tr><th>Type</th><th>Value</th><th>Status</th><th>Description</th></tr>
        </thead>
        <tbody>
            {% for ioc in iocs %}
            <tr>
                <td>{{ ioc.get_type_display }}</td>
                <td class="mono">{{ ioc.value }}</td>
                <td>{{ ioc.get_status_display }}</td>
                <td>{{ ioc.description|default:"-" }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty-msg">No IoCs recorded.</div>
    {% endif %}
    {% endwith %}
</div>
{% endif %}

<!-- ── Tasks ── -->
{% if 'tasks' in sections %}
<div class="report-section">
    <div class="section-title">Tasks</div>
    {% with tasks=incident.tasks.all %}
    {% if tasks %}
    <table class="report-table">
        <thead>
            <tr><th>Priority</th><th>Title</th><th>Status</th><th>Assignee</th><th>Description</th></tr>
        </thead>
        <tbody>
            {% for task in tasks %}
            <tr>
                <td>{{ task.priority }}</td>
                <td>{{ task.title }}</td>
                <td>{{ task.status }}</td>
                <td>{{ task.assignee.username|default:"-" }}</td>
                <td>{{ task.description|default:"-" }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty-msg">No tasks recorded.</div>
    {% endif %}
    {% endwith %}
</div>
{% endif %}

<!-- ── Notes ── -->
{% if 'notes' in sections %}
<div class="report-section">
    <div class="section-title">Notes</div>
    {% with notes=incident.notes.all %}
    {% if notes %}
        {% for note in notes %}
        <div class="note-block">
            <div class="note-header">
                <div class="note-title">{{ note.name }}</div>
                <div class="note-meta">
                    {{ note.created_by.username|default:"Unknown" }} &nbsp;·&nbsp;
                    {{ note.created_at|date:"d M Y · H:i" }}
                </div>
            </div>
            <div class="note-body">{{ note.text }}</div>
        </div>
        {% endfor %}
    {% else %}
    <div class="empty-msg">No notes recorded.</div>
    {% endif %}
    {% endwith %}
</div>
{% endif %}

<!-- ── Lessons Learned ── -->
{% if 'lessons_learned' in sections %}
<div class="report-section">
    <div class="section-title">Lessons Learned</div>
    {% if incident.lessons_learned and incident.lessons_learned != 'SOME STRING' %}
    <div class="section-prose">{{ incident.lessons_learned }}</div>
    {% else %}
    <div class="empty-msg">No lessons learned recorded.</div>
    {% endif %}
</div>
{% endif %}

<!-- ── Technical Details ── -->
{% if 'technical_details' in sections %}
<div class="report-section">
    <div class="section-title">Technical Details</div>
    {% if incident.technical_details and incident.technical_details != 'SOME STRING' %}
    <div class="section-prose-mono">{{ incident.technical_details }}</div>
    {% else %}
    <div class="empty-msg">No technical details recorded.</div>
    {% endif %}
</div>
{% endif %}

<!-- ── PDF footer (xhtml2pdf fixed, repeats on every page) ── -->
{% if is_pdf %}
<div class="pdf-footer tlp-{{ tlp|lower }}"
     style="background:{{ tlp_style.bg }};color:{{ tlp_style.text }};">
    TLP:{{ tlp }} &nbsp;|&nbsp; {{ incident.name }} &nbsp;|&nbsp; Generated {{ generated_at }}
</div>
{% endif %}

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add sharpcirt/templates/reports/report_template.html
git commit -m "feat: add self-contained unified report HTML template"
```

---

## Task 4: Add `report_preview` view and URL

**Files:**
- Modify: `sharpcirt/views.py` — add import + view
- Modify: `sharpcirt/urls.py` — add URL pattern

- [ ] **Step 1: Add import to views.py**

At the top of `sharpcirt/views.py`, after the existing imports (around line 22), add:

```python
from .report_generators import parse_sections, parse_tlp, TLP_STYLES, DEFAULT_SECTIONS, ALL_SECTIONS, generate_markdown, generate_deep_json
import csv
from io import StringIO
```

- [ ] **Step 2: Add the `report_preview` view to views.py**

Add this function **before** the existing `report` view (around line 362). Insert it before `@login_required(login_url='login')  def report(...)`:

```python
@login_required(login_url='login')
@user_is_incident_responder_orpublic
def report_preview(request, id):
    """
    GET /api/incident/<id>/report-preview/?sections=executive_summary,iocs&tlp=AMBER
    Returns an HTML string for the iframe srcdoc.
    """
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return HttpResponse('<p style="padding:20px;color:#dc2626;">Incident not found.</p>', status=404)

    sections = parse_sections(request.GET)
    tlp = parse_tlp(request.GET)
    tlp_style = TLP_STYLES[tlp]

    html = render_to_string('reports/report_template.html', {
        'incident': incident,
        'sections': sections,
        'tlp': tlp,
        'tlp_style': tlp_style,
        'is_pdf': False,
        'generated_at': timezone.now().strftime('%d %B %Y, %H:%M'),
        'generated_by': request.user.username,
    })
    return HttpResponse(html, content_type='text/html; charset=utf-8')
```

- [ ] **Step 3: Add URL pattern to urls.py**

In `sharpcirt/urls.py`, add after the `download-pdf` line (around line 36):

```python
path('api/incident/<int:id>/report-preview/', views.report_preview, name='report_preview'),
```

- [ ] **Step 4: Manual smoke test**

Start the server (`python manage.py runserver 8765`) and visit:
```
http://localhost:8765/api/incident/1/report-preview/?sections=executive_summary,metadata&tlp=AMBER
```
Expected: a styled HTML page with cover + executive summary + metadata sections, orange TLP:AMBER banner at top.

- [ ] **Step 5: Commit**

```bash
git add sharpcirt/views.py sharpcirt/urls.py
git commit -m "feat: add report_preview API endpoint"
```

---

## Task 5: Rewrite `download_incident_pdf` (xhtml2pdf)

**Files:**
- Modify: `sharpcirt/views.py` — replace the existing `download_incident_pdf` function

- [ ] **Step 1: Replace the function**

Find the existing `download_incident_pdf` function (starts around line 696 after `pdfkit` removal). Replace the entire function body with:

```python
@login_required(login_url='login')
@user_is_incident_responder
def download_incident_pdf(request, id):
    """
    POST /api/incident/<id>/download-pdf/
    Body (form-encoded): sections=executive_summary,iocs&tlp=AMBER
    Returns a PDF file download.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)
    tlp_style = TLP_STYLES[tlp]

    html = render_to_string('reports/report_template.html', {
        'incident': incident,
        'sections': sections,
        'tlp': tlp,
        'tlp_style': tlp_style,
        'is_pdf': True,
        'generated_at': timezone.now().strftime('%d %B %Y, %H:%M'),
        'generated_by': request.user.username,
    })

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')

    if pisa_status.err:
        return HttpResponse(
            f'PDF generation error (xhtml2pdf code {pisa_status.err}). '
            f'Try the HTML export as a workaround.',
            status=500
        )

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.pdf"'
    )
    return response
```

- [ ] **Step 2: Manual smoke test**

On the server, submit a POST to the endpoint (easiest via the report page UI built in Task 11). For now, test with curl:

```bash
curl -s -X POST http://localhost:8765/api/incident/1/download-pdf/ \
  -b "sessionid=<your-session-cookie>" \
  -d "csrfmiddlewaretoken=<csrf>&sections=executive_summary,metadata,iocs&tlp=AMBER" \
  -o /tmp/test.pdf
file /tmp/test.pdf
```

Expected: `PDF document, version 1.4` (or similar).

- [ ] **Step 3: Commit**

```bash
git add sharpcirt/views.py
git commit -m "feat: replace wkhtmltopdf PDF with xhtml2pdf, add section/TLP support"
```

---

## Task 6: Add `download_incident_word` view

**Files:**
- Modify: `sharpcirt/views.py` — add import + new view
- Modify: `sharpcirt/urls.py` — add URL pattern

- [ ] **Step 1: Add python-docx import to views.py**

After the existing imports block at the top of `sharpcirt/views.py`, add:

```python
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor
```

- [ ] **Step 2: Add the view after `download_incident_pdf`**

```python
@login_required(login_url='login')
@user_is_incident_responder
def download_incident_word(request, id):
    """
    POST /api/incident/<id>/download-word/
    Body: sections=..., tlp=...
    Returns a .docx file download.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)

    TLP_COLORS = {
        'WHITE': RGBColor(80, 80, 80),
        'GREEN': RGBColor(40, 167, 69),
        'AMBER': RGBColor(253, 126, 20),
        'RED':   RGBColor(220, 53, 69),
    }

    doc = DocxDocument()

    # ── Cover ──
    doc.add_heading(incident.name, 0)

    tlp_para = doc.add_paragraph()
    tlp_run = tlp_para.add_run(f'TLP:{tlp}')
    tlp_run.bold = True
    tlp_run.font.size = Pt(13)
    tlp_run.font.color.rgb = TLP_COLORS.get(tlp, RGBColor(80, 80, 80))

    meta_para = doc.add_paragraph()
    meta_para.add_run(
        f'Generated {timezone.now().strftime("%d %B %Y, %H:%M")} by {request.user.username}'
    ).font.color.rgb = RGBColor(130, 130, 130)
    doc.add_paragraph()  # spacer

    # ── Executive Summary ──
    if 'executive_summary' in sections:
        doc.add_heading('Executive Summary', 1)
        doc.add_paragraph(incident.executive_summary or 'No executive summary provided.')

    # ── Metadata ──
    if 'metadata' in sections:
        doc.add_heading('Incident Metadata', 1)
        table = doc.add_table(rows=0, cols=2)
        table.style = 'Table Grid'
        for label, value in [
            ('Severity', incident.severity),
            ('Status', incident.get_status_display()),
            ('Start time', str(incident.starting_time)),
            ('End time', str(incident.ending_time)),
            ('Duration', str(incident.duration)),
            ('Time to detect', str(incident.time_to_detect)),
            ('Time to respond', str(incident.time_to_respond)),
            ('Created by', incident.created_by.username if incident.created_by else 'Unknown'),
            ('Public', 'Yes' if incident.is_public else 'No'),
        ]:
            row = table.add_row().cells
            row[0].text = label
            row[1].text = value

    # ── Responders ──
    if 'responders' in sections:
        doc.add_heading('Responders', 1)
        roles_qs = incident.incident_roles.all().select_related('user')
        if roles_qs.exists():
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            for i, h in enumerate(['Username', 'Display Name', 'Role', 'Display Role']):
                table.rows[0].cells[i].text = h
            for ur in roles_qs:
                row = table.add_row().cells
                row[0].text = ur.user.username
                row[1].text = ur.user.displayname or '-'
                row[2].text = ur.get_role_display()
                row[3].text = ur.display_role or '-'
        else:
            doc.add_paragraph('No responders recorded.')

    # ── Timeline ──
    if 'timeline' in sections:
        doc.add_heading('Timeline', 1)
        actions_qs = incident.actions.all().order_by('observed_at').select_related('created_by')
        if not actions_qs.exists():
            doc.add_paragraph('No timeline events recorded.')
        else:
            for action in actions_qs:
                if action.observed_at:
                    time_str = action.observed_at.strftime('%d %b %Y %H:%M')
                elif action.starting_time:
                    time_str = action.starting_time.strftime('%d %b %Y %H:%M')
                else:
                    time_str = ''
                p = doc.add_paragraph(style='List Bullet')
                r = p.add_run(f'[{action.get_type_display()}] {action.title}')
                r.bold = True
                if time_str:
                    p.add_run(f'  —  {time_str}')
                if action.description:
                    doc.add_paragraph(action.description)

    # ── IoCs ──
    if 'iocs' in sections:
        doc.add_heading('IoC / Evidence', 1)
        iocs_qs = incident.genericiocs.all()
        if not iocs_qs.exists():
            doc.add_paragraph('No IoCs recorded.')
        else:
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            for i, h in enumerate(['Type', 'Value', 'Status', 'Description']):
                table.rows[0].cells[i].text = h
            for ioc in iocs_qs:
                row = table.add_row().cells
                row[0].text = ioc.get_type_display()
                row[1].text = ioc.value
                row[2].text = ioc.get_status_display()
                row[3].text = ioc.description or '-'

    # ── Tasks ──
    if 'tasks' in sections:
        doc.add_heading('Tasks', 1)
        tasks_qs = incident.tasks.all().select_related('assignee')
        if not tasks_qs.exists():
            doc.add_paragraph('No tasks recorded.')
        else:
            table = doc.add_table(rows=1, cols=5)
            table.style = 'Table Grid'
            for i, h in enumerate(['Priority', 'Title', 'Status', 'Assignee', 'Description']):
                table.rows[0].cells[i].text = h
            for task in tasks_qs:
                row = table.add_row().cells
                row[0].text = task.priority
                row[1].text = task.title
                row[2].text = task.status
                row[3].text = task.assignee.username if task.assignee else '-'
                row[4].text = task.description or '-'

    # ── Notes ──
    if 'notes' in sections:
        doc.add_heading('Notes', 1)
        notes_qs = incident.notes.all().select_related('created_by')
        if not notes_qs.exists():
            doc.add_paragraph('No notes recorded.')
        else:
            for note in notes_qs:
                doc.add_heading(note.name, 2)
                author = note.created_by.username if note.created_by else 'Unknown'
                p = doc.add_paragraph()
                p.add_run(
                    f'{author}  ·  {note.created_at.strftime("%d %b %Y %H:%M")}'
                ).italic = True
                doc.add_paragraph(note.text)

    # ── Lessons Learned ──
    if 'lessons_learned' in sections:
        doc.add_heading('Lessons Learned', 1)
        ll = incident.lessons_learned
        doc.add_paragraph(
            ll if ll and ll != 'SOME STRING' else 'No lessons learned recorded.'
        )

    # ── Technical Details ──
    if 'technical_details' in sections:
        doc.add_heading('Technical Details', 1)
        td = incident.technical_details
        doc.add_paragraph(
            td if td and td != 'SOME STRING' else 'No technical details recorded.'
        )

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.docx"'
    )
    return response
```

- [ ] **Step 3: Add URL to urls.py**

```python
path('api/incident/<int:id>/download-word/', views.download_incident_word, name='download_incident_word'),
```

- [ ] **Step 4: Smoke test**

Navigate to the report page (Task 11) and click the Word button, or use curl. Open the resulting .docx in LibreOffice / Word.

- [ ] **Step 5: Commit**

```bash
git add sharpcirt/views.py sharpcirt/urls.py
git commit -m "feat: add Word (.docx) export via python-docx"
```

---

## Task 7: Rewrite `download_incident_markdown`

**Files:**
- Modify: `sharpcirt/views.py` — replace the function body

- [ ] **Step 1: Replace the function**

Find the existing `download_incident_markdown` function (currently around line 674). Replace it entirely with:

```python
@login_required(login_url='login')
@user_is_incident_responder
def download_incident_markdown(request, id):
    """
    POST /api/incident/<id>/download-markdown/
    Body: sections=..., tlp=...
    Returns a .md file download.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)

    content = generate_markdown(incident, sections, tlp, request.user.username)

    response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.md"'
    )
    return response
```

- [ ] **Step 2: Commit**

```bash
git add sharpcirt/views.py
git commit -m "feat: rewrite markdown export with section picker + TLP support"
```

---

## Task 8: Rewrite `download_incident_json` (deep export)

**Files:**
- Modify: `sharpcirt/views.py` — replace the function body

- [ ] **Step 1: Replace the function**

Find the existing `download_incident_json` function (currently around line 652). Replace it entirely with:

```python
@login_required(login_url='login')
@user_is_incident_responder_orpublic
def download_incident_json(request, id):
    """
    GET /api/incident/<id>/download-json/
    Returns a full deep JSON export (sections don't apply — always full).
    """
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    data = generate_deep_json(incident, request.user.username)

    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_full.json"'
    )
    return response
```

- [ ] **Step 2: Commit**

```bash
git add sharpcirt/views.py
git commit -m "feat: replace shallow JSON export with deep serialiser (iocs, timeline, notes, tasks, impacts)"
```

---

## Task 9: Add `download_incident_csv` view

**Files:**
- Modify: `sharpcirt/views.py` — add new view
- Modify: `sharpcirt/urls.py` — add URL pattern

- [ ] **Step 1: Add the view after `download_incident_json`**

```python
@login_required(login_url='login')
@user_is_incident_responder_orpublic
def download_incident_csv(request, id):
    """
    GET /api/incident/<id>/download-csv/
    Returns a CSV of all IoCs (sections don't apply).
    Columns: Type, Value, Status, Description, Created At, Linked Actions
    """
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Type', 'Value', 'Status', 'Description', 'Created At', 'Linked Actions'])

    for ioc in (
        incident.genericiocs.all()
        .prefetch_related('actions')
        .select_related('created_by')
    ):
        linked = ', '.join(str(a.title) for a in ioc.actions.all())
        writer.writerow([
            ioc.get_type_display(),
            ioc.value,
            ioc.get_status_display(),
            ioc.description or '',
            ioc.created_at.strftime('%Y-%m-%d %H:%M') if ioc.created_at else '',
            linked,
        ])

    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_iocs.csv"'
    )
    return response
```

- [ ] **Step 2: Add URL to urls.py**

```python
path('api/incident/<int:id>/download-csv/', views.download_incident_csv, name='download_incident_csv'),
```

- [ ] **Step 3: Commit**

```bash
git add sharpcirt/views.py sharpcirt/urls.py
git commit -m "feat: add CSV IoC export"
```

---

## Task 10: Add `download_incident_html` view

**Files:**
- Modify: `sharpcirt/views.py` — add new view
- Modify: `sharpcirt/urls.py` — add URL pattern

- [ ] **Step 1: Add the view**

```python
@login_required(login_url='login')
@user_is_incident_responder
def download_incident_html(request, id):
    """
    POST /api/incident/<id>/download-html/
    Body: sections=..., tlp=...
    Returns the report as a self-contained .html file download.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)
    tlp_style = TLP_STYLES[tlp]

    html = render_to_string('reports/report_template.html', {
        'incident': incident,
        'sections': sections,
        'tlp': tlp,
        'tlp_style': tlp_style,
        'is_pdf': False,
        'generated_at': timezone.now().strftime('%d %B %Y, %H:%M'),
        'generated_by': request.user.username,
    })

    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.html"'
    )
    return response
```

- [ ] **Step 2: Add URL to urls.py**

```python
path('api/incident/<int:id>/download-html/', views.download_incident_html, name='download_incident_html'),
```

- [ ] **Step 3: Commit**

```bash
git add sharpcirt/views.py sharpcirt/urls.py
git commit -m "feat: add HTML archive export"
```

---

## Task 11: Report page UI — rewrite `report.html` and `report.css`

**Files:**
- Modify: `sharpcirt/views.py` — update `report` view context
- Rewrite: `sharpcirt/templates/incidents/report.html`
- Rewrite: `sharpcirt/static/css/report.css`

### Sub-step A: Update the `report` view

- [ ] **Step 1: Update the `report` view to pass the sections info**

Find `def report(request, id):` (around line 364). Replace the entire function with:

```python
@login_required(login_url='login')
@user_is_incident_responder_orpublic
def report(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        return HttpResponse("Incident not found.", status=404)

    return render(request, 'incidents/report.html', {
        'incident': incident,
        'user': request.user,
        'current_user_role': user_role,
        'all_sections': list(ALL_SECTIONS),
        'default_sections': list(DEFAULT_SECTIONS),
    })
```

### Sub-step B: Rewrite `report.html`

- [ ] **Step 2: Rewrite `sharpcirt/templates/incidents/report.html`**

```html
{% extends 'incidents/base.html' %}
{% load static %}

{% block styles %}
<link rel="stylesheet" href="{% static 'css/report.css' %}">
{% endblock %}

{% block content %}
<div class="report-page">

    <!-- ── LEFT PANEL: section picker ── -->
    <div class="report-left-panel">

        <div class="panel-section">
            <div class="panel-label">Sections</div>
            <div class="section-list">

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="executive_summary" checked>
                    <span class="section-item-label">Executive Summary</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="metadata" checked>
                    <span class="section-item-label">Incident Metadata</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="responders" checked>
                    <span class="section-item-label">Responders</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="timeline" checked>
                    <span class="section-item-label">Timeline</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="iocs" checked>
                    <span class="section-item-label">IoC / Evidence</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="tasks">
                    <span class="section-item-label">Tasks</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="notes">
                    <span class="section-item-label">Notes</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="lessons_learned" checked>
                    <span class="section-item-label">Lessons Learned</span>
                </label>

                <label class="section-item">
                    <input type="checkbox" class="section-cb" value="technical_details" checked>
                    <span class="section-item-label">Technical Details</span>
                </label>

            </div>
        </div>

        <div class="panel-section">
            <div class="panel-label">TLP Classification</div>
            <div class="tlp-pills">
                <button class="tlp-pill tlp-white" data-tlp="WHITE">WHITE</button>
                <button class="tlp-pill tlp-green" data-tlp="GREEN">GREEN</button>
                <button class="tlp-pill tlp-amber tlp-active" data-tlp="AMBER">AMBER</button>
                <button class="tlp-pill tlp-red" data-tlp="RED">RED</button>
            </div>
        </div>

        <div class="panel-section">
            <div class="panel-label">Export</div>
            <div class="export-btn-grid">
                <button class="export-btn export-primary" onclick="exportFormat('pdf')">
                    <i class="fa-regular fa-file-pdf"></i> PDF
                </button>
                <button class="export-btn" onclick="exportFormat('word')">
                    <i class="fa-regular fa-file-word"></i> Word
                </button>
                <button class="export-btn" onclick="exportFormat('markdown')">
                    <i class="fa-brands fa-markdown"></i> Markdown
                </button>
                <button class="export-btn" onclick="exportFormat('json')">
                    <i class="fa-solid fa-code"></i> JSON
                </button>
                <button class="export-btn" onclick="exportFormat('csv')">
                    <i class="fa-regular fa-file-lines"></i> CSV IoCs
                </button>
                <button class="export-btn" onclick="exportFormat('html')">
                    <i class="fa-brands fa-html5"></i> HTML
                </button>
            </div>
        </div>

    </div>

    <!-- ── RIGHT PANEL: live preview ── -->
    <div class="report-right-panel">
        <div class="preview-toolbar">
            <span class="preview-label">
                <i class="fa-regular fa-eye"></i> Live Preview
            </span>
            <span class="preview-loading" id="preview-loading" style="display:none;">
                <i class="fa-solid fa-spinner fa-spin"></i> Updating…
            </span>
        </div>
        <iframe id="report-preview" class="report-iframe" srcdoc="<p style='padding:24px;font-family:sans-serif;color:#aaa;'>Loading preview…</p>"></iframe>
    </div>

</div>

<script>
const INCIDENT_ID = {{ incident.id }};

// ── Helpers ─────────────────────────────────────────────────────────────────

function getSelectedSections() {
    return Array.from(document.querySelectorAll('.section-cb:checked'))
        .map(cb => cb.value)
        .join(',');
}

function getSelectedTlp() {
    const active = document.querySelector('.tlp-pill.tlp-active');
    return active ? active.dataset.tlp : 'AMBER';
}

function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
}

// ── Preview ──────────────────────────────────────────────────────────────────

let previewTimer = null;

async function refreshPreview() {
    const sections = getSelectedSections();
    const tlp = getSelectedTlp();
    const url = `/api/incident/${INCIDENT_ID}/report-preview/?sections=${encodeURIComponent(sections)}&tlp=${tlp}`;

    document.getElementById('preview-loading').style.display = 'inline-flex';
    try {
        const resp = await fetch(url, { credentials: 'same-origin' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const html = await resp.text();
        document.getElementById('report-preview').srcdoc = html;
    } catch (e) {
        document.getElementById('report-preview').srcdoc =
            `<p style="padding:20px;color:#dc2626;font-family:sans-serif;">Preview failed: ${e.message}</p>`;
    } finally {
        document.getElementById('preview-loading').style.display = 'none';
    }
}

function schedulePreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(refreshPreview, 400);
}

// ── Export ───────────────────────────────────────────────────────────────────

function exportFormat(format) {
    const sections = getSelectedSections();
    const tlp = getSelectedTlp();

    // JSON and CSV: GET endpoints, no sections needed
    if (format === 'json') {
        window.location.href = `/api/incident/${INCIDENT_ID}/download-json/`;
        return;
    }
    if (format === 'csv') {
        window.location.href = `/api/incident/${INCIDENT_ID}/download-csv/`;
        return;
    }

    // PDF, Word, Markdown, HTML: POST with sections + TLP
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/api/incident/${INCIDENT_ID}/download-${format}/`;

    const fields = {
        csrfmiddlewaretoken: getCsrf(),
        sections: sections,
        tlp: tlp,
    };
    for (const [name, value] of Object.entries(fields)) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
    }

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}

// ── Event listeners ──────────────────────────────────────────────────────────

document.querySelectorAll('.section-cb').forEach(cb => {
    cb.addEventListener('change', schedulePreview);
});

document.querySelectorAll('.tlp-pill').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tlp-pill').forEach(b => b.classList.remove('tlp-active'));
        btn.classList.add('tlp-active');
        schedulePreview();
    });
});

// Initial load
refreshPreview();
</script>

{% endblock %}
```

### Sub-step C: Rewrite `report.css`

- [ ] **Step 3: Rewrite `sharpcirt/static/css/report.css`**

```css
/* ── Report page — two-panel layout ── */

.report-page {
    display: flex;
    height: calc(100vh - 56px); /* subtract base.html navbar height */
    overflow: hidden;
    background: var(--background-color);
}

/* ── Left panel ── */
.report-left-panel {
    width: 290px;
    min-width: 290px;
    border-right: 1px solid var(--border-color);
    background: var(--widget-background-color);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0;
}

.panel-section {
    padding: 16px 18px;
    border-bottom: 1px solid var(--border-color);
}

.panel-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-color-2);
    margin-bottom: 12px;
}

/* ── Section checkboxes ── */
.section-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.section-item {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 6px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.12s;
}

.section-item:hover {
    background: var(--main-color-1);
}

.section-item input[type="checkbox"] {
    width: 15px;
    height: 15px;
    accent-color: var(--accent-color);
    cursor: pointer;
    flex-shrink: 0;
}

.section-item-label {
    font-size: 0.84rem;
    color: var(--text-color-1);
    user-select: none;
}

/* ── TLP pills ── */
.tlp-pills {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
}

.tlp-pill {
    padding: 5px 8px;
    border-radius: 6px;
    border: 2px solid transparent;
    font-size: 0.75rem;
    font-weight: 700;
    font-family: inherit;
    letter-spacing: 0.06em;
    cursor: pointer;
    opacity: 0.55;
    transition: opacity 0.15s, border-color 0.15s;
}

.tlp-pill.tlp-active {
    opacity: 1;
    border-color: currentColor;
}

.tlp-pill:hover { opacity: 0.85; }

.tlp-white { background: #e8e8e8; color: #333; }
.tlp-green { background: #28a745; color: #fff; }
.tlp-amber { background: #fd7e14; color: #fff; }
.tlp-red   { background: #dc3545; color: #fff; }

/* ── Export buttons ── */
.export-btn-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.export-btn {
    padding: 9px 14px;
    border-radius: 7px;
    border: 1px solid var(--border-color);
    background: var(--background-color);
    color: var(--text-color-1);
    font-size: 0.84rem;
    font-family: inherit;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background 0.12s, border-color 0.12s;
    text-align: left;
}

.export-btn:hover {
    background: var(--main-color-1);
    border-color: var(--main-color-3);
}

.export-primary {
    background: var(--accent-color);
    color: #fff;
    border-color: var(--accent-color);
}

.export-primary:hover {
    background: #a8832c;
    border-color: #a8832c;
}

/* ── Right panel — preview ── */
.report-right-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: #f4f4f4;
}

.preview-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    border-bottom: 1px solid var(--border-color);
    background: var(--widget-background-color);
    min-height: 38px;
}

.preview-label {
    font-size: 0.77rem;
    font-weight: 600;
    color: var(--text-color-2);
    display: flex;
    align-items: center;
    gap: 6px;
}

.preview-loading {
    font-size: 0.77rem;
    color: var(--accent-color);
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.report-iframe {
    flex: 1;
    border: none;
    width: 100%;
    background: #fff;
}
```

- [ ] **Step 4: Manual end-to-end test**

1. Start the server: `python manage.py runserver 8765`
2. Log in as `lead_admin / admin`
3. Open any incident → Report tab
4. Verify: two-panel layout loads, preview populates within 1s
5. Toggle a section checkbox → preview updates after 400ms
6. Click TLP: RED → preview banner turns red
7. Click PDF → file downloads and opens as a styled PDF
8. Click Word → .docx downloads and opens correctly
9. Click Markdown → .md downloads with TLP header + sections
10. Click JSON → .json downloads with deep structure
11. Click CSV IoCs → .csv downloads with correct headers
12. Click HTML → .html downloads and opens correctly in browser

- [ ] **Step 5: Commit**

```bash
git add sharpcirt/views.py sharpcirt/templates/incidents/report.html sharpcirt/static/css/report.css
git commit -m "feat: report page — two-panel section picker + live preview + 6 export formats"
```

---

## Final verification checklist

After all tasks are complete:

- [ ] All 7 API endpoints return 200 (or the correct Content-Type for downloads)
- [ ] PDF renders without xhtml2pdf errors; TLP footer appears on every page
- [ ] Word .docx opens in LibreOffice/Word without corruption warnings
- [ ] Markdown has pipe-escaped IoC values
- [ ] JSON export includes `iocs`, `timeline`, `notes`, `tasks`, `impacts`, `responders` at root level
- [ ] CSV has correct 6-column header row
- [ ] HTML archive is self-contained (open it offline — styles load from inline `<style>`)
- [ ] Section toggle + TLP change each trigger a debounced preview refresh
- [ ] Tasks and Notes checkboxes start unchecked (spec requirement)
- [ ] No pdfkit import remains in views.py
- [ ] `python -m pytest sharpcirt/tests/test_report_generators.py -v` passes

---

## Rollback notes

If xhtml2pdf produces a broken PDF (blank pages, encoding errors):

1. Check that the template has no Django template tags that produce malformed HTML (e.g. `{{ None }}`)
2. xhtml2pdf doesn't support CSS Grid/Flex — the template only uses block + table layouts, so this shouldn't occur
3. Fallback: ship without the PDF footer (`{% if is_pdf %}` block) and confirm the bare PDF renders, then add the footer back

If python-docx throws `PackageNotFoundError`:

```bash
pip install --force-reinstall python-docx
```
