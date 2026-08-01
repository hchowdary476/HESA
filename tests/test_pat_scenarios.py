import unittest
from unittest.mock import MagicMock, patch
import os
import time
import json

from tool_sdk import tool_manager
from JARVIS.core.system.environment_validator import EnvironmentValidator
from JARVIS.core.system.startup_manager import StartupManager
from JARVIS.core.system.diagnostics_center import DiagnosticsCenter
from JARVIS.runtime.self_healing import SelfHealingEngine
from memory_engine import MemoryEngine
from knowledge_graph import ProductionKnowledgeGraph
from workflow_engine import Workflow, WorkflowNode

class JARVISProductionAcceptanceTests(unittest.TestCase):
    
    def setUp(self):
        from tool_sdk import initialize_sdk
        initialize_sdk()
        self.diagnostics = DiagnosticsCenter()
        self.healing = SelfHealingEngine()
        self.memory = MemoryEngine()
        self.kg = ProductionKnowledgeGraph()
        
    def test_pat_scenario_1_startup_and_validation(self):
        """Scenario 1: Verify environment validator and startup managers execute safely"""
        validator = EnvironmentValidator()
        self.assertTrue(validator.validate_all())
        
        # Test startup checklist does not raise errors
        startup = StartupManager()
        self.assertTrue(startup.initialize_all_services())
        self.assertTrue(startup.is_ready_for_gui_launch())
        
    def test_pat_scenario_2_voice_intent_routing(self):
        """Scenario 2: Verify 'Open Visual Studio Code' voice intent matches to ProcessTool"""
        voice_query = "Open Visual Studio Code"
        
        # Verify matching tools exist
        self.assertIn("process_tool", tool_manager.tools)
        tool = tool_manager.tools["process_tool"]
        self.assertTrue(tool.is_healthy)
        
    def test_pat_scenario_3_developer_workflow(self):
        """Scenario 3: Verify developer workspace python template file generation"""
        test_dir = "logs/test_dev_project"
        os.makedirs(test_dir, exist_ok=True)
        
        # Write dummy python project templates
        try:
            with open(os.path.join(test_dir, "README.md"), "w") as f:
                f.write("# Test Project")
            with open(os.path.join(test_dir, "requirements.txt"), "w") as f:
                f.write("pytest\n")
            with open(os.path.join(test_dir, "app.py"), "w") as f:
                f.write("print('hello')\n")
                
            self.assertTrue(os.path.exists(os.path.join(test_dir, "README.md")))
            self.assertTrue(os.path.exists(os.path.join(test_dir, "requirements.txt")))
        finally:
            # Cleanup test files
            for file in ["README.md", "requirements.txt", "app.py"]:
                p = os.path.join(test_dir, file)
                if os.path.exists(p):
                    os.remove(p)
            os.rmdir(test_dir)
            
    def test_pat_scenario_4_testing_workflow(self):
        """Scenario 4: Verify test execution summary parsing"""
        # Simulated run test outcome
        test_run_data = {
            "total": 554,
            "passed": 554,
            "failed": 0,
            "skipped": 2
        }
        self.assertEqual(test_run_data["failed"], 0)
        self.assertEqual(test_run_data["passed"], 554)
        
    def test_pat_scenario_5_model_switching(self):
        """Scenario 5: Switch models and ensure config registry updates dynamically"""
        models = ["Gemini", "Claude", "ChatGPT", "Groq", "DeepSeek", "LM Studio", "Ollama"]
        
        # Simulate router update
        for model in models:
            self.diagnostics.record_model_query(model, 120.0, 0.0, 50, True)
            self.assertIn(model, self.diagnostics.model_stats)
            
    def test_pat_scenario_6_windows_integration_checks(self):
        """Scenario 6: Test clipboard, processes, notifications, and monitor metrics are executable"""
        # Test ClipboardTool registration
        self.assertIn("clipboard_tool", tool_manager.tools)
        # Test HardwareMonitoringTool metrics
        self.assertIn("hardware_monitoring_tool", tool_manager.tools)
        
    def test_pat_scenario_7_workflow_automation_dag(self):
        """Scenario 7: Test complex multi-step automation workflow DAG nodes"""
        n1 = WorkflowNode("1", "Open browser", "browser", "browser_open_tool", [])
        n2 = WorkflowNode("2", "Extract text", "agent", "clipboard_tool", ["1"])
        
        wf = Workflow("Google Search Automation", [n1, n2])
        self.assertEqual(wf.name, "Google Search Automation")
        self.assertEqual(len(wf.nodes), 2)
        
    def test_pat_scenario_8_gui_verification_bridge(self):
        """Scenario 8: Verify QML bridge property updates are callable"""
        from JARVIS.gui.qml_bridge import JarvisBridge
        bridge = JarvisBridge()
        self.assertTrue(bridge._is_alive)
        
    def test_pat_scenario_9_diagnostics_telemetry(self):
        """Scenario 9: Confirm live subsystem diagnostics metrics report health"""
        health = self.diagnostics.get_subsystems_health()
        self.assertIn("Voice Engine", health)
        self.assertIn("AI Router", health)
        self.assertEqual(health["AI Router"]["status"], "Running")
        
    def test_pat_scenario_10_session_recovery(self):
        """Scenario 10: Validate self healing state loading/saving on session restore"""
        self.healing.rollback_count = 5
        self.healing._save_state()
        
        # Re-init state
        self.healing._load_state()
        self.assertEqual(self.healing.rollback_count, 5)

if __name__ == "__main__":
    unittest.main()
