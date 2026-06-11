# Docker Compose Runbook

This repository now ships with a Docker-based deployment split into three services:

- `backend`: Django + Gunicorn application server
- `frontend`: Nginx reverse proxy that serves static/media files and forwards dynamic requests to Django
- `db`: PostgreSQL database

## What you need

- Docker Desktop or Docker Engine with Compose v2
- Git
- A shell capable of running the commands below

## Files added for containerized deployment

- `Dockerfile` builds the Django backend image
- `docker-compose.yml` defines backend, frontend, and database services
- `docker/nginx.conf` configures Nginx as the public entrypoint
- `.env.example` lists the environment variables you should set

## First-time setup

1. Clone the repository.
2. Create your environment file:

```bash
cp .env.example .env
```

3. Edit `.env` and set at least:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `ALLOWED_HOSTS`

4. Build and start the stack:

```bash
docker compose up --build
```

5. Open the app in your browser:

```text
http://localhost:8080
```

## How the stack works

- Nginx listens on port `8080` on your machine and proxies application traffic to Django.
- Django runs in the `backend` container on port `8000`.
- PostgreSQL persists data in the `postgres_data` Docker volume.
- Static files are collected into a shared `static_volume` and served by Nginx.
- Uploaded media is stored in a shared `media_volume` and served by Nginx.

## Daily usage

Start the app:

```bash
docker compose up -d
```

See logs:

```bash
docker compose logs -f backend
```

Run Django management commands inside the backend container:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py migrate
```

Stop the app:

```bash
docker compose down
```

Remove everything, including database data and uploaded files:

```bash
docker compose down -v
```

## Accessing the application

- Public web app: `http://localhost:8080`
- Admin interface: `http://localhost:8080/admin/`

## Environment variables

Required:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`

Recommended:

- `DEBUG=False`
- `ALLOWED_HOSTS=localhost,127.0.0.1`

Optional integration keys:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `VIRUSTOTAL_API_KEY`
- `ABUSEIPDB_API_KEY`

## Notes

- The backend container automatically runs `migrate` and `collectstatic` on startup.
- The local development SQLite database is still supported when you run Django directly outside Docker.
- If you change templates or static assets, rebuild or restart the stack so Nginx serves the latest collected files.
- The default admin account is seeded as `admin / admin` during migration.
