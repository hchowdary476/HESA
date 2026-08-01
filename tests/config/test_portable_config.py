import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from JARVIS.config.manager import ConfigManager
from JARVIS.config.paths import ConfigPaths
from JARVIS.release.portable_policy import is_denied_portable_path


class PortableConfigTests(unittest.TestCase):
    def test_portable_manager_uses_config_settings_json(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ConfigPaths.for_portable_root(root)
            manager = ConfigManager(paths=paths, env={})

            manager.load()
            manager.set("voice.wake_word", "friday")
            manager.save()

            self.assertTrue(paths.portable)
            self.assertTrue((root / "config" / "settings.json").exists())

    def test_portable_policy_denies_real_settings_file(self):
        denied = is_denied_portable_path("config/settings.json")

        self.assertTrue(denied["denied"])
        self.assertIn("settings", str(denied["reason"]).lower())


if __name__ == "__main__":
    unittest.main()
