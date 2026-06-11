# OpenCIRT — Report & Export System Design
**Date:** 2026-06-09
**Feature:** Report page redesign with section picker, live preview, and multi-format export

---

## 1. Goal

Transform the report page into a fully-featured incident reporting hub. An analyst configures which sections to include, picks a TLP classification, previews the report live, and exports to any of six formats in one click.

Reporting is a primary deliverable of the platform — the output goes to CISOs, regulators, legal teams, and threat intel platforms.

---

## 2. Page Layout

Two-panel layout inside the existing `incidents/base.html` sidebar.

### Left panel (~300px, fixed)

**Section picker** — checkboxes, evaluated top-to-bottom in the rendered report:

| Section | Default |
|---|---|
| Executive Summary | ✅ on |
| Incident Metadata | ✅ on |
| Responders | ✅ on |
| Timeline | ✅ on |
| IoC / Evidence | ✅ on |
| Tasks | ☐ off |
| Notes | ☐ off |
| Lessons Learned | ✅ on |
| Technical Details | ✅ on |

**TLP classification** — pill selector (one active at a time):
- `WHITE` — public
- `GREEN` — community
- `AMBER` — restricted (default)
- `RED` — named recipients only

Each TLP level has a distinct background color in the pill and in the report header/footer.

**Export buttons** — clicking any button immediately POSTs the current section selection and TLP, triggering a download:

| Button | Format | Library |
|---|---|---|
| 📄 PDF | `.pdf` | xhtml2pdf (pure Python) |
| 📝 Word | `.docx` | python-docx |
| 📋 Markdown | `.md` | string render |
| `{}` JSON | `.json` | Python json |
| 📊 CSV | `.csv` | Python csv |
| 🌐 HTML | `.html` | same template as preview |

PDF button is gold (primary action). Others are secondary style.

### Right panel (flex-1)

Live preview `<iframe>` rendered server-side. Updates 400ms after any section checkbox toggle or TLP change (debounced). Shows a subtle loading overlay during re-fetch. Uses `srcdoc` attribute to avoid a separate browser navigation.

---

## 3. Architecture

### One template, three renderers

```
opencirt/templates/reports/report_template.html
    ↓  rendered with context {incident, sections: set[str], tlp: str}
    ├── GET  /api/<id>/report-preview/    → HTML string → iframe srcdoc
    ├── POST /api/<id>/download-pdf/      → xhtml2pdf → .pdf download
    └── POST /api/<id>/download-html/     → same HTML → .html archive download
```

Markdown and Word are generated programmatically (not from the HTML template) but from the same incident data.

### Template structure

`report_template.html` uses Django `{% if 'section_key' in sections %}` guards for each block. A `@media print` / `@page` CSS block handles PDF-specific layout (margins, page breaks, no sidebar chrome).

Cover page is always rendered (not toggleable).

### PDF library

Switch from `wkhtmltopdf` (hardcoded Windows path, external binary) to `xhtml2pdf` (`from xhtml2pdf import pisa` — already imported in `views.py`). PDF options: A4, UTF-8, TLP footer on every page.

### Word generation

`python-docx` generates the `.docx` programmatically:
- `Heading 1` for cover / section titles
- `Normal` paragraph style for prose fields
- `Table` for IoC list, responders, tasks
- Bold label + value for metadata rows

### JSON export (enhanced)

Current implementation uses shallow `model_to_dict`. Replace with a deep serializer:
```json
{
  "incident": { all fields },
  "tlp": "AMBER",
  "exported_at": "...",
  "exported_by": "username",
  "responders": [ {username, role, display_role} ],
  "iocs": [ {type, value, status, description, tags, created_at, linked_actions} ],
  "timeline": [ {type, title, description, observed_at, starting_time, ending_time, tags, iocs} ],
  "notes": [ {name, text, created_by, created_at} ],
  "tasks": [ {title, priority, status, assignee, description} ],
  "impacts": [ {title, severity, status, type, description} ]
}
```
JSON always exports all sections regardless of the section picker.

### CSV export

IoC list only. Columns: `type, value, status, description, created_at, linked_actions`
Always full — section picker does not affect it.

---

## 4. Report Content Per Section

### Cover (always present)
- Incident name (large)
- Severity badge (colored)
- TLP classification badge
- Status
- Generated: `<date>` by `<username>`
- Incident ID

### Executive Summary
`incident.executive_summary` prose, full width.

### Incident Metadata
Two-column definition list:
- Severity, Status, Public/Private
- Start time, End time, Duration
- Time to detect (TTD), Time to respond (TTR)
- Created by, Created at

### Responders
Table: Avatar initial · Username · Display Name · Role · Display Role

### Timeline
Chronological list. Each action:
- Timestamp (observed_at or starting→ending)
- Type badge (Malicious / Defensive / Mitigation / etc.)
- Title (bold)
- Description
- Linked IoC chips (if any)

### IoC / Evidence
Table: Type · Value · Status · Description · Linked Actions

### Tasks
Table: Priority · Title · Status · Assignee · Description

### Notes
Each note as a card: title, author, date, body text.

### Lessons Learned
`incident.lessons_learned` prose, full width.

### Technical Details
`incident.technical_details` prose, full width. Monospace font for code-like content.

---

## 5. TLP Branding

| Level | Color | Usage |
|---|---|---|
| WHITE | `#f0f0f0` / dark text | Public release |
| GREEN | `#28a745` / white text | Community sharing |
| AMBER | `#fd7e14` / white text | Restricted |
| RED | `#dc3545` / white text | Named recipients only |

Appears in:
- Cover page: large badge top-right
- PDF: every page footer via `@page` CSS (`content: "TLP:<level>"`)
- Markdown: first line `> **TLP:<level>**`
- JSON: root-level `"tlp"` field
- HTML archive: sticky banner at top of page

---

## 6. New API Endpoints

| Method | URL | Action |
|---|---|---|
| GET | `/api/incident/<id>/report-preview/` | Returns HTML for iframe. Query params: `sections` (comma-separated), `tlp` |
| POST | `/api/incident/<id>/download-pdf/` | Body: `sections`, `tlp` → .pdf |
| POST | `/api/incident/<id>/download-word/` | Body: `sections`, `tlp` → .docx |
| POST | `/api/incident/<id>/download-markdown/` | Body: `sections`, `tlp` → .md |
| GET  | `/api/incident/<id>/download-json/` | No params needed → full deep .json |
| GET  | `/api/incident/<id>/download-csv/` | No params needed → IoC .csv |
| POST | `/api/incident/<id>/download-html/` | Body: `sections`, `tlp` → .html |

Existing endpoints `download_incident_pdf`, `download_incident_markdown`, `download_incident_json` are replaced.

---

## 7. Files Changed

| File | Action |
|---|---|
| `opencirt/templates/incidents/report.html` | Full rewrite — section picker + live preview pane |
| `opencirt/templates/reports/report_template.html` | New — unified HTML report template |
| `opencirt/static/css/report.css` | Full rewrite — two-panel layout + print CSS |
| `opencirt/views.py` | Add `report_preview`, `download_word`, `download_csv`, `download_html`; replace PDF/MD/JSON views |
| `opencirt/urls.py` | Add new endpoints, replace old ones |
| `requirements.txt` | Add `python-docx` |

---

## 8. Dependencies

| Library | Use | Status |
|---|---|---|
| `xhtml2pdf` | PDF generation | Already in `views.py` import |
| `python-docx` | Word (.docx) | Needs `pip install python-docx` |
| `python csv` | CSV export | stdlib, no install |

`wkhtmltopdf` / `pdfkit` are removed from the PDF path.

---

## 9. Out of Scope (future)

- MISP-compatible JSON export
- STIX 2.1 export
- Saved report configurations (per-incident defaults)
- Scheduled/automated report generation
- Email delivery of reports
