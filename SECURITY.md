# Security Policy

## Supported Versions

Only the latest release receives security fixes.

| Version | Supported |
| ------- | --------- |
| latest  | ✓         |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting — click **"Report a vulnerability"** on the [Security tab](https://github.com/nicoloo/OpenCIRT/security/advisories/new). Include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations

You can expect an acknowledgement within 72 hours and a fix timeline within 14 days for critical issues.

## Security Hardening for Production

Before deploying OpenCIRT in production:

1. **Set a strong `SECRET_KEY`** — at least 50 random characters. Never reuse the example value.
2. **Change the default admin password** immediately after first login. The initial password is printed during `migrate`.
3. **Use HTTPS** — place TLS certificates in `docker/certs/` and configure your domain in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
4. **Set `DEBUG=False`** in your `.env` file.
5. **Rotate API keys** — if any AI or CTI provider keys are compromised, replace them in `.env` and restart the stack.

See `.env.example` for the full list of required environment variables.
