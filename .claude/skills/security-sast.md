---
name: security-sast
description: SAST checklist for OpenCIRT — Django-specific security review covering auth, input validation, file uploads, XSS, and open redirects
---

# OpenCIRT Security (SAST)

## Known Issues to Address

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | Open redirect — `next` param not validated in login | `views.py` `custom_login` | Medium |
| 2 | File upload: extension check only, no MIME type validation | `views.py` `update_profile` | Medium |
| 3 | Redundant `User.objects.get()` before `authenticate()` — leaks user existence | `views.py` `custom_login` | Low |
| 4 | Missing `select_related`/`prefetch_related` in list views — N+1 queries | Various views | Low |
| 5 | No rate limiting on login or API endpoints | `urls.py` + views | Medium |

## SAST Checklist for New Code

### Authentication & Authorization
- [ ] All non-public views protected by `@login_required` or custom decorators
- [ ] Role checks use `@user_is_incident_responder` or `@verify_permissions(role)` from `utils.py`
- [ ] Redirect targets (`next=`, `redirect_to=`) validated with Django's `url_has_allowed_host_and_scheme()`
- [ ] No `User.objects.get()` before `authenticate()` — use `authenticate()` exclusively

### Input Validation
- [ ] JSON body parsed inside `try/except json.JSONDecodeError`
- [ ] Required POST fields checked before use — avoid bare `.POST['key']` (raises KeyError)
- [ ] IOC values validated/sanitized before save (type matches value format)
- [ ] No `eval()`, `exec()`, or subprocess calls with user-controlled input

### File Uploads
- [ ] Validate MIME type using `python-magic` or `imghdr`, not just file extension
- [ ] Rename uploaded files server-side — never trust the user-supplied filename
- [ ] Store uploads under `MEDIA_ROOT` only; never serve from `BASE_DIR`
- [ ] Restrict allowed extensions AND MIME types explicitly

### Database
- [ ] Use Django ORM only — no raw SQL with string formatting (`cursor.execute(f"...")` is forbidden)
- [ ] Add `select_related()` for FK lookups, `prefetch_related()` for M2M in list views
- [ ] Avoid `get_or_create` in concurrent request contexts without unique constraints

### Templates / XSS
- [ ] Never use `{{ value | safe }}` on user-supplied content
- [ ] User-controlled data rendered in `<script>` blocks must be JSON-encoded: `{{ value | json_script:"id" }}`
- [ ] Sensitive data not leaked into template context unnecessarily

### API Endpoints
- [ ] All POST/PUT/DELETE views have CSRF validation (automatic for Django views, check if DRF is added)
- [ ] Unauthorized access returns 403, not 404 — don't leak resource existence via status code
- [ ] `JsonResponse` used for API responses, not `HttpResponse` with manual JSON

## Quick Scan Commands
```bash
# Potential open redirects
grep -n "redirect(request.GET\|redirect(request.POST" opencirt/views.py

# Raw SQL
grep -n "\.raw(\|cursor\.\|execute(" opencirt/views.py

# Unsafe template rendering
grep -rn "| safe" opencirt/templates/

# Views missing auth decorator
grep -n "^def \|^@" opencirt/views.py | grep -v "login_required\|csrf"

# File extension checks (look for missing MIME validation nearby)
grep -n "\.endswith\|split('.')" opencirt/views.py
```

## Fix Patterns

### Open Redirect (login)
```python
from django.utils.http import url_has_allowed_host_and_scheme

next_url = request.GET.get('next', '')
if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
    return redirect(next_url)
return redirect('index')
```

### File Upload MIME Validation
```python
import imghdr

def is_valid_image(file):
    allowed_types = {'jpeg', 'png'}
    img_type = imghdr.what(file)
    return img_type in allowed_types
```
