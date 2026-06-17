# OpenCIRT — Incident Response Platform

OpenCIRT is an open-source platform for cybersecurity teams to manage the full incident response lifecycle.

---

![OpenCIRT overview](docs/screenshot.png)

---

## Features

- **Incident management** — track incidents with severity, status, TLP classification, and timelines
- **Evidence collection** — log actions, attach files, and capture IOCs
- **Collaborative investigation** — role-based access per incident (Lead, Analyst, Reader)
- **IOC enrichment** — VirusTotal, AbuseIPDB, MISP integration
- **Report export** — PDF / DOCX with configurable sections
- **AI assistance** — optional Anthropic / OpenAI integration

## Quick start (pre-built image)

No source clone or local build needed — pulls the latest published image from GitHub Container Registry.

```bash
# 1. Download the two files you need
curl -O https://raw.githubusercontent.com/nicoloo/OpenCIRT/master/docker-compose.prod.yml
curl --create-dirs -O --output-dir docker https://raw.githubusercontent.com/nicoloo/OpenCIRT/master/docker/nginx-http.conf

# 2. Create your .env
curl -O https://raw.githubusercontent.com/nicoloo/OpenCIRT/master/.env.example
cp .env.example .env
# Edit .env: set SECRET_KEY and POSTGRES_PASSWORD

# 3. Start
docker compose -f docker-compose.prod.yml up -d
```

Open [http://localhost](http://localhost) — username `admin`, password printed in the container logs on first start.

> **Demo data:** set `LOAD_DEMO_DATA=true` in `.env` before the first `docker compose` to load sample incidents automatically.

### HTTPS / production (TLS)

The quick-start uses `nginx-http.conf` (HTTP only, port 80) so it works without any certificates.

For a production deployment with TLS:

1. Place your certificates in `docker/certs/`: `fullchain.pem` and `privkey.pem`.
2. In `docker-compose.prod.yml`, replace the nginx volume mount:
   ```yaml
   - ./docker/nginx-http.conf:/etc/nginx/conf.d/default.conf:ro
   ```
   with:
   ```yaml
   - ./docker/nginx.conf:/etc/nginx/conf.d/default.conf:ro
   - ./docker/certs:/etc/nginx/certs:ro
   ```
3. Also add `- "443:443"` under `ports` for the frontend service.
4. Restart: `docker compose -f docker-compose.prod.yml up -d`

### Pinning a specific version

```bash
# Pin to a specific release — edit docker-compose.prod.yml and change:
#   image: ghcr.io/nicoloo/opencirt:latest
# to:
#   image: ghcr.io/nicoloo/opencirt:1.2.3
```

Available tags: `latest`, `sha-<commit>`, and semver tags (`1.2.3`, `1.2`, `1`) for each [release](https://github.com/nicoloo/OpenCIRT/releases).

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `ALLOWED_HOSTS` | No | Comma-separated allowed hosts (default: `localhost,127.0.0.1`) |
| `LOAD_DEMO_DATA` | No | Set to `true` to seed sample incidents on first migrate |
| `ANTHROPIC_API_KEY` | No | AI rephrasing features |
| `OPENAI_API_KEY` | No | Alternative AI provider |
| `VIRUSTOTAL_API_KEY` | No | IOC enrichment |
| `ABUSEIPDB_API_KEY` | No | IP reputation lookups |

## Development / build from source

```bash
git clone https://github.com/nicoloo/OpenCIRT.git
cd OpenCIRT
cp .env.example .env
# Edit .env: set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

## Contributing

Contributions, integrations, and feedback are welcome. See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

---

Made by [@nicoloo](https://github.com/nicoloo)
