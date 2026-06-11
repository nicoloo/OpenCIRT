---
name: project-context
description: OpenCIRT project description, goals, and recommended codebase structure — background context for all development work
---

# OpenCIRT — Incident Response Platform

OpenCIRT is an open-source application for incident response used by cybersecurity teams. Its primary goal is to streamline the incident response lifecycle by providing a lightweight, purpose-built workspace for:

- Collecting and centralizing incident data and evidence.
- Capturing and managing Indicators of Compromise (IOCs).
- Cross-checking and enriching indicators across sources.
- Supporting analyst-driven investigation and collaborative analysis.
- Producing a complete incident report suitable for stakeholders.

The platform focuses on practical workflows: rapid evidence capture, flexible action items and timelines, tagging and correlation of indicators, and exportable reporting. Case management is a possible future enhancement to support multi-stage investigations, longer-running cases, and richer audit trails.

Goals:

- Reduce friction for responders during evidence collection and triage.
- Improve indicator validation and reuse across incidents.
- Provide clear, stakeholder-ready reporting outputs.
- Remain extensible and integrable with other tools (MISP, Jira, Defender, etc.).

This project is intended to be community-friendly and extendable — contributions, integrations, and feedback are welcome.

## Recommended Project Structure

This is the target layout as we rename and refactor to `opencirt`:

- `opencirt/` — Django app (models, views, urls, templates, static)
  - `migrations/` — Django migrations (update app labels when renaming)
  - `templates/` — HTML templates, organized by feature
  - `static/` — CSS, JS, images; include `css/variables.css` for theme
  - `fixtures/` — JSON fixtures (update model labels to `opencirt.<model>`)
  - `media/` — uploaded files (profile pics, images)
- `crud/` — Django project settings and root URLs
- `docs/` — Documentation and integration READMEs (MISP, Jira, Defender)
- `scripts/` — helper scripts (db export, import, fixture tools)
- `tests/` — higher-level test suites (optional; keep app tests in app)
- `requirements.txt` — pinned Python dependencies
- `.claude/skills/` — Claude Code skills for this project

## Renaming `opencirt` → `opencirt`

When completing the rename:

- Update all internal imports, `AppConfig.name`, and migration app labels
- Search/replace `opencirt` → `opencirt` in code, templates, fixtures, and migration files
- Update `crud/settings.py`: add `opencirt` to `INSTALLED_APPS`, set `AUTH_USER_MODEL = 'opencirt.User'`
- Run `python manage.py makemigrations` and `python manage.py migrate` on a safe branch
- If migrations reference the old label, update tuples (e.g. `('opencirt', '0001_initial')` → `('opencirt', '0001_initial')`)
