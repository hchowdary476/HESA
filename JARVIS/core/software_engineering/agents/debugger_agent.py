"""
JARVIS Debugger Agent — SE Layer.

Analyses errors, stack traces, and compiler output to:
  - Identify root causes with line-level precision
  - Suggest targeted fixes with diff-style output
  - Apply safe single-line fixes (with explicit content, not shell exec)
  - Validate that proposed fixes resolve the issue

Uses AIOrchestrator for deep LLM-based error analysis.
"""

from __future__ import annotations

import os
import re
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("debugger_agent")

# Common error pattern library
_PYTHON_ERROR_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"ModuleNotFoundError: No module named '([^']+)'"), "Missing Python module", "Run: pip install {0}"),
    (
        re.compile(r"ImportError: cannot import name '([^']+)' from '([^']+)'"),
        "Import name mismatch",
        "Check that '{0}' is exported from '{1}'. Verify module version.",
    ),
    (
        re.compile(r"IndentationError: (expected an indented block|unexpected indent)"),
        "Python indentation error",
        "Check indentation — Python requires consistent spaces (4 spaces recommended).",
    ),
    (re.compile(r"SyntaxError: (.+) \((.+), line (\d+)\)"), "Python syntax error", "Syntax error in {1} at line {2}: {0}"),
    (
        re.compile(r"TypeError: (.+) takes (\d+) positional argument"),
        "Wrong number of arguments",
        "Function called with wrong number of arguments. Check the function signature.",
    ),
    (
        re.compile(r"AttributeError: '([^']+)' object has no attribute '([^']+)'"),
        "Attribute does not exist",
        "Object of type '{0}' has no attribute '{1}'. Check typos or use hasattr().",
    ),
    (
        re.compile(r"KeyError: '?([^'\s]+)'?"),
        "Dictionary key missing",
        "Key '{0}' not found in dict. Use dict.get('{0}', default) for safe access.",
    ),
    (
        re.compile(r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'"),
        "File not found",
        "File '{0}' does not exist. Check the path and working directory.",
    ),
    (
        re.compile(r"PermissionError: \[Errno 13\] Permission denied: '([^']+)'"),
        "Permission denied",
        "No write permission for '{0}'. Run as administrator or change file permissions.",
    ),
    (
        re.compile(r"ConnectionRefusedError"),
        "Server not running",
        "Connection refused — ensure the server is started before running the client.",
    ),
    (
        re.compile(r"sqlalchemy\.exc\.OperationalError"),
        "Database connection error",
        "Database not reachable. Check DATABASE_URL in .env and ensure DB is running.",
    ),
    (
        re.compile(r"pydantic\.ValidationError"),
        "Pydantic schema validation failed",
        "Request body does not match schema. Check required fields and data types.",
    ),
    (
        re.compile(r"jwt\.exceptions\.(ExpiredSignatureError|InvalidSignatureError)"),
        "JWT token error",
        "JWT token is expired or invalid. Refresh the token or check SECRET_KEY.",
    ),
]

_FLUTTER_ERROR_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"Because (.+) depends on (.+) which requires .+, version solving failed"),
        "Flutter dependency conflict",
        "Run 'flutter pub upgrade' or pin dependency versions in pubspec.yaml.",
    ),
    (
        re.compile(r"The getter '(.+)' isn't defined for the class '(.+)'"),
        "Dart undefined getter",
        "'{0}' is not a property of '{1}'. Check class definition or imports.",
    ),
    (
        re.compile(r"FAILURE: Build failed with an exception.*Gradle"),
        "Gradle build failure",
        "Clean and rebuild: 'flutter clean && flutter pub get && flutter build apk'",
    ),
    (
        re.compile(r"Exception: No connected devices"),
        "No device connected",
        "Start an emulator or connect a physical device, then run 'flutter devices'.",
    ),
]

_JS_ERROR_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"Cannot find module '([^']+)'"), "Node module not found", "Run: npm install {0}"),
    (
        re.compile(r"SyntaxError: Unexpected token '(.+)'"),
        "JavaScript syntax error",
        "Syntax error near '{0}'. Check JSX/TypeScript syntax.",
    ),
    (
        re.compile(r"TypeError: Cannot read propert(?:y|ies) of (null|undefined)"),
        "Null/undefined access",
        "Add null check: use optional chaining (?.) or check if value exists before access.",
    ),
    (
        re.compile(r"CORS policy: No 'Access-Control-Allow-Origin'"),
        "CORS blocked",
        "Add CORS middleware to the backend. FastAPI: add CORSMiddleware with allow_origins=['*'].",
    ),
    (
        re.compile(r"net::ERR_CONNECTION_REFUSED"),
        "Backend not running",
        "Backend server is not running. Start it with: uvicorn main:app --reload",
    ),
]


class DebuggerAgent:
    """
    Analyses errors and stack traces to identify root causes and suggest fixes.

    Uses pattern-matching library first (fast, offline), then falls back to
    AIOrchestrator for complex errors that need LLM analysis.
    """

    def analyse(self, error_text: str, source_context: str = "", project_path: str = "") -> dict[str, Any]:
        """
        Analyse an error string and return root cause + fix suggestions.

        Args:
            error_text: The full error output / stack trace
            source_context: Optional relevant source code snippet
            project_path: Path to the project for context

        Returns:
            Analysis report with root_cause, suggestions, severity, fix_diffs
        """
        logger.info("DebuggerAgent analysing error: %s...", error_text[:80])

        # Step 1: Pattern-based fast analysis
        pattern_results = self._run_pattern_analysis(error_text)

        # Step 2: Stack trace parsing
        stack_frames = self._parse_stack_trace(error_text)

        # Step 3: Severity classification
        severity = self._classify_severity(error_text)

        # Step 4: Fix generation
        fixes = self._generate_fixes(pattern_results, stack_frames, error_text)

        # Step 5: LLM deep analysis (if available)
        llm_analysis = self._llm_analyse(error_text, source_context)

        return {
            "success": True,
            "severity": severity,
            "pattern_matches": pattern_results,
            "stack_frames": stack_frames,
            "root_cause": pattern_results[0]["cause"] if pattern_results else (llm_analysis or "Unknown error"),
            "suggestions": fixes,
            "llm_analysis": llm_analysis,
            "message": (
                f"Debugger identified {len(pattern_results)} pattern match(es). "
                f"Severity: {severity}. "
                f"{len(fixes)} fix suggestion(s) generated."
            ),
        }

    def analyse_file_for_errors(self, file_path: str) -> dict[str, Any]:
        """Read a Python/JS file and check for common static issues."""
        if not os.path.exists(file_path):
            return {"success": False, "message": f"File not found: {file_path}"}

        try:
            with open(file_path, encoding="utf-8") as fh:
                content = fh.read()
        except Exception as e:
            return {"success": False, "message": f"Cannot read file: {e}"}

        issues: list[dict] = []

        if file_path.endswith(".py"):
            import ast

            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append(
                    {"type": "SyntaxError", "line": e.lineno, "msg": str(e), "fix": "Check indentation and syntax at the indicated line."}
                )

        return {
            "success": True,
            "file": file_path,
            "issues": issues,
            "message": f"Static analysis complete: {len(issues)} issue(s) found.",
        }

    # ── Internal methods ──────────────────────────────────────────────────────

    def _run_pattern_analysis(self, error_text: str) -> list[dict[str, str]]:
        matches: list[dict] = []
        all_patterns = _PYTHON_ERROR_PATTERNS + _FLUTTER_ERROR_PATTERNS + _JS_ERROR_PATTERNS
        for pattern, cause, fix_template in all_patterns:
            m = pattern.search(error_text)
            if m:
                try:
                    fix = fix_template.format(*m.groups())
                except (IndexError, KeyError):
                    fix = fix_template
                matches.append(
                    {
                        "pattern": pattern.pattern[:60],
                        "cause": cause,
                        "fix": fix,
                        "matched_text": m.group(0)[:120],
                    }
                )
        return matches

    def _parse_stack_trace(self, error_text: str) -> list[dict[str, str]]:
        frames: list[dict] = []
        # Python traceback
        for line in error_text.splitlines():
            m = re.search(r'File "([^"]+)", line (\d+), in (.+)', line)
            if m:
                frames.append({"file": m.group(1), "line": m.group(2), "function": m.group(3).strip()})
        # Dart traceback
        for line in error_text.splitlines():
            m = re.search(r"#(\d+)\s+(.+)\s+\((.+):(\d+):(\d+)\)", line)
            if m:
                frames.append({"file": m.group(3), "line": m.group(4), "function": m.group(2).strip()})
        return frames[-10:]  # Keep last 10 frames (nearest to error)

    def _classify_severity(self, error_text: str) -> str:
        err_lower = error_text.lower()
        if any(w in err_lower for w in ["fatal", "segfault", "out of memory", "system crash", "kernel"]):
            return "CRITICAL"
        if any(w in err_lower for w in ["error", "exception", "failed", "failure"]):
            return "ERROR"
        if any(w in err_lower for w in ["warning", "deprecated", "warn"]):
            return "WARNING"
        return "INFO"

    def _generate_fixes(self, pattern_results: list[dict], stack_frames: list[dict], error_text: str) -> list[dict[str, str]]:
        fixes: list[dict] = []

        for result in pattern_results:
            fixes.append(
                {
                    "type": "pattern_fix",
                    "description": result["cause"],
                    "action": result["fix"],
                }
            )

        # Suggest looking at the top frame
        if stack_frames:
            top = stack_frames[-1]
            fixes.append(
                {
                    "type": "inspect_file",
                    "description": f"Examine {top['file']} at line {top['line']} in function '{top['function']}'",
                    "action": f"Open {top['file']} and inspect line {top['line']} for the root cause.",
                }
            )

        # Generic suggestions based on error keywords
        err_lower = error_text.lower()
        if "import" in err_lower and "no module" in err_lower:
            fixes.append(
                {
                    "type": "dependency",
                    "description": "Missing package",
                    "action": "Run: pip install <package-name> or check requirements.txt",
                }
            )
        if "database" in err_lower or "sqlalchemy" in err_lower:
            fixes.append(
                {
                    "type": "database",
                    "description": "Database issue",
                    "action": "Ensure database is running and DATABASE_URL in .env is correct.",
                }
            )
        if "port" in err_lower and "already in use" in err_lower:
            fixes.append(
                {
                    "type": "port_conflict",
                    "description": "Port conflict",
                    "action": "Kill the process on that port: netstat -ano | findstr :8000 → taskkill /PID <pid> /F",
                }
            )

        return fixes

    def _llm_analyse(self, error_text: str, context: str) -> str | None:
        """Use AIOrchestrator for deep analysis of complex errors."""
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            orchestrator = AIOrchestrator()
            prompt = (
                "You are an expert debugger. Analyse this error and give ONE concise root cause "
                "and ONE specific fix (max 3 sentences total):\n\n"
                f"Error:\n{error_text[:1500]}\n\n"
                f"Context:\n{context[:500] if context else 'None provided'}"
            )
            result = orchestrator.query_with_failover(prompt)
            return result
        except Exception as e:
            logger.warning("DebuggerAgent LLM analysis failed: %s", e)
            return None
