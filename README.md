# OpenCIRT — Incident Response Platform

OpenCIRT is an open-source platform for cybersecurity teams to manage the full incident response lifecycle.

## What it does

- **Incident management** — create and track incidents with severity, status, TLP classification, and timelines
- **Evidence collection** — log actions, attach files, and capture Indicators of Compromise (IOCs)
- **Collaborative investigation** — invite team members per incident with role-based access (Incident Lead, Analyst, Reader)
- **IOC enrichment** — cross-check indicators against external sources (VirusTotal, AbuseIPDB, MISP)
- **Report export** — generate stakeholder-ready reports in PDF or DOCX and more, with configurable sections
- **AI assistance** — optional Anthropic / OpenAI integration to help rephrase and summarize findings


## Tech stack

- **Backend:** Django 6, PostgreSQL
- **Server:** Gunicorn behind Nginx
- **Containerization:** Docker Compose

## Quick start (Docker)

```bash
# 1. Clone the repository
git clone <repo-url>
cd opencirt

# 2. Create your environment file
cp .env.example .env

# 3. Edit .env and set at minimum:
#    SECRET_KEY=<random string>
#    POSTGRES_PASSWORD=<password>
#    ALLOWED_HOSTS=localhost,127.0.0.1

# 4. Build and start
docker compose up --build

# 5. Open the app
# http://localhost:8080
# Admin panel: http://localhost:8080/admin/
# Default credentials: admin / admin
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | `change-me-in-production` | Django secret key |
| `POSTGRES_PASSWORD` | Yes | `opencirt` | Database password |
| `DEBUG` | No | `False` | Enable Django debug mode |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `ANTHROPIC_API_KEY` | No | — | AI rephrasing features |
| `OPENAI_API_KEY` | No | — | Alternative AI provider |
| `VIRUSTOTAL_API_KEY` | No | — | IOC enrichment |
| `ABUSEIPDB_API_KEY` | No | — | IP reputation lookups |


## Local development (without Docker)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```


## Contributing

Contributions, integrations, and feedback are welcome.