import unittest
import os
import json
import shutil
import time
from unittest.mock import patch

from JARVIS.services.supervisor import create_backup, BACKUP_METRICS, calculate_sha256

class TestBackupCooldown(unittest.TestCase):
    def setUp(self):
        # Save original metrics and reset
        self.original_metrics = {
            "config": dict(BACKUP_METRICS["config"]),
            "memory": dict(BACKUP_METRICS["memory"])
        }
        
        # Reset state
        for key in ["config", "memory"]:
            BACKUP_METRICS[key] = {
                "last_backup_time": 0.0,
                "backup_count": 0,
                "skipped_backups": 0,
                "last_sha256": "",
                "last_mtime": 0.0
            }
            
        # Set up test directories and files
        self.test_dir = os.path.join("logs", "test_backups")
        os.makedirs(self.test_dir, exist_ok=True)
        
        self.test_file_config = os.path.join(self.test_dir, "test_settings.json")
        self.test_file_memory = os.path.join(self.test_dir, "test_memory.json")
        
        # Save existing backup status file if any
        self.status_file_path = os.path.join("logs", "backup_status.json")
        self.status_file_backup = os.path.join("logs", "backup_status_temp_bak.json")
        if os.path.exists(self.status_file_path):
            shutil.copy2(self.status_file_path, self.status_file_backup)
            os.remove(self.status_file_path)
            
        # Clean up any potential leftover test backup directories
        self.backup_dir_config = os.path.join("logs", "backups", "test_config")
        self.backup_dir_memory = os.path.join("logs", "backups", "test_memory")
        if os.path.exists(self.backup_dir_config):
            shutil.rmtree(self.backup_dir_config)
        if os.path.exists(self.backup_dir_memory):
            shutil.rmtree(self.backup_dir_memory)

    def tearDown(self):
        # Clean up files created
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists(self.backup_dir_config):
            shutil.rmtree(self.backup_dir_config)
        if os.path.exists(self.backup_dir_memory):
            shutil.rmtree(self.backup_dir_memory)
            
        # Restore status file
        if os.path.exists(self.status_file_path):
            os.remove(self.status_file_path)
        if os.path.exists(self.status_file_backup):
            shutil.copy2(self.status_file_backup, self.status_file_path)
            os.remove(self.status_file_backup)
            
        # Restore original metrics
        for key in ["config", "memory"]:
            BACKUP_METRICS[key] = self.original_metrics[key]

    def _write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def test_invalid_json_is_skipped(self):
        # Write corrupted JSON
        with open(self.test_file_config, "w", encoding="utf-8") as f:
            f.write("{invalid_json:")
            
        create_backup(self.test_file_config, "test_config")
        
        # Verify no backup was created
        self.assertFalse(os.path.exists(os.path.join(self.backup_dir_config, "test_config_bak_1.json")))
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 0)
        self.assertEqual(BACKUP_METRICS["config"]["skipped_backups"], 0)

    def test_first_backup_success(self):
        data = {"theme": "cyberpunk", "volume": 80}
        self._write_json(self.test_file_config, data)
        
        create_backup(self.test_file_config, "test_config")
        
        # Verify backup was created
        backup_path = os.path.join(self.backup_dir_config, "test_config_bak_1.json")
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, "r", encoding="utf-8") as f:
            backed_data = json.load(f)
        self.assertEqual(backed_data, data)
        
        # Verify metrics updated
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        self.assertEqual(BACKUP_METRICS["config"]["skipped_backups"], 0)
        self.assertGreater(BACKUP_METRICS["config"]["last_backup_time"], 0.0)
        self.assertEqual(BACKUP_METRICS["config"]["last_sha256"], calculate_sha256(self.test_file_config))
        
        # Verify status file written
        self.assertTrue(os.path.exists(self.status_file_path))
        with open(self.status_file_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        self.assertEqual(status["config"]["backup_count"], 1)
        self.assertEqual(status["config"]["skipped_backups"], 0)

    def test_unchanged_content_skips_backup(self):
        data = {"theme": "cyberpunk"}
        self._write_json(self.test_file_config, data)
        
        # First backup (success)
        create_backup(self.test_file_config, "test_config")
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        self.assertEqual(BACKUP_METRICS["config"]["skipped_backups"], 0)
        
        # Second backup (should skip because content unchanged)
        create_backup(self.test_file_config, "test_config")
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        self.assertEqual(BACKUP_METRICS["config"]["skipped_backups"], 1)
        
        # Verify status file reflects skipped backups
        with open(self.status_file_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        self.assertEqual(status["config"]["backup_count"], 1)
        self.assertEqual(status["config"]["skipped_backups"], 1)

    def test_cooldown_skips_backup_if_changed(self):
        data1 = {"theme": "cyberpunk"}
        self._write_json(self.test_file_config, data1)
        
        # First backup (success)
        create_backup(self.test_file_config, "test_config")
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        
        # Modify content
        data2 = {"theme": "neon"}
        self._write_json(self.test_file_config, data2)
        
        # Second backup (should skip due to cooldown)
        create_backup(self.test_file_config, "test_config")
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        self.assertEqual(BACKUP_METRICS["config"]["skipped_backups"], 1)

    def test_emergency_bypass_cooldown(self):
        data1 = {"theme": "cyberpunk"}
        self._write_json(self.test_file_config, data1)
        
        # First backup (success)
        create_backup(self.test_file_config, "test_config")
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        
        # Modify content
        data2 = {"theme": "neon"}
        self._write_json(self.test_file_config, data2)
        
        # Second backup as emergency (should succeed, bypassing cooldown)
        create_backup(self.test_file_config, "test_config", emergency=True)
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 2)
        self.assertEqual(BACKUP_METRICS["config"]["skipped_backups"], 0)
        
        # Verify second backup has data2
        backup_path = os.path.join(self.backup_dir_config, "test_config_bak_1.json")
        with open(backup_path, "r", encoding="utf-8") as f:
            backed_data = json.load(f)
        self.assertEqual(backed_data, data2)

    def test_emergency_skips_if_unchanged(self):
        data = {"theme": "cyberpunk"}
        self._write_json(self.test_file_config, data)
        
        # First backup (success)
        create_backup(self.test_file_config, "test_config")
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        
        # Second backup as emergency but unchanged (should skip)
        create_backup(self.test_file_config, "test_config", emergency=True)
        self.assertEqual(BACKUP_METRICS["config"]["backup_count"], 1)
        self.assertEqual(BACKUP_METRICS["config"]["skipped_backups"], 1)

    def test_cooldown_status_field(self):
        data = {"theme": "cyberpunk"}
        self._write_json(self.test_file_config, data)
        
        # Initially cooldown status should be idle or active depending on time
        create_backup(self.test_file_config, "test_config")
        
        with open(self.status_file_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        self.assertEqual(status["config"]["backup_cooldown_status"], "active")
        
        # Mocking time to be 11 minutes later
        now = time.time()
        with patch("time.time", return_value=now + 660):
            # Regenerate status data
            from JARVIS.services.supervisor import write_backup_status_file
            write_backup_status_file()
            
            with open(self.status_file_path, "r", encoding="utf-8") as f:
                status = json.load(f)
            self.assertEqual(status["config"]["backup_cooldown_status"], "idle")

if __name__ == "__main__":
    unittest.main()
