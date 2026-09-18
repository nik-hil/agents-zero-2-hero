"""Tests for mcp_client.py against the bundled example server (offline, no key).

These spawn mcp_servers/echo_server.py as a real subprocess and talk MCP to it —
no network, no API key. They prove the client can initialize, list, and call.

Run:
    python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

from mcp_client import MCPClient, to_openai_schemas, make_proxies

ROOT = Path(__file__).resolve().parent.parent
SERVER = [sys.executable, str(ROOT / "mcp_servers" / "echo_server.py")]


class LiveServer(unittest.TestCase):
    def setUp(self):
        self.client = MCPClient(SERVER).start()
        self.addCleanup(self.client.stop)

    def test_list_tools(self):
        names = {t["name"] for t in self.client.list_tools()}
        self.assertEqual(names, {"echo", "add"})

    def test_call_add(self):
        out = self.client.call_tool("add", {"a": 21, "b": 21})
        self.assertEqual(out["content"][0]["text"], "42")

    def test_call_echo(self):
        out = self.client.call_tool("echo", {"text": "hi"})
        self.assertEqual(out["content"][0]["text"], "hi")

    def test_error_surfaces(self):
        with self.assertRaises(RuntimeError):
            self.client.call_tool("nonexistent", {})


class SchemaAndProxies(unittest.TestCase):
    def setUp(self):
        self.client = MCPClient(SERVER).start()
        self.addCleanup(self.client.stop)
        self.tools = self.client.list_tools()

    def test_schemas_are_namespaced_and_valid(self):
        schemas = to_openai_schemas(self.tools)
        names = {s["function"]["name"] for s in schemas}
        self.assertEqual(names, {"mcp__echo", "mcp__add"})
        add = next(s for s in schemas if s["function"]["name"] == "mcp__add")
        self.assertEqual(add["function"]["parameters"]["required"], ["a", "b"])

    def test_proxy_calls_through(self):
        proxies = make_proxies(self.client, self.tools)
        result = proxies["mcp__add"](a=2, b=3)
        self.assertEqual(result["content"][0]["text"], "5")


if __name__ == "__main__":
    unittest.main()
