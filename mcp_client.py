"""mcp_client.py — a minimal Model Context Protocol client (lesson v0.11).

MCP is how agents use tools they didn't ship with: an external *server* exposes
tools, and the harness (the *client*) discovers and calls them. This is a tiny
client for the **stdio** transport — it launches a server as a subprocess and
exchanges newline-delimited JSON-RPC 2.0 messages over stdin/stdout.

Flow:
    start()        -> spawn server, send `initialize`, then `initialized`
    list_tools()   -> `tools/list`  (returns the server's tool definitions)
    call_tool()    -> `tools/call`  (runs one tool, returns its result)

Then `to_openai_schemas()` and `make_proxies()` turn those remote tools into the
exact same (schema, callable) shape the harness already uses — so MCP tools drop
straight into TOOLS / TOOL_SCHEMAS alongside the built-in ones.
"""
from __future__ import annotations

import json
import subprocess


class MCPClient:
    def __init__(self, command: list[str]):
        self.command = command
        self.proc: subprocess.Popen | None = None
        self._id = 0
        self.tools: list[dict] = []

    # -- lifecycle -----------------------------------------------------------
    def start(self):
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, bufsize=1,
        )
        self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "agents-zero-2-hero", "version": "0.11"},
        })
        self._notify("notifications/initialized")
        return self

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # -- JSON-RPC plumbing ---------------------------------------------------
    def _send(self, msg: dict):
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _notify(self, method: str, params: dict | None = None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _request(self, method: str, params: dict | None = None) -> dict:
        assert self.proc and self.proc.stdout
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}})
        # Read lines until we see the response with our id (skip notifications).
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed the connection")
            data = json.loads(line)
            if data.get("id") == self._id:
                if "error" in data:
                    raise RuntimeError(f"MCP error: {data['error']}")
                return data.get("result", {})

    # -- MCP methods ---------------------------------------------------------
    def list_tools(self) -> list[dict]:
        self.tools = self._request("tools/list").get("tools", [])
        return self.tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self._request("tools/call", {"name": name, "arguments": arguments})


def to_openai_schemas(tools: list[dict], prefix: str = "mcp__") -> list[dict]:
    """Convert MCP tool defs to OpenAI function-tool schemas (namespaced)."""
    schemas = []
    for t in tools:
        schemas.append({
            "type": "function",
            "function": {
                "name": prefix + t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        })
    return schemas


def make_proxies(client: MCPClient, tools: list[dict], prefix: str = "mcp__") -> dict:
    """Build {schema_name: callable} that forward to the MCP server."""
    proxies = {}
    for t in tools:
        real_name = t["name"]

        def _proxy(_real=real_name, **kwargs):
            return client.call_tool(_real, kwargs)

        proxies[prefix + real_name] = _proxy
    return proxies
