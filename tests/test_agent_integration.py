"""Integration test — runs the REAL agent against a live LLM.

Requires a provider key (OPENROUTER_API_KEY or DIGITALOCEAN_INFERENCE_KEY).
If none is set, the whole test is skipped so `unittest` stays green offline.

It proves the v0.6 feature end-to-end: in PLAN mode the permission layer stops
the real model from writing a file, no matter what it tries.

Run (with a key in your environment or .env):
    python -m unittest tests.test_agent_integration -v
"""
import os
import unittest

HAS_KEY = bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("DIGITALOCEAN_INFERENCE_KEY"))


@unittest.skipUnless(HAS_KEY, "no LLM key set (OPENROUTER_API_KEY / DIGITALOCEAN_INFERENCE_KEY)")
class PlanModeBlocksWrites(unittest.TestCase):
    def test_agent_cannot_write_in_plan_mode(self):
        # Import here so the module (which chdirs into agent_workspace) only loads
        # when we actually have a key and intend to run the agent.
        import coding_agent
        from permissions import PermissionChecker

        target = coding_agent.WORKSPACE / "should_not_exist.txt"
        target.unlink(missing_ok=True)

        checker = PermissionChecker(mode="plan")
        try:
            coding_agent.run_agent(
                "Create a file named should_not_exist.txt containing 'blocked', then finish.",
                max_iterations=3,
                verbose=False,
                permissions=checker,
            )
        except RuntimeError:
            # Expected: with writes blocked the agent may never reach finish()
            # and hit the max-iteration guard. That's fine for this test.
            pass

        self.assertFalse(
            target.exists(),
            "plan mode should have blocked the write, but the file was created",
        )


if __name__ == "__main__":
    unittest.main()
