"""Unit tests for permissions.py (offline — always run, no key needed).

Run:
    python -m unittest discover -s tests
"""
import unittest

from permissions import PermissionChecker, Mode


class Modes(unittest.TestCase):
    def test_auto_allows_mutating_tool(self):
        c = PermissionChecker(mode="auto")
        self.assertTrue(c.check("write_file", {"filepath": "a.txt", "content": "x"}).allowed)

    def test_plan_blocks_writes_allows_reads(self):
        c = PermissionChecker(mode="plan")
        self.assertFalse(c.check("write_file", {"filepath": "a.txt", "content": "x"}).allowed)
        self.assertTrue(c.check("read_file", {"filepath": "a.txt"}).allowed)

    def test_default_asks_the_approver(self):
        allow = PermissionChecker(mode="default", approver=lambda t, a: True)
        deny = PermissionChecker(mode="default", approver=lambda t, a: False)
        self.assertTrue(allow.check("edit_file", {"filepath": "a.py"}).allowed)
        self.assertFalse(deny.check("edit_file", {"filepath": "a.py"}).allowed)

    def test_default_approver_defaults_to_deny(self):
        # No approver supplied -> mutating calls are refused.
        c = PermissionChecker(mode="default")
        self.assertFalse(c.check("bash", {"command": "ls"}).allowed)


class HardRules(unittest.TestCase):
    def test_denied_command_blocked_even_in_auto(self):
        c = PermissionChecker(mode="auto")
        d = c.check("bash", {"command": "rm -rf /"})
        self.assertFalse(d.allowed)
        self.assertIn("rm -rf", d.reason)

    def test_denied_pattern_in_execute_code(self):
        c = PermissionChecker(mode="auto")
        self.assertFalse(c.check("execute_code", {"code": "import shutil; shutil.rmtree('/')"}).allowed)

    def test_path_rule_denies_matching_glob(self):
        c = PermissionChecker(mode="auto", path_rules=[("*.env", False)])
        self.assertFalse(c.check("read_file", {"filepath": "secrets.env"}).allowed)
        self.assertTrue(c.check("read_file", {"filepath": "notes.txt"}).allowed)


if __name__ == "__main__":
    unittest.main()
