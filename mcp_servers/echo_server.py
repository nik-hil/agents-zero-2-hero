#!/usr/bin/env python3
"""A tiny example MCP server (stdio transport, pure stdlib).

This exists so the MCP lesson is self-contained: the harness can connect to a
*real* Model Context Protocol server without installing anything. It speaks
newline-delimited JSON-RPC 2.0 over stdin/stdout and exposes two trivial tools:

    echo(text)   -> returns the same text
    add(a, b)    -> returns a + b

Run it directly to eyeball the protocol:
    echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python mcp_servers/echo_server.py
"""
import json
import sys

TOOLS = {
    "echo": {
        "description": "Echo back the given text.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    "add": {
        "description": "Add two numbers and return the sum.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
}


def _call(name, args):
    if name == "echo":
        return str(args.get("text", ""))
    if name == "add":
        return str(args.get("a", 0) + args.get("b", 0))
    raise KeyError(name)


def handle(req):
    """Return a result dict for a request method, or raise for an error."""
    method = req.get("method")
    params = req.get("params") or {}

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "echo-server", "version": "0.1"},
        }
    if method == "tools/list":
        return {"tools": [{"name": n, **d} for n, d in TOOLS.items()]}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        text = _call(name, args)
        return {"content": [{"type": "text", "text": text}]}
    raise ValueError(f"unknown method: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        # Notifications have no id and expect no response.
        if "id" not in req:
            continue
        try:
            result = handle(req)
            resp = {"jsonrpc": "2.0", "id": req["id"], "result": result}
        except Exception as e:  # noqa: BLE001 — report any failure as JSON-RPC error
            resp = {"jsonrpc": "2.0", "id": req["id"],
                    "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
