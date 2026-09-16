"""Unit tests for hooks.py (offline — always run, no key needed).

Run:
    python -m unittest discover -s tests
"""
import unittest

from hooks import HookManager, HookResult, make_counter, block_tool, redact_post_hook


class PreHooks(unittest.TestCase):
    def test_pre_hook_can_block(self):
        m = HookManager(pre=[block_tool("bash")])
        allowed, reason, _ = m.run_pre("bash", {"command": "ls"})
        self.assertFalse(allowed)
        self.assertIn("bash", reason)

    def test_pre_hook_passes_other_tools(self):
        m = HookManager(pre=[block_tool("bash")])
        allowed, _, _ = m.run_pre("read_file", {"filepath": "a.txt"})
        self.assertTrue(allowed)

    def test_pre_hook_can_rewrite_args(self):
        def force_relative(tool, args):
            return HookResult(args={**args, "filepath": args["filepath"].lstrip("/")})
        m = HookManager(pre=[force_relative])
        allowed, _, args = m.run_pre("read_file", {"filepath": "/etc/hosts"})
        self.assertTrue(allowed)
        self.assertEqual(args["filepath"], "etc/hosts")

    def test_pre_hooks_run_in_order(self):
        order = []
        m = HookManager(pre=[
            lambda t, a: order.append("first") or None,
            lambda t, a: order.append("second") or None,
        ])
        m.run_pre("read_file", {})
        self.assertEqual(order, ["first", "second"])


class PostHooks(unittest.TestCase):
    def test_counter_counts_calls(self):
        counts = {}
        m = HookManager(post=[make_counter(counts)])
        m.run_post("read_file", {}, {"ok": True})
        m.run_post("read_file", {}, {"ok": True})
        m.run_post("bash", {}, {"ok": True})
        self.assertEqual(counts, {"read_file": 2, "bash": 1})

    def test_post_hook_can_rewrite_result(self):
        m = HookManager(post=[redact_post_hook])
        out = m.run_post("read_file", {}, {"content": "key sk-abcdef1234567890"})
        self.assertIn("REDACTED", str(out))
        self.assertNotIn("1234567890", str(out))

    def test_post_hook_leaves_clean_result_untouched(self):
        m = HookManager(post=[redact_post_hook])
        original = {"content": "nothing secret here"}
        self.assertEqual(m.run_post("read_file", {}, original), original)


if __name__ == "__main__":
    unittest.main()
