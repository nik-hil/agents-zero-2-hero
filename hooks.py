"""hooks.py — lifecycle hooks around every tool call (lesson v0.7).

Permissions (v0.6) answered "is this allowed?". Hooks answer "what else should
happen around it?" — logging, metrics, redaction, or extra custom blocking —
*without* touching the tools or the loop. Two moments:

    PreToolUse   fires before a tool runs. Can observe, rewrite the args, or
                 block the call.
    PostToolUse  fires after a tool runs. Can observe or rewrite the result.

A hook is just a callable that returns a HookResult (or None to do nothing):

    pre  hook: fn(tool, args)          -> HookResult | None
    post hook: fn(tool, args, result)  -> HookResult | None

Hooks run in registration order; each pre-hook sees the (possibly rewritten)
args from the previous one.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class HookResult:
    allow: bool = True            # pre-hook: False blocks the tool call
    reason: str = ""              # why it was blocked
    args: dict | None = None      # pre-hook: if set, replaces the tool args
    result: dict | None = None    # post-hook: if set, replaces the tool result


@dataclass
class HookManager:
    pre: list = field(default_factory=list)
    post: list = field(default_factory=list)

    def run_pre(self, tool: str, args: dict):
        """Returns (allowed, reason, args) — args may have been rewritten."""
        for hook in self.pre:
            r = hook(tool, args)
            if r is None:
                continue
            if r.args is not None:
                args = r.args
            if not r.allow:
                return False, r.reason, args
        return True, "", args

    def run_post(self, tool: str, args: dict, result: dict):
        """Returns the (possibly rewritten) result."""
        for hook in self.post:
            r = hook(tool, args, result)
            if r is None:
                continue
            if r.result is not None:
                result = r.result
        return result


# --------------------------------------------------------------------------
# Example hooks — small, copy-pasteable building blocks.
# --------------------------------------------------------------------------

class TimingLogger:
    """Logs each tool call and how long it took. Register .pre and .post."""

    def __init__(self):
        self._start = {}

    def pre(self, tool: str, args: dict) -> HookResult | None:
        self._start[tool] = time.perf_counter()
        print(f"  [hook] → {tool}({args})")
        return None

    def post(self, tool: str, args: dict, result: dict) -> HookResult | None:
        dt = time.perf_counter() - self._start.get(tool, time.perf_counter())
        print(f"  [hook] ← {tool} done in {dt*1000:.1f} ms")
        return None


def make_counter(counts: dict):
    """Returns a post-hook that tallies how often each tool is used."""
    def _hook(tool: str, args: dict, result: dict) -> HookResult | None:
        counts[tool] = counts.get(tool, 0) + 1
        return None
    return _hook


def block_tool(name: str):
    """Returns a pre-hook that blocks one tool by name (e.g. 'bash')."""
    def _hook(tool: str, args: dict) -> HookResult | None:
        if tool == name:
            return HookResult(allow=False, reason=f"hook policy: {name} disabled")
        return None
    return _hook


def redact_post_hook(tool: str, args: dict, result: dict) -> HookResult | None:
    """Post-hook: mask anything that looks like an API key in tool output."""
    import json
    import re

    dumped = json.dumps(result)
    masked = re.sub(r"(sk-[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+", r"\1…REDACTED", dumped)
    if masked != dumped:
        return HookResult(result={"redacted": True, "content": masked})
    return None
