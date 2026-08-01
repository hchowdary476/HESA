import unittest
import os
import json
import time
import shutil
import urllib.request
import urllib.error
import threading
from unittest.mock import patch, MagicMock

from JARVIS.core.ai_router.cloud.server import start_cloud_server, CLOUD_MEMORY_FILE
from JARVIS.core.memory.memory_store import MEMORY_FILE, load_memory, save_memory

TEST_PORT = 8999
CLOUD_URL = f"http://localhost:{TEST_PORT}"

class TestCloudContinuity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server in a background thread
        cls.server_thread = threading.Thread(
            target=start_cloud_server,
            args=(TEST_PORT,),
            daemon=True,
            name="test_cloud_server"
        )
        cls.server_thread.start()
        # Give server time to bind and listen
        time.sleep(0.5)

    def setUp(self):
        # Patch is_internet_available to return False for offline rules fallback
        self.internet_patcher = patch("JARVIS.core.automation.groq_router.is_internet_available", return_value=False)
        self.mock_internet = self.internet_patcher.start()

        # Back up existing files
        self.backup_files = []
        for file in [MEMORY_FILE, CLOUD_MEMORY_FILE]:
            if os.path.exists(file):
                bak = file + ".test_bak"
                shutil.copy2(file, bak)
                os.remove(file)
                self.backup_files.append((file, bak))

    def tearDown(self):
        # Stop patcher
        if hasattr(self, "internet_patcher"):
            self.internet_patcher.stop()

        # Clean up files created during tests
        for file in [MEMORY_FILE, CLOUD_MEMORY_FILE]:
            if os.path.exists(file):
                os.remove(file)
        # Restore backups
        for file, bak in self.backup_files:
            if os.path.exists(bak):
                shutil.copy2(bak, file)
                os.remove(bak)

    def _post_json(self, path, data, headers=None):
        url = f"{CLOUD_URL}{path}"
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        
        req_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers=req_headers, method="POST")
        with urllib.request.urlopen(req, timeout=2) as response:
            return json.loads(response.read().decode("utf-8")), response.status

    def _get_json(self, path, headers=None):
        url = f"{CLOUD_URL}{path}"
        req_headers = {}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            return json.loads(response.read().decode("utf-8")), response.status

    def test_unauthorized_chat(self):
        # Unauthenticated access to /api/chat should return 401
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_json("/api/chat", {"command": "hello jarvis"})
        self.assertEqual(ctx.exception.code, 401)

    def test_telugu_intelligence_chat(self):
        headers = {"Authorization": "Bearer session_ok"}
        
        # Test basic mock command routing
        res, code = self._post_json("/api/chat", {"command": "hello jarvis"}, headers=headers)
        self.assertEqual(code, 200)
        self.assertIn("response", res)
        
        # Test Telugu mixed question fallback routing
        res_tel, code_tel = self._post_json("/api/chat", {"command": "Jarvis em chestunnav?"}, headers=headers)
        self.assertEqual(code_tel, 200)
        self.assertIn("response", res_tel)
        # Check standard Telugu response
        self.assertTrue(
            "ready" in res_tel["response"].lower() or 
            "commands" in res_tel["response"].lower() or
            "command" in res_tel["response"].lower() or
            "siddhanga" in res_tel["response"].lower() or
            "vachindi" in res_tel["response"].lower() or
            "received" in res_tel["response"].lower()
        )

if __name__ == "__main__":
    unittest.main()
