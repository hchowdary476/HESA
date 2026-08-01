import unittest
import os
import shutil
from tool_sdk import tool_manager

class TestDeveloperEcosystemTools(unittest.TestCase):

    def setUp(self) -> None:
        from tool_sdk import initialize_sdk
        initialize_sdk()
        self.assertIn("vscode_tool", tool_manager.tools)
        self.assertIn("git_tool", tool_manager.tools)
        self.test_workspace = os.path.abspath("logs/test_dev_workspace")
        if os.path.exists(self.test_workspace):
            shutil.rmtree(self.test_workspace)

    def tearDown(self) -> None:
        if os.path.exists(self.test_workspace):
            shutil.rmtree(self.test_workspace)

    def test_vscode_project_creation_and_history(self):
        """Verify project template generation and recently used folder tracking in VSCodeTool"""
        vstool = tool_manager.tools["vscode_tool"]
        
        # Test project creation
        res_create = vstool.execute(action="create_project", path=self.test_workspace)
        self.assertTrue(res_create.success)
        self.assertTrue(os.path.exists(os.path.join(self.test_workspace, "README.md")))
        self.assertTrue(os.path.exists(os.path.join(self.test_workspace, "app.py")))
        self.assertTrue(os.path.exists(os.path.join(self.test_workspace, "requirements.txt")))
        
        # Test recently used list
        res_recent = vstool.execute(action="get_recent")
        self.assertTrue(res_recent.success)
        self.assertIn(self.test_workspace, res_recent.output["recent_projects"])

    def test_vscode_task_runner_and_linting(self):
        """Verify linter, problems parsing, and task execution commands in VSCodeTool"""
        vstool = tool_manager.tools["vscode_tool"]
        
        # Make a dummy workspace and write invalid syntax python file
        os.makedirs(self.test_workspace, exist_ok=True)
        bad_file = os.path.join(self.test_workspace, "invalid.py")
        with open(bad_file, "w") as f:
            f.write("def invalid_syntax_here(:\n    pass")
            
        # Test read_problems static syntax checking
        res_prob = vstool.execute(action="read_problems", path=self.test_workspace)
        self.assertTrue(res_prob.success)
        self.assertGreater(res_prob.output["count"], 0)
        self.assertEqual(res_prob.output["problems"][0]["file"], "invalid.py")

        # Test task runner
        res_task = vstool.execute(action="run_task", cmd="echo 'build completed'", cwd=self.test_workspace)
        self.assertTrue(res_task.success)
        self.assertIn("build completed", res_task.output["stdout"].lower())

    def test_git_tool_actions_pipeline(self):
        """Verify git actions (init, status, branch, checkout, commit, diff) in GitTool"""
        git = tool_manager.tools["git_tool"]
        os.makedirs(self.test_workspace, exist_ok=True)
        
        # 1. Test Git Init
        res_init = git.execute(action="init", repo_path=self.test_workspace)
        self.assertTrue(res_init.success)
        self.assertTrue(os.path.exists(os.path.join(self.test_workspace, ".git")))
        
        # Write dummy file to track
        with open(os.path.join(self.test_workspace, "code.py"), "w") as f:
            f.write("print(1)")
            
        # 2. Test Git Status
        res_status = git.execute(action="status", repo_path=self.test_workspace)
        self.assertTrue(res_status.success)
        self.assertTrue(res_status.output["uncommitted"])
        
        # 3. Test Git Commit
        res_commit = git.execute(action="commit", repo_path=self.test_workspace, message="Initial test commit")
        self.assertTrue(res_commit.success)
        
        # 4. Test Git Branch List
        res_branch = git.execute(action="branch", repo_path=self.test_workspace)
        self.assertTrue(res_branch.success)
        
        # 5. Test Git Branch Creation
        res_new_branch = git.execute(action="branch", repo_path=self.test_workspace, branch_name="dev-feature")
        self.assertTrue(res_new_branch.success)
        
        # 6. Test Git Checkout
        res_checkout = git.execute(action="checkout", repo_path=self.test_workspace, branch_name="dev-feature")
        self.assertTrue(res_checkout.success)

if __name__ == "__main__":
    unittest.main()
