# CONTINUOUS LEARNING REPORT

Specification of the personal user preference learning and workflow optimization engine.

---

## 1. Learning Targets
- **Preferred AI models**: Tracks response latency and user feedback to prioritize local or cloud models.
- **Preferred frameworks**: Learns favorite UI styles (e.g., React vs. Flutter).
- **Coding Style**: Customizes tab spacings, lint parameters, and naming rules.
- **Favorite IDE / Tools**: Prioritizes launch commands for preferred editors (VS Code, Android Studio).
- **Workflows & Fixes**: Logs successful self-healing repairs and standard compilation fixes to avoid repetitive failures.

## 2. Preference Protection Rules
- Automatic learning loops *never* overwrite user-explicit preferences saved in `memory_preferences.json`.
- Learning recommendations occur asynchronously in the background.
