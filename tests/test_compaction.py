"""Unit tests for compaction.py (offline — always run, no key needed).

Uses a fake summarizer so nothing hits the network.

Run:
    python -m unittest discover -s tests
"""
import json
import os
import unittest

from compaction import Compactor, estimate_size, heuristic_summarizer


FAKE = lambda text: "SUMMARY"


# --- Minimal fakes mimicking the OpenAI SDK response shape (no key/network) ---

class _Fn:
    def __init__(self, name, args): self.name, self.arguments = name, json.dumps(args)

class _ToolCall:
    def __init__(self, id, name, args): self.id, self.function = id, _Fn(name, args)

class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content, self.tool_calls = content, tool_calls

class _Resp:
    def __init__(self, msg): self.choices = [type("C", (), {"message": msg})]

class _Completions:
    def __init__(self, scripted): self._s, self._i = scripted, 0
    def create(self, **kw):
        r = self._s[self._i]; self._i += 1; return r

class FakeClient:
    def __init__(self, scripted):
        self.chat = type("Chat", (), {"completions": _Completions(scripted)})()


class EstimateSize(unittest.TestCase):
    def test_counts_content_chars(self):
        msgs = [{"role": "user", "content": "abcd"}, {"role": "assistant", "content": "ef"}]
        self.assertEqual(estimate_size(msgs), 6)


class NoOp(unittest.TestCase):
    def test_under_threshold_is_unchanged(self):
        c = Compactor(max_chars=1000, summarizer=FAKE)
        msgs = [{"role": "system", "content": "sys"},
                {"role": "user", "content": "hi"}]
        out, changed = c.maybe_compact(msgs)
        self.assertFalse(changed)
        self.assertEqual(out, msgs)

    def test_no_churn_when_nothing_to_summarize(self):
        # Over budget, but everything is system + task + recent (empty middle).
        # Must be a no-op so a too-low budget can't cause per-iteration churn.
        c = Compactor(max_chars=10, keep_recent=2, summarizer=FAKE)
        msgs = [{"role": "system", "content": "S" * 100},
                {"role": "user", "content": "task"},
                {"role": "assistant", "content": "a1"},
                {"role": "assistant", "content": "a2"}]
        out, changed = c.maybe_compact(msgs)
        self.assertFalse(changed)
        self.assertEqual(out, msgs)


class Compacts(unittest.TestCase):
    def _big(self):
        return [
            {"role": "system", "content": "SYSTEM"},
            {"role": "user", "content": "the original task"},
            {"role": "assistant", "content": "x" * 500},
            {"role": "tool", "content": "y" * 500},
            {"role": "assistant", "content": "z" * 500},
            {"role": "user", "content": "recent-1"},
            {"role": "assistant", "content": "recent-2"},
        ]

    def test_compacts_over_threshold(self):
        c = Compactor(max_chars=100, keep_recent=2, summarizer=FAKE)
        out, changed = c.maybe_compact(self._big())
        self.assertTrue(changed)
        self.assertLess(estimate_size(out), estimate_size(self._big()))

    def test_preserves_system_and_task_and_recent(self):
        c = Compactor(max_chars=100, keep_recent=2, summarizer=FAKE)
        out, _ = c.maybe_compact(self._big())
        self.assertEqual(out[0]["content"], "SYSTEM")           # system kept
        self.assertEqual(out[1]["content"], "the original task")  # task kept
        self.assertIn("SUMMARY", out[2]["content"])             # summary inserted
        self.assertEqual(out[-1]["content"], "recent-2")        # recent tail kept
        self.assertEqual(out[-2]["content"], "recent-1")

    def test_result_has_no_tool_messages(self):
        # Compacted output must be a valid request: no tool/tool_call leftovers.
        c = Compactor(max_chars=100, keep_recent=3, summarizer=FAKE)
        out, _ = c.maybe_compact(self._big())
        self.assertTrue(all(m["role"] in ("system", "user", "assistant") for m in out))


class Heuristic(unittest.TestCase):
    def test_short_text_passthrough(self):
        self.assertEqual(heuristic_summarizer("short"), "short")

    def test_long_text_truncated(self):
        out = heuristic_summarizer("a" * 5000)
        self.assertLess(len(out), 5000)
        self.assertIn("omitted", out)


class LoopFiresCompaction(unittest.TestCase):
    """Drive run_agent with a fake model so compaction triggers mid-run."""

    def test_run_agent_compacts_when_over_budget(self):
        # coding_agent builds a client at import time; give it a dummy key so the
        # import succeeds. We immediately swap in a FakeClient, so it's never used.
        os.environ.setdefault("OPENROUTER_API_KEY", "test-dummy")
        import coding_agent

        # Script: (1) a big assistant message that inflates the history, then
        # (2) a finish call to end the loop.
        scripted = [
            _Resp(_Msg(content="A" * 3000, tool_calls=None)),
            _Resp(_Msg(content=None, tool_calls=[_ToolCall("1", "finish", {"answer": "ok"})])),
        ]
        original = coding_agent.client
        coding_agent.client = FakeClient(scripted)
        self.addCleanup(lambda: setattr(coding_agent, "client", original))

        # Spy summarizer records each compaction call; small budget forces it.
        calls = []
        comp = Compactor(max_chars=1000, keep_recent=0,
                         summarizer=lambda text: calls.append(text) or "SUMMARY")

        result = coding_agent.run_agent("do the thing", max_iterations=5,
                                        verbose=False, compactor=comp)

        self.assertEqual(result, "ok")
        self.assertGreaterEqual(len(calls), 1, "compaction should have fired at least once")


if __name__ == "__main__":
    unittest.main()
