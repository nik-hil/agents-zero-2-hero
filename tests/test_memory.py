"""Unit tests for memory.py (offline — always run, no key needed).

Everything is exercised in a temp directory so the repo's real MEMORY.md and
.agent_sessions/ are never touched.

Run:
    python -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

from memory import Memory, SessionStore


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_remember_appends_and_loads(self):
        m = Memory(self.dir)
        self.assertEqual(m.load_memory(), "")          # nothing yet
        m.remember("favorite language is Python")
        m.remember("deploys happen on Fridays")
        loaded = m.load_memory()
        self.assertIn("favorite language is Python", loaded)
        self.assertIn("deploys happen on Fridays", loaded)

    def test_remember_rejects_empty(self):
        m = Memory(self.dir)
        self.assertIn("error", m.remember("   "))

    def test_load_context_reads_agents_md(self):
        (self.dir / "AGENTS.md").write_text("use tabs, not spaces", encoding="utf-8")
        m = Memory(self.dir)
        ctx = m.load_context()
        self.assertIn("AGENTS.md", ctx)
        self.assertIn("use tabs", ctx)

    def test_system_addendum_combines_context_and_memory(self):
        (self.dir / "AGENTS.md").write_text("project rule X", encoding="utf-8")
        m = Memory(self.dir)
        m.remember("remembered fact Y")
        add = m.system_addendum()
        self.assertIn("Project context", add)
        self.assertIn("project rule X", add)
        self.assertIn("Remembered notes", add)
        self.assertIn("remembered fact Y", add)

    def test_addendum_empty_when_nothing_present(self):
        self.assertEqual(Memory(self.dir).system_addendum(), "")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SessionStore(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_then_load_round_trip(self):
        transcript = [{"role": "user", "content": "hi"},
                      {"role": "assistant", "content": "done"}]
        self.store.save("s1", transcript)
        self.assertEqual(self.store.load("s1"), transcript)

    def test_load_missing_returns_none(self):
        self.assertIsNone(self.store.load("nope"))

    def test_as_text_formats_roles(self):
        text = self.store.as_text([{"role": "user", "content": "hi"},
                                   {"role": "tool", "content": "{}"}])
        self.assertEqual(text, "user: hi\ntool: {}")


if __name__ == "__main__":
    unittest.main()
