# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The HESA (JARVIS) team takes security seriously. If you discover a security vulnerability within this repository, please do **NOT** open a public issue.

### Disclosure Process
1. Email your findings to security@open-jarvis.org (or report via GitHub Security Advisories).
2. Include a detailed description of the vulnerability, steps to reproduce, and potential impact.
3. The project maintainers will acknowledge receipt within 48 hours and provide updates on resolution.

### Security Best Practices for Users
- Never commit your `.env` file or raw API keys to public repositories.
- Use `JARVIS_PRIVACY_MODE=true` when running in sensitive environments.
- Maintain key permissions on your localized SQLite and Fernet key stores.
