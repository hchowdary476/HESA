# 🔌 HESA Plugin System & Extension Guide

HESA includes a modular plugin architecture allowing developers to extend system capabilities with custom tools and automation hooks.

---

## 📦 Plugin Architecture

A HESA plugin is a directory inside `plugins/` (or `sample_plugins/`) containing a manifest and Python implementation.

### Required Directory Structure
```
plugins/
└── my_custom_plugin/
    ├── manifest.json
    ├── plugin.py
    └── README.md
```

---

## 📄 Manifest Specification (`manifest.json`)

```json
{
  "id": "com.example.myplugin",
  "name": "My Custom Plugin",
  "version": "1.0.0",
  "description": "Adds custom workspace utility commands to HESA.",
  "author": "Your Name",
  "entrypoint": "plugin.py",
  "permissions": [
    "system.notification",
    "storage.read"
  ]
}
```

---

## 🐍 Writing a Plugin (`plugin.py`)

```python
from JARVIS.plugins.plugin_api import BasePlugin, register_plugin

class CustomWorkspacePlugin(BasePlugin):
    def on_load(self):
        self.logger.info("CustomWorkspacePlugin loaded successfully.")

    def execute_action(self, action_name: str, params: dict):
        if action_name == "hello":
            return {"status": "success", "message": f"Hello, {params.get('name', 'User')}!"}
        return {"status": "error", "message": "Unknown action"}

    def on_unload(self):
        self.logger.info("CustomWorkspacePlugin unloaded.")

register_plugin(CustomWorkspacePlugin)
```

---

## 🛡️ Sandbox & Security Rules

- Plugins run in an isolated execution sandbox (`plugin_sandbox.py`).
- Plugins must explicitly request permissions in `manifest.json`.
- Arbitrary code execution targeting system directories or raw socket connections without permission will be blocked by the Security Shield.
