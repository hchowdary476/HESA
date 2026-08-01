import unittest
from unittest.mock import patch

import JARVIS.core.automation.komutlar as komutlar


class ProcessCommandLocalRouterTests(unittest.TestCase):
    def test_process_command_executes_local_action_before_groq(self):
        with (
            patch("JARVIS.core.automation.komutlar.add_to_short_term"),
            patch("JARVIS.core.automation.komutlar.track_command"),
            patch("JARVIS.core.automation.komutlar.detect_and_save_preference", return_value=None),
            patch(
                "JARVIS.core.automation.local_intent_router.route_local_intent",
                return_value={"action": "get_time", "params": {}, "response": "Sir, it is 10:00 PM."},
            ) as local_mock,
            patch(
                "JARVIS.core.ai_router.ai_orchestrator.AIOrchestrator.query_with_failover", return_value="Sir, it is 10:00 PM."
            ) as orchestrator_mock,
            patch("JARVIS.core.automation.komutlar.execute_action", return_value=True) as execute_mock,
        ):
            result = komutlar.process_command("what time is it")

        self.assertTrue(result)
        local_mock.assert_called_once_with("what time is it")
        orchestrator_mock.assert_not_called()
        execute_mock.assert_called_once()
        called_arg = execute_mock.call_args[0][0]
        self.assertEqual(called_arg["action"], "get_time")
        self.assertEqual(called_arg["params"], {})
        self.assertEqual(called_arg["response"], "Sir, it is 10:00 PM.")

    def test_process_command_falls_back_to_groq_when_local_router_has_no_match(self):
        with (
            patch("JARVIS.core.automation.komutlar.add_to_short_term"),
            patch("JARVIS.core.automation.komutlar.track_command"),
            patch("JARVIS.core.automation.komutlar.detect_and_save_preference", return_value=None),
            patch("JARVIS.core.automation.local_intent_router.route_local_intent", return_value=None) as local_mock,
            patch(
                "JARVIS.core.ai_router.ai_orchestrator.AIOrchestrator.query_with_failover", return_value="At once, sir."
            ) as orchestrator_mock,
            patch("JARVIS.core.automation.komutlar.execute_action", return_value=True) as execute_mock,
        ):
            result = komutlar.process_command("please plan my morning")

        self.assertTrue(result)
        local_mock.assert_any_call("please plan my morning")
        orchestrator_mock.assert_called_once()
        execute_mock.assert_not_called()

    def test_process_command_routes_expanded_daily_commands_locally(self):
        commands = [
            "open youtube",
            "search for python desktop assistant",
            "volume up",
            "pause music",
            "cpu",
        ]

        for command in commands:
            with self.subTest(command=command):
                with (
                    patch("JARVIS.core.automation.komutlar.add_to_short_term"),
                    patch("JARVIS.core.automation.komutlar.track_command"),
                    patch("JARVIS.core.automation.komutlar.detect_and_save_preference", return_value=None),
                    patch(
                        "JARVIS.core.ai_router.ai_orchestrator.AIOrchestrator.query_with_failover", return_value="Sir, completed."
                    ) as orchestrator_mock,
                    patch("JARVIS.core.automation.komutlar.execute_action", return_value=True) as execute_mock,
                ):
                    result = komutlar.process_command(command)

                self.assertTrue(result)
                orchestrator_mock.assert_not_called()
                execute_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
