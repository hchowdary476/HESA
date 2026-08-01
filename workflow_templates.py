"""Workflow Templates for JARVIS - Pre-defined workflow templates."""

from __future__ import annotations
from workflow_engine import Workflow, WorkflowNode

def create_dev_startup_workflow() -> Workflow:
    """Dev Startup template: opening IDE, restoring, starting webservers and documentation page."""
    nodes = [
        WorkflowNode("N1", "Open IDE", "windows_system_agent", "clipboard_tool", []),
        WorkflowNode("N2", "Restore Workspace", "memory_agent", "clipboard_tool", ["N1"]),
        WorkflowNode("N3", "Start Local AI", "ai_and_ml_agent", "llm_query_tool", ["N1"]),
        WorkflowNode("N4", "Verify Dependencies", "developer_agent", "git_tool", ["N2"]),
        WorkflowNode("N5", "Launch Backend", "developer_agent", "git_tool", ["N3", "N4"]),
        WorkflowNode("N6", "Launch Frontend", "automation_agent", "git_tool", ["N5"]),
        WorkflowNode("N7", "Open Documentation", "research_agent", "browser_open_tool", ["N6"])
    ]
    return Workflow("Development Startup Workflow", nodes)

def create_system_health_workflow() -> Workflow:
    """Daily System Health template: CPU metrics checks, log review audits, and reports generation."""
    nodes = [
        WorkflowNode("H1", "Check CPU and RAM", "windows_system_agent", "process_tool", []),
        WorkflowNode("H2", "Review Event Logs", "cyber_security_agent", "cve_tool", ["H1"]),
        WorkflowNode("H3", "Generate System Report", "windows_system_agent", "clipboard_tool", ["H2"])
    ]
    return Workflow("Daily System Health", nodes)

def create_research_session_workflow() -> Workflow:
    """Research Session template: note extraction, memory KG queries, browser launches, and summaries."""
    nodes = [
        WorkflowNode("R1", "Gather Research Notes", "memory_agent", "json_document_tool", []),
        WorkflowNode("R2", "Retrieve Memory KG", "memory_agent", "json_document_tool", ["R1"]),
        WorkflowNode("R3", "Open Browser to Arxiv", "research_agent", "browser_open_tool", ["R2"]),
        WorkflowNode("R4", "Query AI Summarization", "research_agent", "llm_query_tool", ["R3"])
    ]
    return Workflow("Research Session", nodes)
