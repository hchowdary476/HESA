"""JARVIS Tool SDK - Unified entry point registering all system capabilities."""

from __future__ import annotations
from tool_manager import ToolManager

# Import core tool modules
from tools.windows_tools import (
    ClipboardTool, 
    ProcessTool, 
    WindowManagementTool, 
    NotificationTool, 
    PowerManagementTool, 
    HardwareMonitoringTool
)
from tools.developer_tools import GitTool, VSCodeTool
from tools.ai_tools import LLMQueryTool
from tools.ml_tools import MLTrainingTool
from tools.cyber_tools import CVETool
from tools.browser_tools import BrowserOpenTool
from tools.file_tools import FileSearchTool, FileOperationsTool
from tools.office_tools import JSONDocumentTool
from tools.network_tools import NetworkPingTool

def initialize_sdk() -> ToolManager:
    """Discover, load, and register all default JARVIS Tool SDK modules."""
    mgr = ToolManager()
    
    # 1. Windows Tools
    mgr.register_tool(ClipboardTool())
    mgr.register_tool(ProcessTool())
    mgr.register_tool(WindowManagementTool())
    mgr.register_tool(NotificationTool())
    mgr.register_tool(PowerManagementTool())
    mgr.register_tool(HardwareMonitoringTool())
    
    # 2. Developer Tools
    mgr.register_tool(GitTool())
    mgr.register_tool(VSCodeTool())
    
    # 3. AI Tools
    mgr.register_tool(LLMQueryTool())
    
    # 4. ML Tools
    mgr.register_tool(MLTrainingTool())
    
    # 5. Cyber Tools
    mgr.register_tool(CVETool())
    
    # 6. Browser Tools
    mgr.register_tool(BrowserOpenTool())
    
    # 7. File Tools
    mgr.register_tool(FileSearchTool())
    mgr.register_tool(FileOperationsTool())
    
    # 8. Office Tools
    mgr.register_tool(JSONDocumentTool())
    
    # 9. Network Tools
    mgr.register_tool(NetworkPingTool())
    
    return mgr

# Centralized global manager instance
tool_manager = initialize_sdk()

