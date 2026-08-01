# Contributing to HESA (JARVIS)

Thank you for your interest in contributing to the HESA (JARVIS) AI Assistant!

## Code of Conduct
This project and everyone participating in it is governed by the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs
Before creating bug reports, please check existing issues. When creating a bug report, include:
- A clear summary and steps to reproduce.
- Your OS version and Python environment details.
- Log outputs from `logs/startup.log` or `logs/gui_traceback.log`.

### Suggesting Enhancements
Feature requests are tracked as GitHub Issues. Provide a clear description of the feature, use cases, and proposed design.

### Pull Requests
1. Fork the repository and create a feature branch (`git checkout -b feature/amazing-feature`).
2. Run code verification scripts:
   ```cmd
   python scripts/run_production_feature_audit.py
   python scripts/public_release_check.py
   ```
3. Ensure code adheres to PEP 8 standards.
4. Commit your changes (`git commit -m 'Add amazing feature'`).
5. Push to the branch (`git push origin feature/amazing-feature`).
6. Open a Pull Request against `main`.
