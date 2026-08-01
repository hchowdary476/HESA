# 🛡️ Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The HESA (JARVIS) development team takes security and user privacy seriously. If you discover a security vulnerability within this repository, please do **NOT** open a public GitHub issue.

### Disclosure Process
1. Email your report privately to `security@open-jarvis.org` or report via GitHub Security Advisories.
2. Include a detailed description of the vulnerability, steps to reproduce, and potential security impact.
3. The project maintainers will acknowledge receipt within 48 hours and provide periodic updates until a fix is deployed.

### Security Best Practices for Users
- Never commit your `.env` file or raw API keys to public version control.
- Use `JARVIS_PRIVACY_MODE=true` when executing in sensitive environments.
- Maintain restrictive permissions on local SQLite database files and Fernet key stores.
