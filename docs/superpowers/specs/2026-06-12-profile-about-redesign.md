# Profile & About Page Redesign

**Date:** 2026-06-12
**Branch:** feature/profile-about-redesign

## Goal

Refactor the profile and about pages to match the established design system (ochre palette, `settings-section` / `settings-row` pattern, `base2.html` topbar layout).

## Profile Page

**Layout:** Option B — avatar card hero + grouped sections below.

### Avatar card
- Large letter avatar (first letter of username) using `var(--main-color-2)` background
- Display name + username + email in a single hero card
- "Change photo" button (triggers file input) — keeps existing upload behaviour

### Sections (settings-section / settings-row pattern)
| Section | Fields |
|---------|--------|
| Account | Username, Display name, Email |
| Appearance | Theme selector (Light / Dark) |
| Security | Change password — inline expandable rows |

### Behaviour
- Single `<form>` POSTs to `update_profile`
- Password section hidden by default, toggled with JS (fix current double-display:none bug)
- Save button bottom-right, accent colour

## About Page

**Layout:** Single "Roadmap" page — no "Done" section.

### Sections
| Section | Items |
|---------|-------|
| In progress | Grouped by: Access & Security, Incidents & Data, Integrations |
| Future | Ungrouped list |

### Items removed (done)
- Remove the former `/` page → `/home` redirect
- Write GitHub workflows for CI/CD
- Operationalize through Docker
- Audit trail
- JSON / CSV / PDF / Word / HTML / Markdown export
- Demo fixtures (3 realistic incident scenarios)
- MISP integration
- Refactor profile page (this task)

### Items kept in "In progress"
- Proper RBAC
- Dark / Light mode (toggle exists, not yet active)
- Email notifications (SMTP config)
- Tags on incidents
- Homepage timechart timeframe toggle
- Download all IoCs in MISP-importable format
- Jira / Microsoft Defender integration stubs

### Future
- Share IoCs between incidents
- Import tasks playbook
- Documentation and README for integrations

## Out of scope
- Dark mode implementation
- New logo (separate task, pending new asset)
- Two-tone CSS wordmark in topbar/login (deferred until new logo is ready)
