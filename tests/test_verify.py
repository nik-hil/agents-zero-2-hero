"""Tests for verify.py (offline — spawns unittest subprocesses, no key).

Run:
    python -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

import verify

BUGGY = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n"
TEST = ("import unittest\nfrom calc import add\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n")


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "test_calc.py").write_text(TEST, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_failing_suite_reports_not_passed(self):
        (self.dir / "calc.py").write_text(BUGGY, encoding="utf-8")
        result = verify.run_tests(self.dir)
        self.assertFalse(result["passed"])
        self.assertNotEqual(result["returncode"], 0)
        self.assertIn("FAIL", result["output"])

    def test_passing_suite_reports_passed(self):
        (self.dir / "calc.py").write_text(FIXED, encoding="utf-8")
        result = verify.run_tests(self.dir)
        self.assertTrue(result["passed"])
        self.assertEqual(result["returncode"], 0)

    def test_fix_after_failure_is_seen(self):
        # The stale-bytecode trap: fixing must be visible on the next run.
        (self.dir / "calc.py").write_text(BUGGY, encoding="utf-8")
        self.assertFalse(verify.run_tests(self.dir)["passed"])
        (self.dir / "calc.py").write_text(FIXED, encoding="utf-8")
        self.assertTrue(verify.run_tests(self.dir)["passed"])


if __name__ == "__main__":
    unittest.main()
