# OpenCIRT — Frontend Guidelines

Design system reference for all developers working on templates.

---

## Colours (CSS variables — `variables.css`)

| Variable | Value | Role |
|---|---|---|
| `--main-color-1` | `#f5e8cc` | very light ochre / cream |
| `--main-color-2` | `#e8cc8e` | soft golden ochre |
| `--main-color-3` | `#c49840` | accent ochre |
| `--accent-color` | `#c49840` | same as main-color-3, used on CTAs |
| `--background-color` | `#fdfaf3` | page background |
| `--widget-background-color` | `#faf4e5` | card / widget background |
| `--sidebar-bg` | `#f5ebd0` | sidebar background |
| `--border-color` | `#e5d0a0` | border, input outlines |
| `--text-color-1` | `#0f2b3a` | primary text (dark slate) |
| `--text-color-2` | `#5b6b76` | secondary / muted text |

Never hard-code hex colours in templates. Always use the CSS variables above.

---

## Buttons

All buttons use the `.btn` class defined in `style.css` (incident pages) and `new_style.css` (top-level pages).

### Base style — `.btn`

```css
.btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: linear-gradient(to right, var(--main-color-1), var(--main-color-2));
    border: 1px solid var(--border-color);
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-color-1);
    font-family: inherit;
    white-space: nowrap;
    transition: background 0.15s, border-color 0.15s;
}
.btn:hover  { background: var(--main-color-2); border-color: var(--main-color-3); }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
```

### Modifier classes

| Class | Use-case |
|---|---|
| `.btn` (alone) | Default action — add item, open modal, etc. |
| `.btn .btn-primary` | Primary / save action (ochre solid) |
| `.btn .btn-danger` | Destructive action (red) |
| `.btn .btn-sm` | Smaller size — used in table rows |
| `.btn .btn-icon` | Icon-only button — transparent background |

### Usage rules

- **Always use `class="btn"`** as the base class. Never write `style="background: …"` on a button.
- Add a modifier class for semantic meaning (`.btn-danger` for delete, `.btn-primary` for save).
- For full-width buttons in a sidebar, add `style="width:100%"` inline (acceptable exception).
- Do not invent new button classes — extend this list if a new variant is needed.

### Examples

```html
<!-- Default action -->
<button class="btn" id="addIocBtn" style="width:100%;">+ Add IoC</button>

<!-- Invite / modal opener -->
<button class="btn" id="invite-btn">
    <i class="fa-solid fa-user-plus"></i> Invite Responders
</button>

<!-- Destructive (in table row) -->
<button class="btn btn-sm btn-danger btn-icon delete-btn" title="Delete">
    <i class="fas fa-trash-alt"></i>
</button>

<!-- Save / submit -->
<button class="btn btn-primary" type="submit">Save Changes</button>
```

---

## Page templates

### Incident pages

Extend `incidents/base.html`. This base provides:
- Left sidebar with incident navigation
- `<main class="main-content">` area for page content
- Global CSS: `variables.css` + `style.css` (includes `.btn`)
- Floating chat panel

```django
{% extends 'incidents/base.html' %}
{% block styles %}
    <!-- page-specific CSS only -->
{% endblock %}
{% block content %}
    <!-- page content -->
{% endblock %}
```

### Top-level pages (home, profile, about)

Extend `base2.html`. This base provides:
- Top header with logo and nav
- Global CSS: `variables.css` + `new_style.css` (includes `.btn`)

```django
{% extends 'base2.html' %}
{% block content %}
    <!-- page content -->
{% endblock %}
```

---

## Layout components

### `.main-frame`

Two-column layout: main content + sidebar.

```html
<div class="main-frame">
    <div class="info-container"><!-- table or main content --></div>
    <aside class="sidebar"><!-- widgets + action buttons --></aside>
</div>
```

### `.widget`

Card / panel component used in sidebars and dashboards.

```html
<div class="widget kpi">
    <h3>IoCs</h3>
    <p class="h4">Total</p>
    <p class="KPI-value">42</p>
</div>
```

### `.incident-table`

Standard table style for listing items.

```html
<table class="incident-table">
    <thead><tr><th>Column</th></tr></thead>
    <tbody>...</tbody>
</table>
```

---

## Anti-patterns to avoid

- ❌ Hard-coded hex colours (`color: #333`, `background: white`)
- ❌ Inline `style` on buttons (except `width: 100%` in sidebars)
- ❌ Separate base templates per page — always use `incidents/base.html` or `base2.html`
- ❌ Loading jQuery / DataTables unless the page actually uses them
- ❌ Custom `.btn-*` variants not listed in this document
