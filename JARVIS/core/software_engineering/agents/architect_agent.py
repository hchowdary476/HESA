"""
JARVIS Architect Agent — SE Layer.

Analyses user requirements and produces a complete ArchitectureSpec that all
downstream SE agents (Frontend, Backend, Mobile, AI/ML) consume.

Responsibilities:
  - Parse natural language requirements
  - Select the best technology stack
  - Design the complete folder structure
  - Generate project scaffold files (architecture_spec.json, folder_structure.txt)
  - Produce technical specifications for downstream agents
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("architect_agent")


# ---------------------------------------------------------------------------
# Technology Stack Catalogue
# ---------------------------------------------------------------------------

TECH_STACKS = {
    "fastapi": {
        "backend": "FastAPI", "language": "Python", "orm": "SQLAlchemy",
        "auth": "JWT (python-jose)", "db_default": "SQLite",
        "deps": ["fastapi", "uvicorn", "sqlalchemy", "python-jose", "passlib", "pydantic"],
    },
    "flask": {
        "backend": "Flask", "language": "Python", "orm": "SQLAlchemy",
        "auth": "Flask-JWT-Extended", "db_default": "SQLite",
        "deps": ["flask", "flask-sqlalchemy", "flask-jwt-extended", "flask-cors"],
    },
    "django": {
        "backend": "Django", "language": "Python", "orm": "Django ORM",
        "auth": "Django Auth", "db_default": "PostgreSQL",
        "deps": ["django", "djangorestframework", "django-cors-headers", "psycopg2-binary"],
    },
    "spring": {
        "backend": "Spring Boot", "language": "Java",
        "orm": "Spring Data JPA", "auth": "Spring Security JWT",
        "db_default": "PostgreSQL",
        "deps": ["spring-boot-starter-web", "spring-data-jpa", "spring-security"],
    },
    "react": {
        "frontend": "React", "language": "JavaScript/TypeScript",
        "ui_lib": "Tailwind CSS", "build_tool": "Vite",
        "deps": ["react", "react-dom", "react-router-dom", "axios", "tailwindcss"],
    },
    "nextjs": {
        "frontend": "Next.js", "language": "TypeScript",
        "ui_lib": "Tailwind CSS", "build_tool": "built-in",
        "deps": ["next", "react", "react-dom", "typescript", "tailwindcss"],
    },
    "vanilla": {
        "frontend": "Vanilla HTML/CSS/JS", "language": "JavaScript",
        "ui_lib": "Custom CSS", "build_tool": "None",
        "deps": [],
    },
    "flutter": {
        "mobile": "Flutter", "language": "Dart",
        "state": "Riverpod", "http": "dio",
        "deps": ["flutter", "riverpod", "dio", "shared_preferences", "go_router"],
    },
    "android": {
        "mobile": "Android Native", "language": "Kotlin",
        "arch": "MVVM", "http": "Retrofit",
        "deps": ["retrofit", "okhttp3", "room", "lifecycle-viewmodel"],
    },
}

# Keyword → stack selection heuristics
_BACKEND_KEYWORDS = {
    "fastapi": "fastapi", "fast api": "fastapi",
    "flask": "flask", "django": "django",
    "spring": "spring", "spring boot": "spring",
    "rest api": "fastapi", "api": "fastapi",
}
_FRONTEND_KEYWORDS = {
    "react": "react", "next": "nextjs", "next.js": "nextjs",
    "nextjs": "nextjs", "html": "vanilla", "vanilla": "vanilla",
}
_MOBILE_KEYWORDS = {
    "flutter": "flutter", "android": "android",
    "mobile": "flutter", "app": "flutter",
}
_DB_KEYWORDS = {
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "sqlite": "SQLite",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "redis": "Redis",
}


# ---------------------------------------------------------------------------
# Architecture Spec Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ArchitectureSpec:
    """Full project specification produced by the Architect Agent."""
    project_name: str
    description: str
    project_type: str                  # fullstack | api | mobile | ml | cli
    backend_stack: str | None          # FastAPI | Flask | Django | Spring Boot | None
    frontend_stack: str | None         # React | Next.js | Vanilla | None
    mobile_stack: str | None           # Flutter | Android | None
    ml_stack: str | None               # PyTorch | scikit-learn | TensorFlow | None
    database: str                      # SQLite | PostgreSQL | MySQL | MongoDB
    auth_method: str                   # JWT | Session | None
    features: list[str] = field(default_factory=list)   # user-specified features
    folder_structure: dict[str, Any] = field(default_factory=dict)
    backend_deps: list[str] = field(default_factory=list)
    frontend_deps: list[str] = field(default_factory=list)
    mobile_deps: list[str] = field(default_factory=list)
    api_endpoints: list[dict] = field(default_factory=list)
    data_models: list[dict] = field(default_factory=list)
    workspace_path: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Architect Agent
# ---------------------------------------------------------------------------

class ArchitectAgent:
    """
    Analyses requirements and produces a complete ArchitectureSpec.

    Called first in every SE pipeline run. All other SE agents
    receive the ArchitectureSpec as their primary input.
    """

    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = workspace_root

    def analyse(self, command: str, context: str = "") -> ArchitectureSpec:
        """
        Parse requirements and produce an ArchitectureSpec.

        Args:
            command: Raw user request
            context: Additional context from CognitiveCore memory

        Returns:
            ArchitectureSpec consumed by all downstream agents
        """
        cmd = command.lower()
        logger.info("ArchitectAgent analysing: '%s'", command[:80])

        # ── Project Name ──────────────────────────────────────────────────────
        project_name = self._extract_project_name(command)
        workspace_path = os.path.join(self.workspace_root, project_name)

        # ── Project Type ─────────────────────────────────────────────────────
        project_type = self._detect_project_type(cmd)

        # ── Stack Selection ───────────────────────────────────────────────────
        backend_stack = self._select_backend(cmd, project_type)
        frontend_stack = self._select_frontend(cmd, project_type)
        mobile_stack = self._select_mobile(cmd, project_type)
        ml_stack = self._select_ml_stack(cmd, project_type)

        # ── Database ─────────────────────────────────────────────────────────
        database = self._select_database(cmd, backend_stack)

        # ── Auth ─────────────────────────────────────────────────────────────
        auth_method = "JWT" if any(w in cmd for w in ["auth", "login", "user", "register", "jwt"]) else "None"

        # ── Features ─────────────────────────────────────────────────────────
        features = self._extract_features(cmd)

        # ── Dependencies ─────────────────────────────────────────────────────
        backend_deps = self._get_backend_deps(backend_stack, auth_method, database)
        frontend_deps = self._get_frontend_deps(frontend_stack)
        mobile_deps = self._get_mobile_deps(mobile_stack)

        # ── API Endpoints ─────────────────────────────────────────────────────
        api_endpoints = self._generate_api_endpoints(features, auth_method)

        # ── Data Models ───────────────────────────────────────────────────────
        data_models = self._generate_data_models(features)

        # ── Folder Structure ─────────────────────────────────────────────────
        folder_structure = self._build_folder_structure(
            project_type, backend_stack, frontend_stack, mobile_stack, ml_stack
        )

        spec = ArchitectureSpec(
            project_name=project_name,
            description=command,
            project_type=project_type,
            backend_stack=backend_stack,
            frontend_stack=frontend_stack,
            mobile_stack=mobile_stack,
            ml_stack=ml_stack,
            database=database,
            auth_method=auth_method,
            features=features,
            folder_structure=folder_structure,
            backend_deps=backend_deps,
            frontend_deps=frontend_deps,
            mobile_deps=mobile_deps,
            api_endpoints=api_endpoints,
            data_models=data_models,
            workspace_path=workspace_path,
        )

        # Persist spec
        self._save_spec(spec)
        logger.info(
            "ArchitectAgent complete: %s | type=%s | backend=%s | frontend=%s",
            project_name, project_type, backend_stack, frontend_stack,
        )
        return spec

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _extract_project_name(self, command: str) -> str:
        """Derive a filesystem-safe project name from the command."""
        # Try to extract 'called X', 'named X', 'for X'
        for pat in [r"called\s+(\w+)", r"named\s+(\w+)", r"for\s+(\w+)\s+app", r"for\s+(\w+)"]:
            m = re.search(pat, command, re.IGNORECASE)
            if m:
                return m.group(1).lower()
        # Extract meaningful nouns (task, manager, todo, shop, etc.)
        noun_patterns = [
            r"\b(task|todo|shop|store|blog|chat|note|book|event|recipe|fitness|"
            r"inventory|ticket|forum|social|portfolio|dashboard|admin|crm|erp)\b"
        ]
        for pat in noun_patterns:
            m = re.search(pat, command, re.IGNORECASE)
            if m:
                return f"{m.group(1).lower()}_app"
        # Fallback
        ts = int(time.time()) % 10000
        return f"jarvis_project_{ts}"

    def _detect_project_type(self, cmd: str) -> str:
        if any(w in cmd for w in ["flutter", "android", "mobile", "ios"]):
            return "mobile"
        if any(w in cmd for w in ["ml model", "machine learning", "train", "neural", "ai pipeline", "dataset"]):
            return "ml"
        if any(w in cmd for w in ["fullstack", "full stack", "full-stack", "web app", "website"]):
            return "fullstack"
        if any(w in cmd for w in ["api", "rest", "endpoint", "backend", "fastapi", "flask", "django"]):
            return "api"
        if any(w in cmd for w in ["frontend", "ui", "react", "html", "next"]):
            return "frontend"
        return "fullstack"

    def _select_backend(self, cmd: str, project_type: str) -> str | None:
        if project_type in ("mobile", "frontend"):
            return None
        for kw, stack in _BACKEND_KEYWORDS.items():
            if kw in cmd:
                return TECH_STACKS[stack]["backend"]
        return "FastAPI"  # default

    def _select_frontend(self, cmd: str, project_type: str) -> str | None:
        if project_type in ("mobile", "api", "ml"):
            return None
        for kw, stack in _FRONTEND_KEYWORDS.items():
            if kw in cmd:
                return TECH_STACKS[stack]["frontend"]
        if project_type in ("fullstack", "frontend"):
            return "React"
        return None

    def _select_mobile(self, cmd: str, project_type: str) -> str | None:
        if project_type != "mobile" and not any(w in cmd for w in ["flutter", "android", "mobile"]):
            return None
        for kw, stack in _MOBILE_KEYWORDS.items():
            if kw in cmd:
                return TECH_STACKS[stack]["mobile"]
        return "Flutter"

    def _select_ml_stack(self, cmd: str, project_type: str) -> str | None:
        if project_type != "ml":
            return None
        if "torch" in cmd or "pytorch" in cmd:
            return "PyTorch"
        if "tensorflow" in cmd or "keras" in cmd:
            return "TensorFlow"
        return "scikit-learn"

    def _select_database(self, cmd: str, backend: str | None) -> str:
        for kw, db in _DB_KEYWORDS.items():
            if kw in cmd:
                return db
        if backend == "Django":
            return "PostgreSQL"
        return "SQLite"

    def _extract_features(self, cmd: str) -> list[str]:
        features: list[str] = []
        feature_map = {
            "auth": ["auth", "login", "register", "signup", "user", "jwt", "authentication"],
            "crud": ["crud", "create", "read", "update", "delete", "manage", "manager"],
            "search": ["search", "filter", "query"],
            "real-time": ["real-time", "realtime", "websocket", "live", "socket"],
            "file-upload": ["upload", "file", "image", "media", "attachment"],
            "email": ["email", "notification", "newsletter", "smtp"],
            "payment": ["payment", "stripe", "checkout", "billing", "subscription"],
            "admin-panel": ["admin", "dashboard", "panel", "management"],
            "api-docs": ["swagger", "openapi", "docs", "documentation"],
            "testing": ["test", "tests", "unit test", "pytest"],
        }
        for feature, keywords in feature_map.items():
            if any(kw in cmd for kw in keywords):
                features.append(feature)
        if not features:
            features = ["crud", "auth"]
        return features

    def _get_backend_deps(self, stack: str | None, auth: str, db: str) -> list[str]:
        if not stack:
            return []
        stack_key = stack.lower().replace(" ", "_").replace(".", "")
        base = {
            "fastapi": ["fastapi", "uvicorn[standard]", "sqlalchemy", "alembic", "pydantic[email]",
                        "python-multipart", "python-dotenv", "httpx"],
            "flask": ["flask", "flask-sqlalchemy", "flask-migrate", "flask-cors", "python-dotenv"],
            "django": ["django", "djangorestframework", "django-cors-headers", "python-dotenv"],
            "spring_boot": [],
        }.get(stack_key, [])
        if auth == "JWT":
            if "fastapi" in stack_key:
                base += ["python-jose[cryptography]", "passlib[bcrypt]"]
            elif "flask" in stack_key:
                base += ["flask-jwt-extended"]
        if db == "PostgreSQL":
            base += ["psycopg2-binary"]
        elif db == "MongoDB":
            base += ["motor", "beanie"]
        return base

    def _get_frontend_deps(self, stack: str | None) -> list[str]:
        if not stack:
            return []
        return {
            "React": ["react", "react-dom", "react-router-dom", "axios", "tailwindcss", "@vitejs/plugin-react"],
            "Next.js": ["next", "react", "react-dom", "typescript", "tailwindcss", "axios"],
            "Vanilla HTML/CSS/JS": [],
        }.get(stack, [])

    def _get_mobile_deps(self, stack: str | None) -> list[str]:
        if not stack:
            return []
        return {
            "Flutter": ["riverpod", "dio", "shared_preferences", "go_router", "flutter_secure_storage"],
            "Android Native": ["retrofit", "okhttp3", "room", "lifecycle-viewmodel", "coroutines"],
        }.get(stack, [])

    def _generate_api_endpoints(self, features: list[str], auth: str) -> list[dict]:
        endpoints: list[dict] = []
        if auth == "JWT":
            endpoints += [
                {"method": "POST", "path": "/api/auth/register", "description": "Register new user", "auth": False},
                {"method": "POST", "path": "/api/auth/login", "description": "Login and get JWT token", "auth": False},
                {"method": "POST", "path": "/api/auth/logout", "description": "Logout and invalidate token", "auth": True},
                {"method": "GET", "path": "/api/auth/me", "description": "Get current user profile", "auth": True},
            ]
        if "crud" in features:
            endpoints += [
                {"method": "GET", "path": "/api/items", "description": "List all items", "auth": True},
                {"method": "POST", "path": "/api/items", "description": "Create new item", "auth": True},
                {"method": "GET", "path": "/api/items/{id}", "description": "Get item by ID", "auth": True},
                {"method": "PUT", "path": "/api/items/{id}", "description": "Update item", "auth": True},
                {"method": "DELETE", "path": "/api/items/{id}", "description": "Delete item", "auth": True},
            ]
        if "search" in features:
            endpoints.append({"method": "GET", "path": "/api/items/search", "description": "Search items", "auth": True})
        if not endpoints:
            endpoints.append({"method": "GET", "path": "/api/health", "description": "Health check", "auth": False})
        return endpoints

    def _generate_data_models(self, features: list[str]) -> list[dict]:
        models: list[dict] = []
        if "auth" in features:
            models.append({
                "name": "User",
                "fields": [
                    {"name": "id", "type": "Integer", "primary_key": True},
                    {"name": "username", "type": "String(50)", "unique": True, "nullable": False},
                    {"name": "email", "type": "String(120)", "unique": True, "nullable": False},
                    {"name": "hashed_password", "type": "String(255)", "nullable": False},
                    {"name": "is_active", "type": "Boolean", "default": True},
                    {"name": "created_at", "type": "DateTime", "default": "now()"},
                ],
            })
        if "crud" in features:
            models.append({
                "name": "Item",
                "fields": [
                    {"name": "id", "type": "Integer", "primary_key": True},
                    {"name": "title", "type": "String(200)", "nullable": False},
                    {"name": "description", "type": "Text", "nullable": True},
                    {"name": "is_completed", "type": "Boolean", "default": False},
                    {"name": "owner_id", "type": "Integer", "foreign_key": "user.id"},
                    {"name": "created_at", "type": "DateTime", "default": "now()"},
                    {"name": "updated_at", "type": "DateTime", "onupdate": "now()"},
                ],
            })
        return models

    def _build_folder_structure(
        self,
        project_type: str,
        backend: str | None,
        frontend: str | None,
        mobile: str | None,
        ml: str | None,
    ) -> dict[str, Any]:
        structure: dict[str, Any] = {}
        if backend:
            structure["backend"] = {
                "app": {"models": {}, "routes": {}, "schemas": {}, "services": {}, "core": {}},
                "tests": {},
                "requirements.txt": None,
                ".env.example": None,
                "main.py": None,
            }
        if frontend:
            structure["frontend"] = {
                "src": {"components": {}, "pages": {}, "hooks": {}, "services": {}, "styles": {}},
                "public": {},
                "package.json": None,
                "README.md": None,
            }
        if mobile:
            structure["mobile"] = {
                "lib": {"screens": {}, "widgets": {}, "providers": {}, "services": {}, "models": {}},
                "test": {},
                "pubspec.yaml": None,
            }
        if ml:
            structure["ml"] = {
                "data": {"raw": {}, "processed": {}},
                "models": {},
                "notebooks": {},
                "src": {"training": {}, "inference": {}, "evaluation": {}},
                "requirements.txt": None,
            }
        structure["docs"] = {}
        structure["devops"] = {}
        structure["tests"] = {}
        return structure

    def _save_spec(self, spec: ArchitectureSpec) -> None:
        """Persist architecture spec to workspace."""
        try:
            os.makedirs(spec.workspace_path, exist_ok=True)
            spec_path = os.path.join(spec.workspace_path, "architecture_spec.json")
            with open(spec_path, "w", encoding="utf-8") as fh:
                fh.write(spec.to_json())
            # Also write folder structure summary
            struct_path = os.path.join(spec.workspace_path, "folder_structure.txt")
            with open(struct_path, "w", encoding="utf-8") as fh:
                fh.write(self._render_structure(spec.folder_structure, spec.project_name))
            logger.info("Architecture spec saved to %s", spec.workspace_path)
        except Exception as e:
            logger.error("Failed to save architecture spec: %s", e)

    def _render_structure(self, structure: dict, name: str, indent: int = 0) -> str:
        lines = [f"{'  ' * indent}{name}/"] if indent == 0 else []
        for key, val in structure.items():
            prefix = "  " * (indent + 1)
            if val is None:
                lines.append(f"{prefix}{key}")
            else:
                lines.append(f"{prefix}{key}/")
                lines.append(self._render_structure(val, key, indent + 2))
        return "\n".join(lines)
