"""compaction.py — keep the conversation under the context window (lesson v0.9).

Every iteration the agent appends messages: its thinking, tool calls, and
(often huge) tool results. Left alone, `messages` grows until it overflows the
model's context window. Compaction fixes that: when the history gets too big,
**summarize the older middle into one short note** and keep only:

    [ system prompt ] [ original task ] [ SUMMARY of the middle ] [ recent turns ]

We measure size in characters (a rough proxy for tokens — about 4 chars/token)
so there's no tokenizer dependency. The summary can be produced by the LLM
(faithful) or by a cheap offline heuristic (no API needed — used in tests).

Safety note: the compacted result contains **no tool-call / tool messages** — the
middle is folded into plain text — so the rebuilt message list is always a valid
request (no orphaned tool_call/tool pairing).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


def _role(msg) -> str:
    return msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")


def _content(msg) -> str:
    c = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
    return c or ""


def _has_tool_calls(msg) -> bool:
    tc = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
    return bool(tc)


def estimate_size(messages) -> int:
    """Rough size of the whole message list, in characters."""
    return sum(len(_content(m)) for m in messages)


def heuristic_summarizer(text: str) -> str:
    """Offline fallback: no API. Keep the tail (most recent = most relevant)."""
    text = text.strip()
    limit = 800
    if len(text) <= limit:
        return text
    return "…(older detail omitted)…\n" + text[-limit:]


def llm_summarizer(client, model) -> Callable[[str], str]:
    """Real summarizer: ask the model to compress the earlier conversation."""
    def _summarize(text: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Summarize the conversation below in a few "
                 "bullet points: what was attempted, key results, decisions, and open "
                 "threads. Be concise but keep facts needed to continue the task."},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        return resp.choices[0].message.content or ""
    return _summarize


@dataclass
class Compactor:
    max_chars: int = 8000            # trigger threshold (chars)
    keep_recent: int = 6             # most recent messages kept verbatim
    summarizer: Callable[[str], str] = heuristic_summarizer

    def maybe_compact(self, messages):
        """Return (messages, changed). No-op until the size budget is exceeded."""
        if estimate_size(messages) <= self.max_chars or len(messages) <= 2:
            return messages, False

        # Always preserve the system prompt and the original task.
        preserved = [messages[0]]
        rest = messages[1:]
        if rest and _role(rest[0]) == "user":
            preserved.append(rest[0])
            rest = rest[1:]

        # Split the remainder into a middle (to summarize) and a recent tail.
        if self.keep_recent > 0:
            head, tail = rest[:-self.keep_recent], rest[-self.keep_recent:]
        else:
            head, tail = rest, []

        # Nothing meaningful to summarize (everything is system + task + recent)?
        # Then compaction can't help — do NOT churn every iteration. This guards
        # against a budget set below the fixed overhead (system prompt + memory).
        if not head:
            return messages, False

        # The tail must be self-contained text: no tool messages, no tool_calls.
        # Anything that isn't clean user/assistant text is folded into the summary.
        clean_tail = []
        for m in tail:
            if _role(m) in ("user", "assistant") and _content(m) and not _has_tool_calls(m):
                clean_tail.append({"role": _role(m), "content": _content(m)})
            else:
                head.append(m)

        summary = self.summarizer(_render(head))
        summary_msg = {"role": "user",
                       "content": "[Earlier conversation compacted to save context]\n" + summary}
        return preserved + [summary_msg] + clean_tail, True


def _render(messages) -> str:
    """Flatten messages to 'role: content' text for the summarizer."""
    lines = []
    for m in messages:
        content = _content(m)
        if _has_tool_calls(m) and not content:
            content = "(made tool calls)"
        lines.append(f"{_role(m)}: {content}")
    return "\n".join(lines)
