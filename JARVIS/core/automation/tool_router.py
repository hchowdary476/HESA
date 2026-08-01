"""
JARVIS Tool Router — Layer 4: Natural Language → Tool SDK Auto-Routing.

Maps all Tool SDK categories and individual tools to the correct:
  - AgentManager agent key
  - runtime_actions function
  - Tool category

Users never need to name specific tools. The CognitiveCore intent pipeline
and AutonomousExecutor consult this router to automatically select the right
tool for any natural-language command.

Supported Tool SDK categories:
  • Windows Tools    → windows_system_agent
  • Developer Tools  → developer_agent / coding_agent
  • AI Tools         → ai_and_ml_agent
  • ML Tools         → ai_and_ml_agent
  • Cyber Tools      → cyber_security_agent
  • Browser Tools    → research_agent / automation_agent
  • File Tools       → windows_system_agent / developer_agent
  • Office Tools     → automation_agent
  • Network Tools    → cyber_security_agent / research_agent
  • Plugin Tools     → automation_agent
"""

from __future__ import annotations

import re
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("tool_router")


# ---------------------------------------------------------------------------
# Tool → Agent + Action mapping table
# ---------------------------------------------------------------------------

# Each entry: keyword_patterns → { agent, tool_category, action_hint, priority }
# Priority: lower = matched first

_ROUTING_TABLE: list[dict[str, Any]] = [

    # ── Windows System Tools ─────────────────────────────────────────────────
    {
        "patterns": [r"\bopen\s+(?:vs\s?code|visual\s+studio\s?code|vscode)\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "open_app",
        "tool": "open_vscode",
        "priority": 1,
    },
    {
        "patterns": [r"\bopen\s+chrome\b", r"\blaunch\s+chrome\b", r"\bopen\s+browser\b"],
        "agent": "automation_agent",
        "tool_category": "browser_tools",
        "action_hint": "open_app",
        "tool": "open_chrome",
        "priority": 1,
    },
    {
        "patterns": [r"\block\s+(?:the\s+)?(?:computer|pc|screen)\b", r"\block\s+windows\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "lock_computer",
        "tool": "lock_computer",
        "priority": 1,
    },
    {
        "patterns": [r"\brestart\s+(?:the\s+)?(?:pc|computer|system|windows)\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "restart_computer",
        "tool": "restart_computer",
        "priority": 1,
    },
    {
        "patterns": [r"\bshutdown\b", r"\bshut\s+down\b", r"\bturn\s+off\s+(?:the\s+)?(?:pc|computer)\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "shutdown_computer",
        "tool": "shutdown_computer",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:increase|turn\s+up|raise|boost)\s+volume\b", r"\bvolume\s+up\b"],
        "agent": "automation_agent",
        "tool_category": "windows_tools",
        "action_hint": "press_key",
        "tool": "volume_up",
        "priority": 2,
    },
    {
        "patterns": [r"\b(?:decrease|turn\s+down|lower|reduce)\s+volume\b", r"\bvolume\s+down\b"],
        "agent": "automation_agent",
        "tool_category": "windows_tools",
        "action_hint": "press_key",
        "tool": "volume_down",
        "priority": 2,
    },
    {
        "patterns": [r"\bmute\b", r"\bsilence\b"],
        "agent": "automation_agent",
        "tool_category": "windows_tools",
        "action_hint": "press_key",
        "tool": "mute_volume",
        "priority": 2,
    },
    {
        "patterns": [r"\bopen\s+downloads\b", r"\bopen\s+(?:my\s+)?files?\b", r"\bfile\s+explorer\b"],
        "agent": "windows_system_agent",
        "tool_category": "file_tools",
        "action_hint": "open_app",
        "tool": "open_explorer",
        "priority": 2,
    },
    {
        "patterns": [r"\bclean\s+temp\b", r"\bclean\s+temporary\s+files\b", r"\bclear\s+cache\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "clean_temp_files",
        "tool": "clean_temp",
        "priority": 2,
    },
    {
        "patterns": [r"\bscreenshot\b", r"\bscreen\s+shot\b", r"\bcapture\s+screen\b"],
        "agent": "automation_agent",
        "tool_category": "windows_tools",
        "action_hint": "screenshot",
        "tool": "screenshot",
        "priority": 2,
    },
    {
        "patterns": [r"\bconnect\s+bluetooth\b", r"\bbluetooth\s+settings\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "open_bluetooth",
        "tool": "bluetooth_settings",
        "priority": 2,
    },
    {
        "patterns": [r"\bcpu\b", r"\bprocessor\s+usage\b", r"\bcpu\s+usage\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "get_cpu",
        "tool": "get_cpu",
        "priority": 3,
    },
    {
        "patterns": [r"\bram\b", r"\bmemory\s+usage\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "get_ram",
        "tool": "get_ram",
        "priority": 3,
    },
    {
        "patterns": [r"\bbattery\b", r"\bcharge\s+level\b"],
        "agent": "windows_system_agent",
        "tool_category": "windows_tools",
        "action_hint": "get_battery",
        "tool": "get_battery",
        "priority": 3,
    },

    # ── Developer Tools ───────────────────────────────────────────────────────
    {
        "patterns": [r"\brun\s+tests?\b", r"\bpytest\b", r"\bunit\s+test\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "run_tests",
        "tool": "pytest_runner",
        "priority": 1,
    },
    {
        "patterns": [r"\bbuild\s+(?:the\s+)?(?:project|app|application)\b", r"\bcompile\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "build_project",
        "tool": "build_runner",
        "priority": 1,
    },
    {
        "patterns": [r"\bgit\s+commit\b", r"\bcommit\s+changes\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "git_commit",
        "tool": "git_commit",
        "priority": 1,
    },
    {
        "patterns": [r"\bgit\s+push\b", r"\bpush\s+(?:to\s+)?(?:github|remote|origin)\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "git_push",
        "tool": "git_push",
        "priority": 1,
    },
    {
        "patterns": [r"\bdeploy\b", r"\bship\s+(?:the\s+)?(?:app|application|code)\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "deploy_app",
        "tool": "deploy_runner",
        "priority": 1,
    },
    {
        "patterns": [r"\bvirtual\s+env\b", r"\bvenv\b", r"\bcreate\s+environment\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "create_venv",
        "tool": "venv_creator",
        "priority": 1,
    },
    {
        "patterns": [r"\binstall\s+dependencies\b", r"\bpip\s+install\b", r"\binstall\s+requirements\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "install_deps",
        "tool": "pip_installer",
        "priority": 1,
    },
    {
        "patterns": [r"\brefactor\b", r"\bclean\s+(?:up\s+)?(?:the\s+)?code\b"],
        "agent": "coding_agent",
        "tool_category": "developer_tools",
        "action_hint": "refactor_code",
        "tool": "code_refactor",
        "priority": 2,
    },
    {
        "patterns": [r"\bopen\s+terminal\b", r"\blaunch\s+terminal\b", r"\bopen\s+cmd\b"],
        "agent": "windows_system_agent",
        "tool_category": "developer_tools",
        "action_hint": "open_app",
        "tool": "open_terminal",
        "priority": 2,
    },
    {
        "patterns": [r"\bstart\s+(?:local\s+)?server\b", r"\brun\s+(?:the\s+)?server\b"],
        "agent": "developer_agent",
        "tool_category": "developer_tools",
        "action_hint": "start_server",
        "tool": "server_launcher",
        "priority": 1,
    },

    # ── AI Tools ─────────────────────────────────────────────────────────────
    {
        "patterns": [r"\bstart\s+ollama\b", r"\blaunch\s+ollama\b", r"\bollama\b"],
        "agent": "ai_and_ml_agent",
        "tool_category": "ai_tools",
        "action_hint": "start_ollama",
        "tool": "ollama_launcher",
        "priority": 1,
    },
    {
        "patterns": [r"\bswitch\s+model\b", r"\buse\s+model\b", r"\bchange\s+(?:ai\s+)?model\b"],
        "agent": "ai_and_ml_agent",
        "tool_category": "ai_tools",
        "action_hint": "switch_model",
        "tool": "model_switcher",
        "priority": 1,
    },
    {
        "patterns": [r"\bdebate\s+mode\b", r"\brun\s+debate\b", r"\bmulti[- ]ai\b"],
        "agent": "ai_and_ml_agent",
        "tool_category": "ai_tools",
        "action_hint": "debate_mode",
        "tool": "debate_runner",
        "priority": 1,
    },

    # ── ML Tools ─────────────────────────────────────────────────────────────
    {
        "patterns": [r"\btrain\s+(?:a\s+)?model\b", r"\bfine[- ]tune\b"],
        "agent": "ai_and_ml_agent",
        "tool_category": "ml_tools",
        "action_hint": "train_model",
        "tool": "ml_trainer",
        "priority": 1,
    },
    {
        "patterns": [r"\brun\s+benchmark\b", r"\bbenchmark\s+(?:the\s+)?model\b"],
        "agent": "ai_and_ml_agent",
        "tool_category": "ml_tools",
        "action_hint": "run_benchmark",
        "tool": "ml_benchmark",
        "priority": 2,
    },

    # ── Cyber / Security Tools ────────────────────────────────────────────────
    {
        "patterns": [r"\bsecurity\s+audit\b", r"\baudit\s+(?:the\s+)?(?:system|logs)\b"],
        "agent": "cyber_security_agent",
        "tool_category": "cyber_tools",
        "action_hint": "security_audit",
        "tool": "security_auditor",
        "priority": 1,
    },
    {
        "patterns": [r"\bport\s+scan\b", r"\bscan\s+ports\b", r"\bopen\s+ports\b"],
        "agent": "cyber_security_agent",
        "tool_category": "cyber_tools",
        "action_hint": "port_scan",
        "tool": "port_scanner",
        "priority": 1,
    },
    {
        "patterns": [r"\bcve\b", r"\bvulnerabilit(?:y|ies)\b"],
        "agent": "cyber_security_agent",
        "tool_category": "cyber_tools",
        "action_hint": "cve_lookup",
        "tool": "cve_lookup",
        "priority": 1,
    },
    {
        "patterns": [r"\bcheck\s+firewall\b", r"\bfirewall\s+status\b"],
        "agent": "cyber_security_agent",
        "tool_category": "cyber_tools",
        "action_hint": "check_firewall",
        "tool": "firewall_checker",
        "priority": 2,
    },

    # ── Browser Tools ─────────────────────────────────────────────────────────
    {
        "patterns": [r"\bsearch\s+(?:for\s+|the\s+web\s+for\s+)?(.+)", r"\bgoogle\s+(.+)"],
        "agent": "research_agent",
        "tool_category": "browser_tools",
        "action_hint": "web_search",
        "tool": "web_searcher",
        "priority": 2,
    },
    {
        "patterns": [r"\bopen\s+(?:youtube|github|gmail|openai)\b"],
        "agent": "automation_agent",
        "tool_category": "browser_tools",
        "action_hint": "open_website",
        "tool": "website_opener",
        "priority": 2,
    },

    # ── File Tools ────────────────────────────────────────────────────────────
    {
        "patterns": [r"\bbackup\s+(?:my\s+)?project\b", r"\bcreate\s+backup\b"],
        "agent": "windows_system_agent",
        "tool_category": "file_tools",
        "action_hint": "backup_files",
        "tool": "file_backup",
        "priority": 1,
    },
    {
        "patterns": [r"\bsearch\s+(?:for\s+)?(?:project\s+)?files?\b", r"\bfind\s+files?\b"],
        "agent": "windows_system_agent",
        "tool_category": "file_tools",
        "action_hint": "search_files",
        "tool": "file_searcher",
        "priority": 2,
    },

    # ── Office Tools ──────────────────────────────────────────────────────────
    {
        "patterns": [r"\bopen\s+word\b", r"\blaunch\s+word\b", r"\bmicrosoft\s+word\b"],
        "agent": "automation_agent",
        "tool_category": "office_tools",
        "action_hint": "open_app",
        "tool": "open_word",
        "priority": 2,
    },
    {
        "patterns": [r"\bopen\s+excel\b", r"\blaunch\s+excel\b"],
        "agent": "automation_agent",
        "tool_category": "office_tools",
        "action_hint": "open_app",
        "tool": "open_excel",
        "priority": 2,
    },
    {
        "patterns": [r"\bopen\s+powerpoint\b", r"\blaunch\s+(?:a\s+)?presentation\b"],
        "agent": "automation_agent",
        "tool_category": "office_tools",
        "action_hint": "open_app",
        "tool": "open_powerpoint",
        "priority": 2,
    },
    {
        "patterns": [r"\bgenerate\s+report\b", r"\bcreate\s+report\b", r"\bwrite\s+report\b"],
        "agent": "coding_agent",
        "tool_category": "office_tools",
        "action_hint": "generate_report",
        "tool": "report_generator",
        "priority": 2,
    },

    # ── Network Tools ─────────────────────────────────────────────────────────
    {
        "patterns": [r"\bnetwork\s+(?:status|speed|diagnostics)\b", r"\bcheck\s+(?:my\s+)?internet\b"],
        "agent": "cyber_security_agent",
        "tool_category": "network_tools",
        "action_hint": "network_status",
        "tool": "network_monitor",
        "priority": 2,
    },
    {
        "patterns": [r"\bping\s+(.+)", r"\btest\s+connection\b"],
        "agent": "cyber_security_agent",
        "tool_category": "network_tools",
        "action_hint": "ping",
        "tool": "ping_tool",
        "priority": 2,
    },
    {
        "patterns": [r"\bwifi\s+(?:status|info|networks?)\b"],
        "agent": "cyber_security_agent",
        "tool_category": "network_tools",
        "action_hint": "wifi_status",
        "tool": "wifi_checker",
        "priority": 2,
    },

    # ── Research / AI Research Mode ───────────────────────────────────────────
    {
        "patterns": [r"\bresearch\s+(.+)", r"\binvestigate\s+(.+)", r"\bsummarise\s+(.+)", r"\bsummarize\s+(.+)"],
        "agent": "research_agent",
        "tool_category": "ai_tools",
        "action_hint": "research",
        "tool": "research_engine",
        "priority": 3,
    },
    {
        "patterns": [r"\blatest\s+(?:ai|ml|models?|papers?|research)\b"],
        "agent": "research_agent",
        "tool_category": "ai_tools",
        "action_hint": "research",
        "tool": "research_engine",
        "priority": 3,
    },

    # ── Memory / Knowledge ────────────────────────────────────────────────────
    {
        "patterns": [r"\bremember\b", r"\bsave\s+(?:a\s+)?note\b", r"\bnote\s+(?:that\s+|down\s+)?(.+)"],
        "agent": "memory_agent",
        "tool_category": "memory_tools",
        "action_hint": "save_note",
        "tool": "note_saver",
        "priority": 2,
    },
    {
        "patterns": [r"\bwhat\s+(?:are\s+)?my\s+notes\b", r"\bread\s+(?:my\s+)?notes\b"],
        "agent": "memory_agent",
        "tool_category": "memory_tools",
        "action_hint": "read_notes",
        "tool": "note_reader",
        "priority": 2,
    },

    # ── Diagnostics ───────────────────────────────────────────────────────────
    {
        "patterns": [r"\brun\s+diagnostics\b", r"\bhealth\s+check\b", r"\bsystem\s+health\b"],
        "agent": "windows_system_agent",
        "tool_category": "diagnostics",
        "action_hint": "run_system_diagnostics",
        "tool": "diagnostics_runner",
        "priority": 1,
    },

    # ── Software Engineering Agents ───────────────────────────────────────────
    {
        "patterns": [r"\bbuild\s+(?:a\s+)?(?:web\s+app|website|full-stack\s+app)\b", r"\barchitect\s+app\b"],
        "agent": "architect_agent",
        "tool_category": "developer_tools",
        "action_hint": "architect_app",
        "tool": "architect_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:build|generate)\s+ui\b", r"\b(?:generate|create)\s+(?:html|css|javascript|js|react|next\.?js)\b", r"\bfrontend\s+layout\b"],
        "agent": "frontend_agent",
        "tool_category": "developer_tools",
        "action_hint": "generate_frontend",
        "tool": "frontend_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:build|generate|create)\s+(?:rest\s+)?api\b", r"\bgenerate\s+(?:fastapi|flask|django|spring\s+boot)\b", r"\bgenerate\s+(?:database\s+models|authentication|auth)\b"],
        "agent": "backend_agent",
        "tool_category": "developer_tools",
        "action_hint": "generate_backend",
        "tool": "backend_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:build|generate|create)\s+(?:flutter|android)\s+app\b", r"\b(?:run\s+)?flutter\s+(?:pub\s+get|build\s+apk)\b", r"\banalyze\s+gradle\s+errors\b", r"\bprepare\s+(?:signing\s+config|release\s+apk)\b"],
        "agent": "mobile_agent",
        "tool_category": "developer_tools",
        "action_hint": "generate_mobile",
        "tool": "mobile_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:build|generate)\s+(?:ai\s+pipeline|ml\s+model)\b", r"\b(?:train|evaluate)\s+model\b", r"\bgenerate\s+inference\s+api\b"],
        "agent": "ai_and_ml_agent",
        "tool_category": "developer_tools",
        "action_hint": "generate_ml",
        "tool": "ai_and_ml_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:generate|write)\s+(?:unit|integration)\s+tests\b", r"\b(?:run|execute)\s+test\s+suite\b", r"\bgenerate\s+coverage\s+report\b"],
        "agent": "testing_agent",
        "tool_category": "developer_tools",
        "action_hint": "generate_tests",
        "tool": "testing_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:read|analyze|fix)\s+(?:compiler|runtime)?\s*(?:error|exception|stack\s+trace)\b", r"\bsuggest\s+fix\b"],
        "agent": "debugger_agent",
        "tool_category": "developer_tools",
        "action_hint": "debug_errors",
        "tool": "debugger_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\b(?:generate|write)\s+(?:readme|api\s+docs|architecture\s+diagram|deployment\s+guide|changelog)\b"],
        "agent": "documentation_agent",
        "tool_category": "developer_tools",
        "action_hint": "generate_docs",
        "tool": "documentation_agent",
        "priority": 1,
    },
    {
        "patterns": [r"\bconfigure\s+(?:docker|ci/cd|github\s+actions)\b", r"\bcreate\s+dockerfile\b"],
        "agent": "devops_agent",
        "tool_category": "developer_tools",
        "action_hint": "configure_devops",
        "tool": "devops_agent",
        "priority": 1,
    },
]

# Pre-compile patterns for performance
_COMPILED_TABLE: list[dict[str, Any]] = []
for _entry in sorted(_ROUTING_TABLE, key=lambda x: x["priority"]):
    _COMPILED_TABLE.append({
        **_entry,
        "_compiled": [re.compile(p, re.IGNORECASE) for p in _entry["patterns"]],
    })


# ---------------------------------------------------------------------------
# ToolRouter Class
# ---------------------------------------------------------------------------

class ToolRouter:
    """
    Maps any natural-language command to the correct agent + tool.

    The CognitiveCore and AutonomousExecutor call resolve() to get routing
    hints before dispatching commands. Results enrich intent metadata without
    replacing the existing local_intent_router or groq_router.
    """

    _instance: ToolRouter | None = None
    _lock = __import__("threading").Lock()

    def __new__(cls) -> "ToolRouter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._routing_table = _COMPILED_TABLE
        logger.info(
            "ToolRouter initialised with %d routing rules across 10 tool categories.",
            len(self._routing_table),
        )

    def resolve(self, command: str) -> dict[str, Any]:
        """
        Match a command against the routing table.

        Returns:
            {
                "agent": str,
                "tool": str,
                "tool_category": str,
                "action_hint": str,
                "matched": bool,
                "confidence": float,
            }
        """
        cmd = command.strip()
        for entry in self._routing_table:
            for pattern in entry["_compiled"]:
                if pattern.search(cmd):
                    result = {
                        "agent": entry["agent"],
                        "tool": entry["tool"],
                        "tool_category": entry["tool_category"],
                        "action_hint": entry["action_hint"],
                        "matched": True,
                        "confidence": 1.0 - (entry["priority"] - 1) * 0.1,
                    }
                    logger.debug(
                        "ToolRouter matched: cmd='%s' → agent='%s' tool='%s'",
                        cmd[:60], result["agent"], result["tool"],
                    )
                    return result

        # No match — return empty resolution (CognitiveCore handles fallback)
        logger.debug("ToolRouter: no specific tool match for '%s'", cmd[:60])
        return {
            "agent": None,
            "tool": None,
            "tool_category": "general",
            "action_hint": "talk",
            "matched": False,
            "confidence": 0.0,
        }

    def get_agent_for_category(self, category: str) -> str:
        """Return the default agent key for a given tool category."""
        category_agent_map = {
            "windows_tools": "windows_system_agent",
            "developer_tools": "developer_agent",
            "ai_tools": "ai_and_ml_agent",
            "ml_tools": "ai_and_ml_agent",
            "cyber_tools": "cyber_security_agent",
            "browser_tools": "research_agent",
            "file_tools": "windows_system_agent",
            "office_tools": "automation_agent",
            "network_tools": "cyber_security_agent",
            "memory_tools": "memory_agent",
            "diagnostics": "windows_system_agent",
        }
        return category_agent_map.get(category, "coding_agent")

    def list_categories(self) -> list[str]:
        """Return all registered tool categories."""
        seen: set[str] = set()
        cats: list[str] = []
        for entry in self._routing_table:
            c = entry["tool_category"]
            if c not in seen:
                seen.add(c)
                cats.append(c)
        return cats

    def get_tools_in_category(self, category: str) -> list[str]:
        """Return all tool names within a given category."""
        return [e["tool"] for e in self._routing_table if e["tool_category"] == category]

    def get_routing_summary(self) -> dict[str, Any]:
        """Return a summary of the routing table for diagnostics."""
        categories: dict[str, list[str]] = {}
        for entry in self._routing_table:
            cat = entry["tool_category"]
            categories.setdefault(cat, []).append(entry["tool"])
        return {
            "total_rules": len(self._routing_table),
            "categories": categories,
        }
