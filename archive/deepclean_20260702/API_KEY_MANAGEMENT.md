# API Key Management & Security Strategy

## 1. Encrypted Storage Model
To prevent leaking sensitive API credentials in plaintext, JARVIS utilizes the `cryptography.fernet` module to implement AES-128 in CBC mode (Fernet) for secure storage.

- **Master Key:** A unique key derived from machine-specific hardware identifiers (e.g. combination of CPU ID, motherboard UUID, and MAC address) combined with salt.
- **Config Store:** API keys are encrypted at rest and stored in `.env` or `logs/config_secure.json` under ciphertext blocks:
  - `OPENAI_API_KEY_ENC`
  - `GEMINI_API_KEY_ENC`
  - `ANTHROPIC_API_KEY_ENC`
  - `GROK_API_KEY_ENC`
  - `DEEPSEEK_API_KEY_ENC`

## 2. Key Rotation
- Credentials can be updated or rotated via secure command calls or the Settings QML panel.
- During rotation, keys are re-encrypted with a freshly generated salt and written back to secure storage.

## 3. API Monitoring & Token Guard
- Tracks token consumption per provider (input and output tokens).
- Calculates costs using standard model pricing sheets.
- Alerts user or blocks calls if cost exceeds daily safety thresholds (e.g. $1.00 daily limit).
