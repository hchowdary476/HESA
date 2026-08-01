import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock

from JARVIS.runtime.self_healing import SelfHealingEngine, LOW, MEDIUM, HIGH, CRITICAL
from JARVIS.core.security import security_shield

class SelfHealingEngineTests(unittest.TestCase):
    def setUp(self):
        # Reset state & singleton
        SelfHealingEngine._instance = None
        state_file = os.path.join("logs", "self_healing_state.json")
        if os.path.exists(state_file):
            try:
                os.remove(state_file)
            except OSError:
                pass
        self.engine = SelfHealingEngine()
        
        # Create temp environment or clean test targets
        self.test_dir = "logs/test_healing"
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        # Clean up test directories
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        state_file = os.path.join("logs", "self_healing_state.json")
        if os.path.exists(state_file):
            try:
                os.remove(state_file)
            except OSError:
                pass
        SelfHealingEngine._instance = None

    def test_verify_pin_success(self):
        with patch.object(security_shield, "load_settings", return_value={"recovery_pin": "5678"}):
            self.assertTrue(self.engine.verify_pin("5678"))
            self.assertFalse(self.engine.verify_pin("1234"))

    def test_risk_classification(self):
        report = self.engine.run_diagnostics()
        
        self.assertIn("health_score", report)
        self.assertIn("issues", report)
        self.assertIn("pending_repairs", report)
        self.assertIn("rollback_count", report)

    def test_apply_repair_critical_requires_pin(self):
        self.engine.pending_repairs["critical_test"] = {
            "id": "critical_test",
            "name": "Critical Test",
            "risk": CRITICAL,
            "action": "Reset secure signatures",
            "file": "logs/test_file.json",
            "severity": "Critical",
            "confidence": 1.0,
            "estimated_time": "10s",
            "root_cause": "test critical"
        }
        
        with self.assertRaises(PermissionError):
            self.engine.apply_repair("critical_test", pin=None)
            
        with patch.object(security_shield, "load_settings", return_value={"recovery_pin": "1234"}):
            with self.assertRaises(PermissionError):
                self.engine.apply_repair("critical_test", pin="9999")

    def test_backup_and_rollback_on_failure(self):
        corrupt_filepath = os.path.join(self.test_dir, "corrupt_test.json")
        with open(corrupt_filepath, "w") as f:
            f.write("original correct content")
            
        self.engine.pending_repairs["corrupted_file_corrupt_test_json"] = {
            "id": "corrupted_file_corrupt_test_json",
            "name": "Corrupted configuration: corrupt_test.json",
            "risk": HIGH,
            "action": "Purge corrupted file and restore",
            "file": corrupt_filepath,
            "severity": "High",
            "confidence": 0.95,
            "estimated_time": "3s",
            "root_cause": "corrupt json file",
            "default_content": "[]"
        }
        
        with patch.object(self.engine, "_validate_fix", side_effect=ValueError("Simulated validation crash")):
            with self.assertRaises(RuntimeError) as context:
                self.engine.apply_repair("corrupted_file_corrupt_test_json")
                
            self.assertIn("Automatic rollback executed", str(context.exception))
            
            with open(corrupt_filepath, "r") as f:
                content = f.read()
            self.assertEqual(content, "original correct content")
            
            self.assertEqual(self.engine.rollback_count, 1)

    def test_apply_repair_success(self):
        missing_filepath = os.path.join(self.test_dir, "missing_test.json")
        if os.path.exists(missing_filepath):
            os.remove(missing_filepath)
            
        self.engine.pending_repairs["missing_file_missing_test_json"] = {
            "id": "missing_file_missing_test_json",
            "name": "Missing file: missing_test.json",
            "risk": LOW,
            "action": "Restore missing_test.json",
            "file": missing_filepath,
            "severity": "Medium",
            "confidence": 0.98,
            "estimated_time": "2s",
            "root_cause": "missing test",
            "default_content": '{"ok": true}'
        }
        
        report = self.engine.apply_repair("missing_file_missing_test_json")
        self.assertEqual(report["status"], "Success")
        
        self.assertTrue(os.path.exists(missing_filepath))
        with open(missing_filepath, "r") as f:
            data = json.load(f)
        self.assertTrue(data["ok"])

if __name__ == "__main__":
    unittest.main()
