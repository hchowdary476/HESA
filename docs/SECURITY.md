# 🛡️ HESA Security Policy & Architecture

Security is a foundational pillar of HESA. This document details our threat model, encryption standards, permission framework, and vulnerability reporting procedures.

---

## 🔒 Core Security Principles

1. **Zero Raw Secret Exposure**: API keys and tokens are loaded strictly via environment variables (`.env`) or stored using Fernet AES-128 key encryption (`security_shield.key`).
2. **Local Path Protection**: Path traversal checks prevent system file manipulation outside approved working spaces.
3. **Isolated Sandbox Runtime**: Plugin extensions execute in restricted sandboxes with granular permission manifests.
4. **Offline Privacy Guarantee**: Enabling `JARVIS_PRIVACY_MODE=true` disables all outbound HTTP requests to external LLM providers.

---

## 🏛️ Security Shield Modules

| Security Module | File Location | Responsibility |
|---|---|---|
| **Security Shield** | `JARVIS/core/security/security_shield.py` | Encrypted credential storage, master encryption key generation |
| **Command Safety** | `JARVIS/core/security/command_safety.py` | Rejects dangerous system commands (`rmdir /s /q`, raw disk formatting, unauthorized registry edits) |
| **Path Safety** | `JARVIS/core/security/path_safety.py` | Prevents directory traversal attacks (`../..`) |
| **Release Security** | `JARVIS/core/security/release_security.py` | Cryptographic signature validation for build releases |

---

## 📋 Vulnerability Reporting

If you discover a security vulnerability in HESA, please **do not open a public GitHub issue**.

### Reporting Process
1. Email details to `security@open-jarvis.org` or submit via GitHub Private Vulnerability Reporting.
2. Include steps to reproduce, affected versions, and potential impact.
3. Our security team will acknowledge receipt within **48 hours** and provide periodic updates until resolved.
