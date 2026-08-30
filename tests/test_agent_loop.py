import importlib
import json
import unittest
from types import SimpleNamespace


class FakeCompletions:
    def __init__(self, messages):
        self._messages = messages
        self.calls = 0

    def create(self, **kwargs):
        message = self._messages[self.calls]
        self.calls += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, messages):
        self.chat = SimpleNamespace(completions=FakeCompletions(messages))


def tool_message(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id=call_id,
                function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
            )
        ],
    )


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.agent = importlib.import_module("coding_agent")

    def test_agent_loop_returns_finish_answer(self):
        client = FakeClient([
            tool_message("finish", {"answer": "done"}),
        ])

        result = self.agent.run_agent(
            "Say done",
            max_iterations=1,
            llm_client=client,
            verbose=False,
        )

        self.assertEqual(result, "done")

    def test_agent_loop_recovers_from_unknown_tool(self):
        client = FakeClient([
            tool_message("not_a_tool", {}, "bad_call"),
            tool_message("finish", {"answer": "recovered"}, "finish_call"),
        ])

        result = self.agent.run_agent(
            "Recover from a bad tool call",
            max_iterations=2,
            llm_client=client,
            verbose=False,
        )

        self.assertEqual(result, "recovered")

    def test_agent_loop_stops_at_max_iterations(self):
        client = FakeClient([
            SimpleNamespace(content="thinking", tool_calls=None),
        ])

        with self.assertRaisesRegex(RuntimeError, "Max iterations"):
            self.agent.run_agent(
                "Never finish",
                max_iterations=1,
                llm_client=client,
                verbose=False,
            )


if __name__ == "__main__":
    unittest.main()
