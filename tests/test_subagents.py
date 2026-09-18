"""Tests for subagent delegation (offline — fake model, no key).

We script the fake client with the responses for BOTH the parent and any child
run, in the order create() is called, then assert delegation works and the depth
guard prevents unbounded recursion.

Run:
    python -m unittest discover -s tests
"""
import json
import os
import unittest


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
    def __init__(self, scripted): self._s, self.i = scripted, 0
    def create(self, **kw):
        r = self._s[self.i]; self.i += 1; return r

class FakeClient:
    def __init__(self, scripted):
        self.completions = _Completions(scripted)
        self.chat = type("Chat", (), {"completions": self.completions})()


def _tool(name, **args):
    return _Resp(_Msg(tool_calls=[_ToolCall("1", name, args)]))


class Delegation(unittest.TestCase):
    def _prep(self, scripted):
        os.environ.setdefault("OPENROUTER_API_KEY", "test-dummy")
        import coding_agent
        fake = FakeClient(scripted)
        original = coding_agent.client
        coding_agent.client = fake
        self.addCleanup(lambda: setattr(coding_agent, "client", original))
        return coding_agent, fake

    def test_parent_delegates_and_child_runs(self):
        # Order of create() calls:
        #   1) parent: spawn_subagent(task=...)
        #   2) child : finish("CHILD_OK")
        #   3) parent: finish("DONE")
        scripted = [
            _tool("spawn_subagent", task="do the sub thing"),
            _tool("finish", answer="CHILD_OK"),
            _tool("finish", answer="DONE"),
        ]
        coding_agent, fake = self._prep(scripted)
        result = coding_agent.run_agent("parent task", verbose=False, max_depth=1)
        self.assertEqual(result, "DONE")
        # 3 model calls proves the child loop actually executed.
        self.assertEqual(fake.completions.i, 3)

    def test_depth_guard_blocks_recursion(self):
        # With max_depth=0 the tool isn't offered; if the model calls it anyway,
        # the guard returns an error and NO child run happens.
        scripted = [
            _tool("spawn_subagent", task="try to recurse"),
            _tool("finish", answer="DONE"),
        ]
        coding_agent, fake = self._prep(scripted)
        result = coding_agent.run_agent("parent", verbose=False, max_depth=0)
        self.assertEqual(result, "DONE")
        # Only 2 calls — the parent's two turns; no child was spawned.
        self.assertEqual(fake.completions.i, 2)


if __name__ == "__main__":
    unittest.main()
