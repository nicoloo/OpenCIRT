# OpenCIRT — Feature Design Spec
**Date:** 2026-06-08  
**Features:** Home redesign · Create Incident · Invite flow · Settings page

---

## 1. Home Page Redesign

### Goal
Transform the home page into a high-density landing page that gives responders an instant overview of all their incidents.

### Layout (top → bottom)

#### 1a. Stats Bar
Five KPI chips in a single row:
- **Total Incidents** — count of all user incidents
- **Active** — count where status is OPEN or IN_PROGRESS
- **Critical** — count where severity is CRITICAL
- **Total IoCs Found** — sum of genericiocs across all user incidents
- **Avg TTD** — average time_to_detect across user incidents

#### 1b. Toolbar
Inline row containing:
- Text search input (filters incident cards live by name)
- Severity dropdown (All / Low / Medium / High / Critical)
- Status dropdown (All / Open / In Progress / Resolved / Closed)
- **"+ New Incident"** button (gold accent style, links to `/incident/create`)

#### 1c. Incident Card List
Replace raw `<table>` with styled card rows. Each card shows:
- Colored left border matching severity (Critical=red, High=orange, Medium=yellow, Low=green)
- Severity badge icon
- Incident name (bold)
- Status pill
- Created date
- IoC count chip
- Click anywhere → `/incident/<id>/overview`

Filtering is entirely client-side (JS `data-*` attributes on each card).

#### 1d. Charts Row
Three charts side by side, styled in the ochre palette:
- **Incidents over time** — stacked bar by severity (existing data, restyled)
- **Status distribution** — donut chart (existing data, restyled)
- **Severity distribution** — new donut chart

### Files changed
- `opencirt/templates/home.html` — full rewrite
- `opencirt/static/css/home.css` — new file
- `opencirt/views.py` — add severity_counts to home context

---

## 2. New Incident Creation Page

### Goal
Minimal form to open an incident fast. Creator automatically becomes Incident Lead.

### URL & View
- URL: `GET/POST /incident/create`
- View: `create_incident(request)`
- Template: `opencirt/templates/incidents/create_incident.html` (extends `base2.html`)

### Form Fields (minimal)
| Field | Type | Required | Default |
|-------|------|----------|---------|
| Name | text | yes | — |
| Description | textarea | no | '' |
| Severity | select | yes | MEDIUM |
| Start time | datetime-local | no | now() |
| Is public | checkbox | no | False |

### Server-side defaults for non-nullable model fields
- `ending_time = starting_time`
- `duration = timedelta(0)`
- `time_to_detect = timedelta(0)`
- `time_to_respond = timedelta(0)`
- `executive_summary = ''`
- `lessons_learned = ''`
- `technical_details = ''`

### Post-save flow
1. Create `Incident`
2. Create `UserRole(user=request.user, incident=incident, role='INCIDENT_LEAD', display_role='Incident Lead')`
3. Generate 6-digit `invite_code` (random, stored on the incident)
4. **Redirect to `/incident/<id>/invite`** — the invite screen (see §3b)

### Navbar wire-up
The "New incident" `<a href="#">` in `base2.html` is updated to `href="/incident/create"`.

---

## 3. Invite Flow Redesign

### 3a. Model Change
Add to `Incident`:
```python
invite_code = models.CharField(max_length=6, blank=True, default='')
```
Migration: `python manage.py makemigrations && migrate`

Helper: `generate_invite_code()` → `str(random.randint(100000, 999999))`

### 3b. Post-Creation Invite Screen
- URL: `GET /incident/<id>/invite`
- View: `incident_invite(request, id)`
- Template: `opencirt/templates/incidents/invite.html` (extends `base2.html`)
- **Access**: only the incident lead / logged-in users (no sidebar needed yet — standalone page)

**Page content:**
- Headline: "Incident created. Invite your team."
- Incident name subtitle
- Join URL displayed in a copyable input: `http://<host>/incident/<id>/join`
- 6-digit code in large spaced monospace display (e.g., `4 8 2 – 9 5 0`)
- QR code generated client-side via `qrcode.js` (CDN) encoding the join URL
- "Copy link" button
- "Regenerate code" button (calls `POST /api/incident/<id>/regenerate-invite/`)
- "Go to incident →" gold button → `/incident/<id>/overview`

### 3c. Updated Join Page (`/incident/<id>/join`)
Two paths:

**Not logged in:**
- Fields: Username, Password, 6-digit code
- Creates user account + validates code + creates `UserRole(role='READER')`

**Logged in:**
- Just the 6-digit code input
- Validates code + creates `UserRole(role='READER')` if not already a member

### 3d. Responders Page Invite Modal (update)
- Replace current share-link modal with the full invite UI (URL + code + QR code)
- Add "Regenerate code" button for incident leads

### 3e. New API Endpoint
`POST /api/incident/<id>/regenerate-invite/`
- Requires INCIDENT_LEAD role
- Generates new 6-digit code, saves, returns `{code: "482950"}`

### 3f. QR Code
Client-side only using `qrcode.js` from CDN:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
```
Renders into a `<div id="qrcode">`.

---

## 4. Settings Page

### Goal
App-level preferences for the logged-in user, distinct from the profile page (which handles name/picture/password).

### URL & View
- URL: `GET/POST /settings`
- View: `settings_view(request)`
- Template: `opencirt/templates/settings.html` (extends `base2.html`)
- Navbar: "Settings" link in `base2.html` (currently links to `/about`) → split into separate "Settings" and "About" entries

### Sections

#### Appearance
- Theme toggle: Light / Dark (wires to `user.light_mode` field)

#### Notifications *(UI only — stored as JSON preferences, no email backend yet)*
- Toggle: Email on new incident assignment
- Toggle: Email on @mention in chat

#### Platform Defaults
- Default severity when creating incidents (select)
- Default chart period (Last 7 days / 30 days / All time)

#### Security
- "Change password" link → `/profile_change_password`
- Last login display (read-only, from `user.last_connection_time`)

### Persistence
Add `preferences` field to `User`:
```python
preferences = models.JSONField(default=dict, blank=True)
```
One migration. Endpoint: `POST /api/update-settings/` saves theme + notification toggles + platform defaults into `user.preferences`.

---

## Implementation Order

1. Model migration (invite_code + preferences fields)
2. Home page redesign
3. Create Incident page
4. Post-creation invite screen
5. Updated join page (code validation)
6. Responders invite modal update
7. Settings page
8. Wire up all navbar links
9. Update `about.html` — move each feature to "Done ✓" as it ships

---

## Files Summary

| File | Action |
|------|--------|
| `opencirt/models.py` | Add `invite_code`, `preferences` to respective models |
| `opencirt/views.py` | Add `create_incident`, `incident_invite`, `settings_view`, `regenerate_invite`, update `join`/`welcome` |
| `opencirt/urls.py` | Add `/incident/create`, `/incident/<id>/invite`, `/settings`, `/api/.../regenerate-invite/` |
| `opencirt/templates/home.html` | Full rewrite |
| `opencirt/templates/incidents/create_incident.html` | New |
| `opencirt/templates/incidents/invite.html` | New |
| `opencirt/templates/incidents/join.html` | Update (add code field) |
| `opencirt/templates/incidents/responders.html` | Update invite modal |
| `opencirt/templates/settings.html` | New |
| `opencirt/static/css/home.css` | New |
| `opencirt/templates/base2.html` | Wire up "New incident" + "Settings" nav links |
