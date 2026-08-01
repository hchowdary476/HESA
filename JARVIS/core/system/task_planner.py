"""Autonomous Task Planner - Breaks down natural language goals into Directed Acyclic Graphs (DAG) of subtasks executed concurrently."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from JARVIS.core.ai_router.multi_agent_system import AgentManager
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("task_planner")


# ---------------------------------------------------------------------------
# Goal Template Library — 12 expanded autonomous workflow templates
# ---------------------------------------------------------------------------


def _goal_python_dev_environment() -> list[dict]:
    """Prepare a Python development environment end-to-end."""
    return [
        {
            "id": "PDE1",
            "agent": "windows_system_agent",
            "prompt": "Open VS Code and the project workspace folder",
            "dependencies": [],
            "required_tools": ["app_launcher"],
            "estimated_duration": 3.0,
            "success_criteria": "VS Code is open with project folder",
            "rollback_strategy": "close vscode",
            "status": "QUEUED",
        },
        {
            "id": "PDE2",
            "agent": "memory_agent",
            "prompt": "Restore previous session notes and context from memory",
            "dependencies": ["PDE1"],
            "required_tools": ["memory_reader"],
            "estimated_duration": 1.0,
            "success_criteria": "Session context loaded",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "PDE3",
            "agent": "windows_system_agent",
            "prompt": "Open a new terminal window in the project directory",
            "dependencies": ["PDE1"],
            "required_tools": ["terminal_launcher"],
            "estimated_duration": 1.5,
            "success_criteria": "Terminal open at project path",
            "rollback_strategy": "close terminal",
            "status": "QUEUED",
        },
        {
            "id": "PDE4",
            "agent": "ai_and_ml_agent",
            "prompt": "Start Ollama local AI model endpoint and verify it is reachable",
            "dependencies": ["PDE1"],
            "required_tools": ["ollama_launcher"],
            "estimated_duration": 5.0,
            "success_criteria": "Ollama API responding on port 11434",
            "rollback_strategy": "stop ollama",
            "status": "QUEUED",
        },
        {
            "id": "PDE5",
            "agent": "developer_agent",
            "prompt": "Check if Python virtual environment exists; create it if missing",
            "dependencies": ["PDE3"],
            "required_tools": ["venv_creator"],
            "estimated_duration": 3.0,
            "success_criteria": "Virtual environment active",
            "rollback_strategy": "remove venv",
            "status": "QUEUED",
        },
        {
            "id": "PDE6",
            "agent": "developer_agent",
            "prompt": "Install all requirements from requirements.txt",
            "dependencies": ["PDE5"],
            "required_tools": ["pip_installer"],
            "estimated_duration": 10.0,
            "success_criteria": "All packages installed without errors",
            "rollback_strategy": "rollback package installs",
            "status": "QUEUED",
        },
        {
            "id": "PDE7",
            "agent": "windows_system_agent",
            "prompt": "Open Git and check repository status",
            "dependencies": ["PDE2"],
            "required_tools": ["git_status"],
            "estimated_duration": 1.5,
            "success_criteria": "Git status is clean or staged",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "PDE8",
            "agent": "developer_agent",
            "prompt": "Run project diagnostics and quick test suite",
            "dependencies": ["PDE6", "PDE4"],
            "required_tools": ["diagnostics_runner", "pytest_runner"],
            "estimated_duration": 8.0,
            "success_criteria": "All tests pass",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "PDE9",
            "agent": "developer_agent",
            "prompt": "Launch the local development server",
            "dependencies": ["PDE8"],
            "required_tools": ["server_launcher"],
            "estimated_duration": 4.0,
            "success_criteria": "Development server running",
            "rollback_strategy": "stop server",
            "status": "QUEUED",
        },
        {
            "id": "PDE10",
            "agent": "research_agent",
            "prompt": "Open project documentation in the browser",
            "dependencies": ["PDE9"],
            "required_tools": ["browser_open"],
            "estimated_duration": 1.0,
            "success_criteria": "Documentation page loaded",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "PDE11",
            "agent": "windows_system_agent",
            "prompt": "Announce via voice: Development environment is fully prepared, sir.",
            "dependencies": ["PDE10"],
            "required_tools": ["tts_output"],
            "estimated_duration": 1.0,
            "success_criteria": "Voice announcement made",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_deploy_application() -> list[dict]:
    """Full deploy pipeline: test → build → commit → push → deploy → verify → report."""
    return [
        {
            "id": "DEP1",
            "agent": "developer_agent",
            "prompt": "Run full test suite and analyse any failures",
            "dependencies": [],
            "required_tools": ["pytest_runner"],
            "estimated_duration": 15.0,
            "success_criteria": "All tests pass with zero failures",
            "rollback_strategy": "abort deployment",
            "status": "QUEUED",
        },
        {
            "id": "DEP2",
            "agent": "developer_agent",
            "prompt": "Build the application production bundle",
            "dependencies": ["DEP1"],
            "required_tools": ["build_runner"],
            "estimated_duration": 8.0,
            "success_criteria": "Build artifacts generated successfully",
            "rollback_strategy": "clean build dir",
            "status": "QUEUED",
        },
        {
            "id": "DEP3",
            "agent": "developer_agent",
            "prompt": "Stage and commit all changes with auto-generated commit message",
            "dependencies": ["DEP2"],
            "required_tools": ["git_commit"],
            "estimated_duration": 2.0,
            "success_criteria": "Changes committed to local repo",
            "rollback_strategy": "git reset HEAD",
            "status": "QUEUED",
        },
        {
            "id": "DEP4",
            "agent": "developer_agent",
            "prompt": "Push to remote origin main branch",
            "dependencies": ["DEP3"],
            "required_tools": ["git_push"],
            "estimated_duration": 3.0,
            "success_criteria": "Push succeeded",
            "rollback_strategy": "git revert",
            "status": "QUEUED",
        },
        {
            "id": "DEP5",
            "agent": "developer_agent",
            "prompt": "Deploy application to production environment",
            "dependencies": ["DEP4"],
            "required_tools": ["deploy_runner"],
            "estimated_duration": 20.0,
            "success_criteria": "Deployment health check returns 200 OK",
            "rollback_strategy": "rollback to previous deployment",
            "status": "QUEUED",
        },
        {
            "id": "DEP6",
            "agent": "cyber_security_agent",
            "prompt": "Verify deployment endpoint security and response integrity",
            "dependencies": ["DEP5"],
            "required_tools": ["endpoint_checker"],
            "estimated_duration": 3.0,
            "success_criteria": "Endpoint is reachable and returns valid responses",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "DEP7",
            "agent": "coding_agent",
            "prompt": "Generate a deployment completion report",
            "dependencies": ["DEP6"],
            "required_tools": ["report_generator"],
            "estimated_duration": 2.0,
            "success_criteria": "Report saved to logs",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "DEP8",
            "agent": "windows_system_agent",
            "prompt": "Announce via voice: Deployment completed successfully, sir.",
            "dependencies": ["DEP7"],
            "required_tools": ["tts_output"],
            "estimated_duration": 1.0,
            "success_criteria": "Announcement made",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_research_mode(topic: str) -> list[dict]:
    """AI Research Mode: search → summarise → compare → report → save."""
    return [
        {
            "id": "RES1",
            "agent": "research_agent",
            "prompt": f"Search multiple sources for information on: {topic}",
            "dependencies": [],
            "required_tools": ["web_searcher"],
            "estimated_duration": 5.0,
            "success_criteria": "At least 5 relevant sources found",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "RES2",
            "agent": "research_agent",
            "prompt": f"Summarise the top findings on: {topic}",
            "dependencies": ["RES1"],
            "required_tools": ["research_engine"],
            "estimated_duration": 4.0,
            "success_criteria": "Summary generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "RES3",
            "agent": "ai_and_ml_agent",
            "prompt": f"Compare and contrast the major models or approaches found regarding: {topic}",
            "dependencies": ["RES1"],
            "required_tools": ["debate_runner"],
            "estimated_duration": 6.0,
            "success_criteria": "Comparison table generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "RES4",
            "agent": "coding_agent",
            "prompt": "Generate a structured research report combining all findings",
            "dependencies": ["RES2", "RES3"],
            "required_tools": ["report_generator"],
            "estimated_duration": 3.0,
            "success_criteria": "Research report saved",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "RES5",
            "agent": "memory_agent",
            "prompt": f"Save research notes and update knowledge graph with findings on: {topic}",
            "dependencies": ["RES4"],
            "required_tools": ["note_saver"],
            "estimated_duration": 1.0,
            "success_criteria": "Notes saved and knowledge graph updated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "RES6",
            "agent": "windows_system_agent",
            "prompt": "Announce via voice: Research complete. Report is ready for review, sir.",
            "dependencies": ["RES5"],
            "required_tools": ["tts_output"],
            "estimated_duration": 1.0,
            "success_criteria": "Announcement made",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_security_audit() -> list[dict]:
    """Comprehensive security audit: ports → logs → CVE → compliance → report."""
    return [
        {
            "id": "SEC1",
            "agent": "cyber_security_agent",
            "prompt": "Scan all active network ports and identify open services",
            "dependencies": [],
            "required_tools": ["port_scanner"],
            "estimated_duration": 5.0,
            "success_criteria": "Port scan complete",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "SEC2",
            "agent": "cyber_security_agent",
            "prompt": "Audit Windows system event logs for suspicious activity",
            "dependencies": [],
            "required_tools": ["log_auditor"],
            "estimated_duration": 4.0,
            "success_criteria": "Event logs analysed",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "SEC3",
            "agent": "cyber_security_agent",
            "prompt": "Check for known CVEs in installed software versions",
            "dependencies": ["SEC1"],
            "required_tools": ["cve_lookup"],
            "estimated_duration": 6.0,
            "success_criteria": "CVE database checked",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "SEC4",
            "agent": "windows_system_agent",
            "prompt": "Verify active security shield policies and firewall rules",
            "dependencies": ["SEC1"],
            "required_tools": ["firewall_checker"],
            "estimated_duration": 2.0,
            "success_criteria": "Security policies verified",
            "rollback_strategy": "restore default policies",
            "status": "QUEUED",
        },
        {
            "id": "SEC5",
            "agent": "cyber_security_agent",
            "prompt": "Generate security compliance and risk assessment report",
            "dependencies": ["SEC2", "SEC3", "SEC4"],
            "required_tools": ["report_generator"],
            "estimated_duration": 3.0,
            "success_criteria": "Security report generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "SEC6",
            "agent": "windows_system_agent",
            "prompt": "Announce via voice: Security audit complete. Threat report ready, sir.",
            "dependencies": ["SEC5"],
            "required_tools": ["tts_output"],
            "estimated_duration": 1.0,
            "success_criteria": "Announcement made",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_system_cleanup() -> list[dict]:
    """System cleanup: temp files → cache → logs → disk report."""
    return [
        {
            "id": "CLN1",
            "agent": "windows_system_agent",
            "prompt": "Clean Windows temporary files and clear the Temp folder",
            "dependencies": [],
            "required_tools": ["clean_temp"],
            "estimated_duration": 3.0,
            "success_criteria": "Temp files removed",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "CLN2",
            "agent": "windows_system_agent",
            "prompt": "Clear browser cache and application cache files",
            "dependencies": [],
            "required_tools": ["cache_cleaner"],
            "estimated_duration": 2.0,
            "success_criteria": "Caches cleared",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "CLN3",
            "agent": "windows_system_agent",
            "prompt": "Rotate and compress old log files",
            "dependencies": ["CLN1"],
            "required_tools": ["log_rotator"],
            "estimated_duration": 2.0,
            "success_criteria": "Old logs rotated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "CLN4",
            "agent": "windows_system_agent",
            "prompt": "Announce via voice: System cleanup complete, sir.",
            "dependencies": ["CLN2", "CLN3"],
            "required_tools": ["tts_output"],
            "estimated_duration": 1.0,
            "success_criteria": "Announcement made",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_backup_project() -> list[dict]:
    """Project backup: commit → archive → verify → confirm."""
    return [
        {
            "id": "BAK1",
            "agent": "developer_agent",
            "prompt": "Stage and commit all uncommitted changes before backup",
            "dependencies": [],
            "required_tools": ["git_commit"],
            "estimated_duration": 2.0,
            "success_criteria": "All changes committed",
            "rollback_strategy": "git stash",
            "status": "QUEUED",
        },
        {
            "id": "BAK2",
            "agent": "windows_system_agent",
            "prompt": "Create a ZIP archive of the current project directory",
            "dependencies": ["BAK1"],
            "required_tools": ["file_backup"],
            "estimated_duration": 5.0,
            "success_criteria": "Backup archive created",
            "rollback_strategy": "remove archive",
            "status": "QUEUED",
        },
        {
            "id": "BAK3",
            "agent": "windows_system_agent",
            "prompt": "Verify backup archive integrity and report file count",
            "dependencies": ["BAK2"],
            "required_tools": ["file_verifier"],
            "estimated_duration": 2.0,
            "success_criteria": "Archive is valid and readable",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "BAK4",
            "agent": "windows_system_agent",
            "prompt": "Announce via voice: Project backup completed successfully, sir.",
            "dependencies": ["BAK3"],
            "required_tools": ["tts_output"],
            "estimated_duration": 1.0,
            "success_criteria": "Announcement made",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_morning_briefing() -> list[dict]:
    """Morning briefing: time → system health → memory summary → suggestions → announce."""
    return [
        {
            "id": "MRN1",
            "agent": "windows_system_agent",
            "prompt": "Get current time, date, and system uptime",
            "dependencies": [],
            "required_tools": ["get_time"],
            "estimated_duration": 0.5,
            "success_criteria": "Time retrieved",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "MRN2",
            "agent": "windows_system_agent",
            "prompt": "Run system health diagnostics: CPU, RAM, disk, battery",
            "dependencies": [],
            "required_tools": ["diagnostics_runner"],
            "estimated_duration": 3.0,
            "success_criteria": "System health report generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "MRN3",
            "agent": "memory_agent",
            "prompt": "Retrieve memory summary and most recent session notes",
            "dependencies": [],
            "required_tools": ["memory_reader"],
            "estimated_duration": 1.0,
            "success_criteria": "Memory summary loaded",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "MRN4",
            "agent": "research_agent",
            "prompt": "Fetch top headlines and any pending system alerts",
            "dependencies": ["MRN1"],
            "required_tools": ["web_searcher"],
            "estimated_duration": 2.0,
            "success_criteria": "News fetched",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "MRN5",
            "agent": "windows_system_agent",
            "prompt": "Announce full morning briefing via voice: date, health, summary, suggestions",
            "dependencies": ["MRN2", "MRN3", "MRN4"],
            "required_tools": ["tts_output"],
            "estimated_duration": 2.0,
            "success_criteria": "Briefing announced",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_network_diagnostics() -> list[dict]:
    """Network diagnostics: ping → speed → ports → wifi → report."""
    return [
        {
            "id": "NET1",
            "agent": "cyber_security_agent",
            "prompt": "Ping gateway and key DNS servers, measure latency",
            "dependencies": [],
            "required_tools": ["ping_tool"],
            "estimated_duration": 3.0,
            "success_criteria": "Ping results collected",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "NET2",
            "agent": "cyber_security_agent",
            "prompt": "Check WiFi signal strength and connected network",
            "dependencies": [],
            "required_tools": ["wifi_checker"],
            "estimated_duration": 1.0,
            "success_criteria": "WiFi info retrieved",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "NET3",
            "agent": "cyber_security_agent",
            "prompt": "Scan for open ports and suspicious listening services",
            "dependencies": ["NET1"],
            "required_tools": ["port_scanner"],
            "estimated_duration": 5.0,
            "success_criteria": "Port scan complete",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "NET4",
            "agent": "windows_system_agent",
            "prompt": "Announce via voice: Network diagnostics complete, sir.",
            "dependencies": ["NET2", "NET3"],
            "required_tools": ["tts_output"],
            "estimated_duration": 1.0,
            "success_criteria": "Announcement made",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_full_stack() -> list[dict]:
    """Autonomous software engineering: full stack React + FastAPI app."""
    return [
        {
            "id": "SEF1",
            "agent": "architect_agent",
            "prompt": "Analyze requirements and tech stack selection",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 5.0,
            "success_criteria": "Architecture spec generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "SEF2",
            "agent": "backend_agent",
            "prompt": "Generate REST API, database models, and auth endpoints",
            "dependencies": ["SEF1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 12.0,
            "success_criteria": "FastAPI backend code written",
            "rollback_strategy": "remove backend",
            "status": "QUEUED",
        },
        {
            "id": "SEF3",
            "agent": "frontend_agent",
            "prompt": "Generate React/Next.js frontend UI pages and services",
            "dependencies": ["SEF1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 15.0,
            "success_criteria": "React frontend code written",
            "rollback_strategy": "remove frontend",
            "status": "QUEUED",
        },
        {
            "id": "SEF4",
            "agent": "testing_agent",
            "prompt": "Generate pytest and Vitest unit/integration tests",
            "dependencies": ["SEF2", "SEF3"],
            "required_tools": ["code_gen"],
            "estimated_duration": 10.0,
            "success_criteria": "Tests generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "SEF5",
            "agent": "debugger_agent",
            "prompt": "Verify generated code structure and check syntax",
            "dependencies": ["SEF4"],
            "required_tools": ["code_gen"],
            "estimated_duration": 5.0,
            "success_criteria": "Zero syntax errors found",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "SEF6",
            "agent": "devops_agent",
            "prompt": "Generate Dockerfiles and docker-compose configurations",
            "dependencies": ["SEF5"],
            "required_tools": ["code_gen"],
            "estimated_duration": 6.0,
            "success_criteria": "Docker files created",
            "rollback_strategy": "remove docker configs",
            "status": "QUEUED",
        },
        {
            "id": "SEF7",
            "agent": "documentation_agent",
            "prompt": "Generate README, API docs, and architecture diagrams",
            "dependencies": ["SEF6"],
            "required_tools": ["code_gen"],
            "estimated_duration": 5.0,
            "success_criteria": "Docs created",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_api() -> list[dict]:
    """Autonomous software engineering: REST API backend."""
    return [
        {
            "id": "API1",
            "agent": "architect_agent",
            "prompt": "Analyze backend REST API requirements",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Architecture spec generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "API2",
            "agent": "backend_agent",
            "prompt": "Generate REST API controllers, database models, and JWT schemas",
            "dependencies": ["API1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 10.0,
            "success_criteria": "API controllers written",
            "rollback_strategy": "remove backend",
            "status": "QUEUED",
        },
        {
            "id": "API3",
            "agent": "testing_agent",
            "prompt": "Generate pytest suite for API routes",
            "dependencies": ["API2"],
            "required_tools": ["code_gen"],
            "estimated_duration": 6.0,
            "success_criteria": "Pytest files written",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "API4",
            "agent": "debugger_agent",
            "prompt": "Check code syntax and correct import issues",
            "dependencies": ["API3"],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Syntax validated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "API5",
            "agent": "devops_agent",
            "prompt": "Generate API Dockerfile and docker-compose configurations",
            "dependencies": ["API4"],
            "required_tools": ["code_gen"],
            "estimated_duration": 5.0,
            "success_criteria": "Docker configs written",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "API6",
            "agent": "documentation_agent",
            "prompt": "Generate README and Swagger API docs",
            "dependencies": ["API5"],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Documentation complete",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_mobile() -> list[dict]:
    """Autonomous software engineering: Mobile Flutter App."""
    return [
        {
            "id": "MOB1",
            "agent": "architect_agent",
            "prompt": "Analyze mobile Flutter app specifications",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Architecture spec generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "MOB2",
            "agent": "mobile_agent",
            "prompt": "Generate Flutter App scaffolds, screens, providers, and models",
            "dependencies": ["MOB1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 12.0,
            "success_criteria": "Flutter Dart files generated",
            "rollback_strategy": "remove mobile",
            "status": "QUEUED",
        },
        {
            "id": "MOB3",
            "agent": "testing_agent",
            "prompt": "Generate test suite for Flutter pages and models",
            "dependencies": ["MOB2"],
            "required_tools": ["code_gen"],
            "estimated_duration": 6.0,
            "success_criteria": "Flutter test files generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "MOB4",
            "agent": "debugger_agent",
            "prompt": "Verify Gradle and signing configurations",
            "dependencies": ["MOB3"],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Gradle checked",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "MOB5",
            "agent": "documentation_agent",
            "prompt": "Generate project README and build instructions",
            "dependencies": ["MOB4"],
            "required_tools": ["code_gen"],
            "estimated_duration": 3.0,
            "success_criteria": "README generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_ml() -> list[dict]:
    """Autonomous software engineering: ML Pipeline."""
    return [
        {
            "id": "ML1",
            "agent": "architect_agent",
            "prompt": "Analyze Machine Learning pipeline goals",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Architecture spec generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "ML2",
            "agent": "ai_and_ml_agent",
            "prompt": "Generate dataset processing, model architecture, and train/eval scripts",
            "dependencies": ["ML1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 10.0,
            "success_criteria": "ML pipeline files generated",
            "rollback_strategy": "remove ml",
            "status": "QUEUED",
        },
        {
            "id": "ML3",
            "agent": "testing_agent",
            "prompt": "Generate tests for dataset pipeline and model inference",
            "dependencies": ["ML2"],
            "required_tools": ["code_gen"],
            "estimated_duration": 5.0,
            "success_criteria": "ML tests generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "ML4",
            "agent": "documentation_agent",
            "prompt": "Generate pipeline description and local run instructions",
            "dependencies": ["ML3"],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "README generated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_debug() -> list[dict]:
    """Autonomous software engineering: Debugger flow."""
    return [
        {
            "id": "DBG1",
            "agent": "debugger_agent",
            "prompt": "Read error strings, stack traces, compiler output to find root cause",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Root cause analyzed",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "DBG2",
            "agent": "testing_agent",
            "prompt": "Run pytest/test runner to reproduce the issue",
            "dependencies": ["DBG1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 5.0,
            "success_criteria": "Tests run completed",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "DBG3",
            "agent": "debugger_agent",
            "prompt": "Apply safe line fixes or dependency updates",
            "dependencies": ["DBG2"],
            "required_tools": ["code_gen"],
            "estimated_duration": 6.0,
            "success_criteria": "Fix applied",
            "rollback_strategy": "rollback fix",
            "status": "QUEUED",
        },
        {
            "id": "DBG4",
            "agent": "documentation_agent",
            "prompt": "Produce debug report and changelog entry",
            "dependencies": ["DBG3"],
            "required_tools": ["code_gen"],
            "estimated_duration": 3.0,
            "success_criteria": "Debug report written",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_tests() -> list[dict]:
    """Autonomous software engineering: Test Generation."""
    return [
        {
            "id": "TST1",
            "agent": "testing_agent",
            "prompt": "Read source files and generate unit test suites",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 8.0,
            "success_criteria": "Unit tests written",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "TST2",
            "agent": "debugger_agent",
            "prompt": "Verify tests run successfully without syntax issues",
            "dependencies": ["TST1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Tests syntax validated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "TST3",
            "agent": "documentation_agent",
            "prompt": "Update coverage report and README",
            "dependencies": ["TST2"],
            "required_tools": ["code_gen"],
            "estimated_duration": 3.0,
            "success_criteria": "Docs updated",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_docs() -> list[dict]:
    """Autonomous software engineering: Documentation generation."""
    return [
        {
            "id": "DOC1",
            "agent": "documentation_agent",
            "prompt": "Scan workspace and generate API_DOCS, README, and ARCHITECTURE diagrams",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 6.0,
            "success_criteria": "Markdown documentation created",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "DOC2",
            "agent": "documentation_agent",
            "prompt": "Format files and save markdown artifacts to docs/ directory",
            "dependencies": ["DOC1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "Docs formatted and saved",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


def _goal_se_devops() -> list[dict]:
    """Autonomous software engineering: DevOps setup."""
    return [
        {
            "id": "DEV1",
            "agent": "devops_agent",
            "prompt": "Generate Dockerfiles and docker-compose configurations",
            "dependencies": [],
            "required_tools": ["code_gen"],
            "estimated_duration": 6.0,
            "success_criteria": "Docker files generated",
            "rollback_strategy": "remove docker files",
            "status": "QUEUED",
        },
        {
            "id": "DEV2",
            "agent": "devops_agent",
            "prompt": "Generate CI/CD GitHub Actions workflows",
            "dependencies": ["DEV1"],
            "required_tools": ["code_gen"],
            "estimated_duration": 4.0,
            "success_criteria": "CI/CD configurations created",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
        {
            "id": "DEV3",
            "agent": "documentation_agent",
            "prompt": "Generate DEPLOYMENT guide",
            "dependencies": ["DEV2"],
            "required_tools": ["code_gen"],
            "estimated_duration": 3.0,
            "success_criteria": "Deployment guide written",
            "rollback_strategy": "none",
            "status": "QUEUED",
        },
    ]


# ---------------------------------------------------------------------------
# Semantic Goal Matcher
# ---------------------------------------------------------------------------

_GOAL_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("python development environment", "prepare my python", "setup python", "prepare python"), "python_dev_env"),
    (("deploy", "ship the app", "deploy application", "deploy my app", "push to production"), "deploy_app"),
    (("research", "investigate", "find out about", "latest ai", "latest ml", "multimodal", "latest models"), "research"),
    (
        ("security audit", "check vulnerabilities", "audit security", "scan for vulnerabilities", "security check", "run security"),
        "security_audit",
    ),
    (("clean up", "cleanup", "clean temp", "clean the system", "clear cache", "clean my pc"), "system_cleanup"),
    (("backup my project", "backup project", "create backup", "save backup", "backup the code"), "backup_project"),
    (("morning briefing", "daily briefing", "good morning", "start of day", "daily summary"), "morning_briefing"),
    (("network diagnostics", "check network", "internet diagnostics", "check my network", "network check"), "network_diagnostics"),
    # Software Engineering new templates
    (("build a web app", "create a website", "full-stack app", "full stack"), "se_full_stack"),
    (("build an api", "create fastapi", "create flask", "rest api"), "se_api"),
    (("build a flutter app", "create mobile app", "mobile client"), "se_mobile"),
    (("build an ml model", "train a model", "create ai pipeline", "ml pipeline"), "se_ml"),
    (("debug this", "fix this error", "analyze stack trace"), "se_debug"),
    (("write tests", "generate unit tests"), "se_tests"),
    (("write documentation", "generate readme"), "se_docs"),
    (("dockerize", "setup ci/cd", "create github actions"), "se_devops"),
    # Legacy patterns (kept from original)
    (("ai project", "prepare env"), "python_dev_env"),
    (("development environment",), "legacy_dev_env"),
]


def _classify_goal_template(goal: str) -> str:
    """Return a template key for the given goal string, or 'generic'."""
    g = goal.lower()
    for patterns, key in _GOAL_PATTERNS:
        for p in patterns:
            if p in g:
                return key
    return "generic"


def _extract_topic(goal: str) -> str:
    """Extract research topic from a goal string."""
    # Try 'research X', 'investigate X', 'find out about X'
    for verb in ("research ", "investigate ", "find out about ", "latest "):
        idx = goal.lower().find(verb)
        if idx != -1:
            return goal[idx + len(verb) :].strip()
    return goal


class TaskPlanner:
    """Ingests complex goals, translates them into DAG plans, and coordinates concurrent executions."""

    _instance: TaskPlanner | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> TaskPlanner:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.active_plans: dict[str, dict[str, Any]] = {}
        self.agent_mgr = AgentManager()
        self.plan_lock = threading.Lock()

    def create_plan(self, goal: str) -> str:
        """Decompose a high-level goal into a Directed Acyclic Graph (DAG) of tasks.

        Uses the expanded 12-template goal library first, then falls back to the
        original hardcoded plans for backward compatibility, then to a generic
        single-task plan for any unrecognised goal.
        """
        plan_id = f"PLAN-{uuid.uuid4().hex[:6].upper()}"
        lowered_goal = goal.lower()
        subtasks = []

        # ── Template dispatch (semantic goal matching) ─────────────────────
        template_key = _classify_goal_template(goal)

        if template_key == "python_dev_env":
            subtasks = _goal_python_dev_environment()
        elif template_key == "deploy_app":
            subtasks = _goal_deploy_application()
        elif template_key == "research":
            topic = _extract_topic(goal)
            subtasks = _goal_research_mode(topic or goal)
        elif template_key == "security_audit":
            subtasks = _goal_security_audit()
        elif template_key == "system_cleanup":
            subtasks = _goal_system_cleanup()
        elif template_key == "backup_project":
            subtasks = _goal_backup_project()
        elif template_key == "morning_briefing":
            subtasks = _goal_morning_briefing()
        elif template_key == "network_diagnostics":
            subtasks = _goal_network_diagnostics()
        elif template_key == "se_full_stack":
            subtasks = _goal_se_full_stack()
        elif template_key == "se_api":
            subtasks = _goal_se_api()
        elif template_key == "se_mobile":
            subtasks = _goal_se_mobile()
        elif template_key == "se_ml":
            subtasks = _goal_se_ml()
        elif template_key == "se_debug":
            subtasks = _goal_se_debug()
        elif template_key == "se_tests":
            subtasks = _goal_se_tests()
        elif template_key == "se_docs":
            subtasks = _goal_se_docs()
        elif template_key == "se_devops":
            subtasks = _goal_se_devops()
        elif "ai project" in lowered_goal or "prepare ai env" in lowered_goal:
            # High-fidelity project preparation DAG
            subtasks = [
                {
                    "id": "A",
                    "agent": "windows_system_agent",
                    "prompt": "Open project workspace folder",
                    "dependencies": [],
                    "required_tools": ["os_shell"],
                    "estimated_duration": 2.0,
                    "success_criteria": "Workspace folder is open",
                    "rollback_strategy": "close workspace",
                    "status": "QUEUED",
                },
                {
                    "id": "B",
                    "agent": "memory_agent",
                    "prompt": "Restore previous session details",
                    "dependencies": ["A"],
                    "required_tools": ["file_reader"],
                    "estimated_duration": 1.5,
                    "success_criteria": "Previous session files restored",
                    "rollback_strategy": "clear buffer",
                    "status": "QUEUED",
                },
                {
                    "id": "C",
                    "agent": "ai_and_ml_agent",
                    "prompt": "Start local AI model endpoint",
                    "dependencies": ["A"],
                    "required_tools": ["model_hub"],
                    "estimated_duration": 5.0,
                    "success_criteria": "Ollama local API is reachable",
                    "rollback_strategy": "stop ollama",
                    "status": "QUEUED",
                },
                {
                    "id": "D",
                    "agent": "developer_agent",
                    "prompt": "Verify package dependencies",
                    "dependencies": ["B"],
                    "required_tools": ["pip_command"],
                    "estimated_duration": 3.0,
                    "success_criteria": "All requirements satisfied",
                    "rollback_strategy": "rollback package updates",
                    "status": "QUEUED",
                },
                {
                    "id": "E",
                    "agent": "developer_agent",
                    "prompt": "Launch backend local webserver",
                    "dependencies": ["C", "D"],
                    "required_tools": ["process_spawn"],
                    "estimated_duration": 4.0,
                    "success_criteria": "Backend listening on port 8000",
                    "rollback_strategy": "kill backend process",
                    "status": "QUEUED",
                },
                {
                    "id": "F",
                    "agent": "automation_agent",
                    "prompt": "Launch frontend dev server",
                    "dependencies": ["E"],
                    "required_tools": ["process_spawn"],
                    "estimated_duration": 3.5,
                    "success_criteria": "NPM dev listening on port 3000",
                    "rollback_strategy": "kill node process",
                    "status": "QUEUED",
                },
                {
                    "id": "G",
                    "agent": "research_agent",
                    "prompt": "Open project documentation page",
                    "dependencies": ["F"],
                    "required_tools": ["browser_open"],
                    "estimated_duration": 1.0,
                    "success_criteria": "Documentation page loaded in browser",
                    "rollback_strategy": "close browser tab",
                    "status": "QUEUED",
                },
            ]
        elif "development environment" in lowered_goal or "prepare env" in lowered_goal:
            # Predefined 4-step plan for development environment test
            subtasks = [
                {
                    "id": "D1",
                    "agent": "windows_system_agent",
                    "prompt": "verify VSCode is installed and check active workspace",
                    "dependencies": [],
                    "required_tools": ["os_shell"],
                    "estimated_duration": 2.0,
                    "success_criteria": "VSCode is verified",
                    "rollback_strategy": "none",
                    "status": "QUEUED",
                },
                {
                    "id": "D2",
                    "agent": "memory_agent",
                    "prompt": "check for git configuration file in workspace",
                    "dependencies": ["D1"],
                    "required_tools": ["file_reader"],
                    "estimated_duration": 1.5,
                    "success_criteria": "Git configuration is verified",
                    "rollback_strategy": "none",
                    "status": "QUEUED",
                },
                {
                    "id": "D3",
                    "agent": "research_agent",
                    "prompt": "probe active internet connection and output ping latency",
                    "dependencies": ["D1"],
                    "required_tools": ["socket_ping"],
                    "estimated_duration": 1.0,
                    "success_criteria": "Internet connection verified",
                    "rollback_strategy": "none",
                    "status": "QUEUED",
                },
                {
                    "id": "D4",
                    "agent": "windows_system_agent",
                    "prompt": "announce 'Development environment is prepared, sir.'",
                    "dependencies": ["D2", "D3"],
                    "required_tools": ["audio_output"],
                    "estimated_duration": 1.0,
                    "success_criteria": "Announcement complete",
                    "rollback_strategy": "none",
                    "status": "QUEUED",
                },
            ]
        elif "security audit" in lowered_goal or "check vulnerabilities" in lowered_goal:
            # Security Audit DAG
            subtasks = [
                {
                    "id": "S1",
                    "agent": "cyber_security_agent",
                    "prompt": "Scan active network ports",
                    "dependencies": [],
                    "required_tools": ["port_scanner"],
                    "estimated_duration": 3.0,
                    "success_criteria": "Port scan complete, open ports listed",
                    "rollback_strategy": "clear temp scan results",
                    "status": "QUEUED",
                },
                {
                    "id": "S2",
                    "agent": "cyber_security_agent",
                    "prompt": "Audit windows system events logs",
                    "dependencies": ["S1"],
                    "required_tools": ["log_auditor"],
                    "estimated_duration": 2.5,
                    "success_criteria": "Event logs analyzed for suspicious activity",
                    "rollback_strategy": "release lock on logs",
                    "status": "QUEUED",
                },
                {
                    "id": "S3",
                    "agent": "windows_system_agent",
                    "prompt": "Audit running security shield policies",
                    "dependencies": ["S1"],
                    "required_tools": ["shield_policy_checker"],
                    "estimated_duration": 1.5,
                    "success_criteria": "Active policies confirmed healthy",
                    "rollback_strategy": "restore default policies",
                    "status": "QUEUED",
                },
            ]
        else:
            # Generic single-task DAG
            target_agent = self.agent_mgr.route_command(goal)
            subtasks = [
                {
                    "id": "T1",
                    "agent": target_agent,
                    "prompt": goal,
                    "dependencies": [],
                    "required_tools": ["general_tool"],
                    "estimated_duration": 2.0,
                    "success_criteria": "Command executed successfully",
                    "rollback_strategy": "none",
                    "status": "QUEUED",
                }
            ]

        with self.plan_lock:
            self.active_plans[plan_id] = {
                "goal": goal,
                "subtasks": subtasks,
                "completed": 0,
                "status": "QUEUED",
                "results": [],
                "max_retries": 2,
                "retry_count": {},
            }

        logger.info("Created task plan %s with %d steps for goal '%s'.", plan_id, len(subtasks), goal)
        return plan_id

    def execute_plan(self, plan_id: str) -> None:
        """Asynchronously schedule and run ready tasks concurrently."""
        with self.plan_lock:
            plan = self.active_plans.get(plan_id)
            if not plan:
                return
            plan["status"] = "RUNNING"

        logger.info("Starting execution of Plan %s...", plan_id)
        self._dispatch_ready_tasks(plan_id)

    def _dispatch_ready_tasks(self, plan_id: str) -> None:
        with self.plan_lock:
            plan = self.active_plans.get(plan_id)
            if not plan or plan["status"] not in ["RUNNING", "RETRYING"]:
                return

            completed_ids = {t["id"] for t in plan["subtasks"] if t["status"] == "COMPLETED"}

            # Check for total completion
            if all(t["status"] == "COMPLETED" for t in plan["subtasks"]):
                plan["status"] = "COMPLETED"
                logger.info("Plan %s completed successfully.", plan_id)
                return

            # Check if any task failed permanently
            if any(t["status"] == "FAILED" for t in plan["subtasks"]):
                plan["status"] = "FAILED"
                logger.error("Plan %s failed due to task failure.", plan_id)
                return

            # Scan and dispatch ready tasks
            for t in plan["subtasks"]:
                if t["status"] == "QUEUED":
                    deps_satisfied = all(dep in completed_ids for dep in t["dependencies"])
                    if deps_satisfied:
                        t["status"] = "RUNNING"
                        # Start dispatch in a separate thread so scheduler loop remains non-blocking
                        threading.Thread(target=self._dispatch_task_step, args=(plan_id, t), daemon=True).start()

    def _dispatch_task_step(self, plan_id: str, task_dict: dict) -> None:
        agent_key = task_dict["agent"]
        prompt = task_dict["prompt"]
        task_id = task_dict["id"]

        agent = self.agent_mgr.get_agent(agent_key)

        def _task_finished(report: dict):
            with self.plan_lock:
                plan = self.active_plans.get(plan_id)
                if not plan:
                    return

                if report.get("success", False):
                    task_dict["status"] = "COMPLETED"
                    plan["results"].append(report)
                    plan["completed"] += 1
                    logger.info("Task %s (Plan %s) finished successfully.", task_id, plan_id)
                else:
                    retries = plan["retry_count"].get(task_id, 0)
                    if retries < plan["max_retries"]:
                        plan["retry_count"][task_id] = retries + 1
                        task_dict["status"] = "QUEUED"
                        logger.info("Retrying task %s (Plan %s) (Attempt %d/%d).", task_id, plan_id, retries + 1, plan["max_retries"])
                    else:
                        task_dict["status"] = "FAILED"
                        logger.error(
                            "Task %s (Plan %s) failed after max retries. Rollback strategy: %s.",
                            task_id,
                            plan_id,
                            task_dict["rollback_strategy"],
                        )

            # Recurse check for next wave
            self._dispatch_ready_tasks(plan_id)

        if agent:
            agent.add_task(f"TASK-{plan_id}-{task_id}", prompt, _task_finished)
            # Run the agent work cycle in a background thread if it is not currently processing
            # (In a real service loop it processes, but for unit test simulation we invoke manually)
            threading.Thread(target=agent.execute_next_task, daemon=True).start()
        else:
            logger.warning("No agent found for %s, bypassing.", agent_key)
            _task_finished({"success": True, "result": "Bypassed"})

    def get_plan(self, plan_id: str) -> dict | None:
        """Retrieve the current plan dict."""
        with self.plan_lock:
            return self.active_plans.get(plan_id)

    def get_plan_status(self, plan_id: str) -> dict | None:
        """Get progress and results for a plan."""
        return self.get_plan(plan_id)
