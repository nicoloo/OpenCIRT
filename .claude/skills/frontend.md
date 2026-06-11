---
name: frontend
description: Guidelines for working with the OpenCIRT frontend — Django templates, CSS variables, theming, and vanilla JS/jQuery patterns
---

# OpenCIRT Frontend

## Stack
- **Templates**: Django template language (DTL) — no React/Vue. All HTML in `opencirt/templates/`
- **CSS**: Custom modular CSS with CSS variables in `static/css/variables.css`. Light/dark mode via `light_mode.css` / `dark_mode.css`
- **JS**: Vanilla JS + jQuery 3.6 + DataTables 1.12.1. No build step — plain `.js` files in `static/js/`
- **Icons**: Font Awesome 6.0.0-beta3 (CDN)

## Adding a New Page
1. Create `opencirt/templates/<feature>.html` extending `base.html` or `incidents/base.html`
2. Add a view in `opencirt/views.py`
3. Register the URL in `opencirt/urls.py`
4. If it needs new styles, add `opencirt/static/css/<feature>.css` and load it in the template with `{% load static %}`

## CSS Conventions
- Use CSS variables from `variables.css` — never hardcode colors or spacing
- Theme classes: `light-mode` / `dark-mode` applied at the `<body>` level by JS
- Each feature has its own CSS file (`timeline.css`, `tasks.css`, `iocs.css`, etc.)
- New variables go in `variables.css`, not inline

## Template Layout
- `base.html` — global layout (sidebar, nav) for top-level pages
- `base2.html` — alternate base without sidebar (check before adding a third layout)
- `incidents/base.html` — incident detail layout with tabs (Overview, Timeline, IOCs, Tasks…)
- Always `{% load static %}` at the top and use `{% static 'css/...' %}` for asset paths
- Modals are scaffolded in the base templates — add new modal HTML inside the base `{% block modals %}` if needed

## JS Conventions
- jQuery is globally available as `$`
- Keep feature JS in its own file (`timeline.js`, `chat.js`, etc.) — don't add logic to `base.html`
- API calls use `fetch()` with the CSRF token in the `X-CSRFToken` header

## CSRF in AJAX
```js
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
fetch('/api/endpoint/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': csrfToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

## DataTables
Tables use DataTables 1.12.1. Initialize with `$('#myTable').DataTable({ ... })` in the page's JS file. Avoid reinitializing on the same element.

## Dark/Light Mode
User preference is stored on the `User` model (`light_mode` boolean). The `<body>` class is set server-side in the base template. CSS uses `.light-mode` / `.dark-mode` selectors from `light_mode.css` and `dark_mode.css`.
