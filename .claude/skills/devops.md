---
name: devops
description: Running, building, and debugging OpenCIRT locally and in Docker — environment setup, common failure modes, and CI pipeline reference
---

# OpenCIRT DevOps Reference

## Local Dev Server (no Docker)

Requires **Python 3.12** (Django 6.0 minimum). Uses SQLite by default.

```powershell
# First time
py -3.12 -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python manage.py migrate
.\venv\Scripts\python manage.py runserver
```

App runs at http://localhost:8000. Default admin: `admin` / `admin` (seeded by migration 0014).

## Docker Compose (full stack)

Requires Docker Desktop with **WSL2 kernel** installed.
- If Docker Desktop is stuck on "Starting Docker Engine": run `wsl --update` as Administrator, or download the kernel MSI manually from `https://aka.ms/wsl2kernel`.
- If `wsl --version` fails: install WSL from the Microsoft Store (newer version that supports `--version`).

```powershell
docker compose up --build   # full rebuild
docker compose up           # start without rebuilding
docker compose down -v      # tear down including volumes
```

App runs at http://localhost:8080 (nginx → gunicorn on 8000).

### Stack services
| Service  | Image              | Role                          |
|----------|--------------------|-------------------------------|
| db       | postgres:16-alpine | PostgreSQL database            |
| backend  | local build        | Django + gunicorn on port 8000 |
| frontend | nginx:1.27-alpine  | Reverse proxy + static files   |

### Startup order
`db` healthy → `backend` healthy (TCP :8000) → `frontend` starts.
The backend healthcheck (`docker inspect --format='{{.State.Health.Status}}'`) polls every 10s, up to 10 retries, with a 30s start_period.

## Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No pyvenv.cfg file` | System Python used instead of venv | Use `.\venv\Scripts\python` or activate venv first |
| `Django<7.0,>=6.0` not found | Python < 3.12 | Install Python 3.12 and recreate venv |
| `exec /app/docker/entrypoint.sh: no such file or directory` | CRLF line endings in entrypoint.sh | `.gitattributes` sets `*.sh eol=lf`; re-clone or run dos2unix |
| `host not found in upstream "backend:8000"` | nginx started before gunicorn was ready | `depends_on: backend: condition: service_healthy` is set |
| Exit code 137 in CI `makemigrations` | Container not yet healthy when exec runs | CI wait loop polls `docker inspect` health status before proceeding |
| `no such column: external_reference` on migrate | Fixture loaded before column existed | Fixture load moved to migration 0016 (after column is added) |

## Adding a Migration

Always generate inside the container so the DB dialect and Python version match production:

```powershell
docker compose exec -T backend python manage.py makemigrations
```

Then verify nothing is missing:

```powershell
docker compose exec -T backend python manage.py makemigrations --check --dry-run
```

Copy the generated file out if you need it locally (it's in the bind-mounted source).

## CI Pipeline (`.github/workflows/ci.yml`)

Steps in order:
1. `docker compose config` — validate compose syntax
2. `docker compose build` — build images
3. `docker compose up -d` — start stack
4. **Wait loop** — polls `docker inspect` health on backend, up to 40 × 5s = 3 min
5. `python manage.py check` — Django system checks
6. `python manage.py makemigrations --check --dry-run` — no missing migrations
7. `pytest` — unit tests
8. `docker compose down -v` — teardown (always runs)

If the wait loop times out it dumps `docker compose logs backend` before failing.

## Static Files

Static files are collected at build time (`collectstatic`) into the `static_volume` shared between backend and frontend. **After any CSS/JS/template change you must rebuild** to update the served files:

```powershell
docker compose up --build
```

In local dev mode (`DEBUG=True`) Django serves static files directly from source — no rebuild needed.
