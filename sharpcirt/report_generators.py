"""
Report generation helpers for OpenCIRT.

Keeps views.py thin: views parse the request and delegate to these functions.
All functions are pure (no Django request objects) so they're easy to test.
"""
from django.utils import timezone

_SENTINEL = 'SOME STRING'

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

VALID_TLP = ('WHITE', 'CLEAR', 'GREEN', 'AMBER', 'RED')

TLP_STYLES = {
    'WHITE': {'bg': '#e8e8e8', 'text': '#333333'},
    'CLEAR': {'bg': '#e8e8e8', 'text': '#333333'},
    'GREEN': {'bg': '#28a745', 'text': '#ffffff'},
    'AMBER': {'bg': '#fd7e14', 'text': '#ffffff'},
    'RED':   {'bg': '#dc3545', 'text': '#ffffff'},
}

TLP_DESCRIPTIONS = {
    'RED':   'Strictly limited to initial recipients. No further distribution outside this group.',
    'AMBER': 'Restricted sharing on a need-to-know basis within the organization and trusted partners.',
    'GREEN': 'May be shared within the security community or sector. Do not publish on the open internet.',
    'WHITE': 'No restrictions. Information may be freely shared and published publicly.',
    'CLEAR': 'No restrictions. Information may be freely shared and published publicly.',
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
    def _esc(s):
        """Escape pipe characters (and backticks) in Markdown table cell values."""
        return (s or '-').replace('|', '\\|').replace('`', "'")

    lines = []

    # Header
    tlp_desc = TLP_DESCRIPTIONS.get(tlp, '')
    lines += [
        f'> **TLP:{tlp}** — {tlp_desc}',
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
            lines.append(f'| {_esc(ur.user.username)} | {_esc(ur.user.displayname)} | {ur.get_role_display()} | {_esc(ur.display_role)} |')
        lines.append('')

    if 'timeline' in sections:
        lines += ['## Timeline', '']
        if not incident.actions.exists():
            lines += ['_No timeline events recorded._', '']
        else:
            for action in incident.actions.all().order_by('observed_at').select_related('created_by'):
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
            '| Type | Value | Status | Threat Intel | Description |',
            '|------|-------|--------|-------------|-------------|',
        ]
        if not incident.genericiocs.exists():
            lines.append('| — | _No IoCs recorded._ | — | — | — |')
        else:
            for ioc in incident.genericiocs.all():
                val  = _esc(ioc.value)
                desc = _esc(ioc.description)
                rep  = ioc.reputation
                if rep:
                    verdict = rep.get('status', 'unknown').upper()
                    vt = rep.get('vt') or {}
                    if vt.get('total'):
                        verdict += f" ({vt.get('malicious', 0)}/{vt['total']} engines)"
                else:
                    verdict = '—'
                lines.append(
                    f'| {ioc.get_type_display()} | {val} | {ioc.get_status_display()} | {verdict} | {desc} |'
                )
        lines.append('')

    if 'tasks' in sections:
        lines += [
            '## Tasks',
            '',
            '| Priority | Title | Status | Assignee |',
            '|----------|-------|--------|----------|',
        ]
        if not incident.tasks.exists():
            lines.append('| — | _No tasks recorded._ | — | — |')
        else:
            for task in incident.tasks.all().select_related('assignee'):
                assignee = task.assignee.username if task.assignee else '-'
                lines.append(f'| {task.priority} | {_esc(task.title)} | {task.status} | {_esc(assignee)} |')
        lines.append('')

    if 'notes' in sections:
        lines += ['## Notes', '']
        if not incident.notes.exists():
            lines += ['_No notes recorded._', '']
        else:
            for note in incident.notes.all().select_related('created_by'):
                author = note.created_by.username if note.created_by else 'Unknown'
                lines += [
                    f'### {note.name}',
                    f'*{author} — {note.created_at.strftime("%Y-%m-%d %H:%M")}*',
                    '',
                    note.text,
                    '',
                ]

    if 'lessons_learned' in sections:
        ll = incident.lessons_learned
        lines += [
            '## Lessons Learned',
            '',
            ll if ll and ll != _SENTINEL else '_No lessons learned recorded._',
            '',
        ]

    if 'technical_details' in sections:
        td = incident.technical_details
        lines += [
            '## Technical Details',
            '',
            td if td and td != _SENTINEL else '_No technical details recorded._',
            '',
        ]

    return '\n'.join(lines)


# ── Deep JSON serialiser ─────────────────────────────────────────────────────

def generate_deep_json(incident, generated_by, tlp='AMBER'):
    """
    Build a deep JSON-serialisable dict for the incident.
    Always exports all sections — the section picker does not apply.
    tlp: one of 'WHITE', 'GREEN', 'AMBER', 'RED'. Defaults to 'AMBER'.
    """

    def fmt_dt(dt):
        return dt.isoformat() if dt else None

    def fmt_td(td):
        return str(td) if td else None

    return {
        'exported_at': timezone.now().isoformat(),
        'exported_by': generated_by,
        'tlp': tlp,
        'tlp_description': TLP_DESCRIPTIONS.get(tlp, ''),
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
                'threat_intel': {
                    'verdict':     ioc.reputation.get('status'),
                    'checked_at':  ioc.reputation.get('checked_at'),
                    'summary':     ioc.reputation_summary,
                    'details':     ioc.reputation.get('vt'),
                } if ioc.reputation else None,
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
