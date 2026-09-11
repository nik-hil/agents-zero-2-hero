"""permissions.py — a small permission layer for the agent (lesson v0.6).

The bash tool (v0.3) already had an allowlist. This generalizes that idea into
one gate that every tool call passes through *before* it runs. The model still
decides WHAT to do; the harness decides whether it's ALLOWED.

Three modes:

    auto     allow everything            (sandboxed / trusted runs)
    default  allow reads, ASK on writes  (day-to-day; approver decides)
    plan     allow reads, BLOCK writes   (review-only, no side effects)

Plus two config knobs:

    path_rules       deny tool calls whose file path matches a glob
    denied_commands  deny bash/execute_code whose text contains a phrase

A tool is either read-only (safe) or mutating (write_file, edit_file,
execute_code, bash). Only mutating tools are gated by the mode.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    AUTO = "auto"
    DEFAULT = "default"
    PLAN = "plan"


# Tools that cannot change anything -> always safe to run.
READ_ONLY_TOOLS = {"list_files", "read_file", "code_search", "finish"}

# Sensible defaults; a demo can pass its own.
DEFAULT_DENIED_COMMANDS = [
    "rm -rf", "rm -fr", "mkfs", "dd if=", ":(){", "shutdown", "reboot",
    "shutil.rmtree", "os.system", "> /dev/",
]
# Which argument holds a file path, per tool.
PATH_ARG = {"read_file": "filepath", "write_file": "filepath", "edit_file": "filepath"}
# Which argument holds runnable text, per tool.
TEXT_ARG = {"bash": "command", "execute_code": "code"}


@dataclass
class Decision:
    allowed: bool
    reason: str = ""


def _always_deny(tool: str, args: dict) -> bool:
    """Approver used when none is supplied: deny anything that needs asking."""
    return False


@dataclass
class PermissionChecker:
    mode: Mode = Mode.AUTO
    denied_commands: list[str] = field(default_factory=lambda: list(DEFAULT_DENIED_COMMANDS))
    # (glob, allow) rules; first match wins. e.g. [("*.env", False)]
    path_rules: list[tuple[str, bool]] = field(default_factory=list)
    # Called for mutating tools in DEFAULT mode; return True to allow.
    approver: callable = _always_deny

    def __post_init__(self):
        self.mode = Mode(self.mode)  # accept a plain string too

    def check(self, tool: str, args: dict) -> Decision:
        # 1) Hard rules apply in every mode (even auto).
        text = args.get(TEXT_ARG.get(tool, ""), "") if tool in TEXT_ARG else ""
        for phrase in self.denied_commands:
            if phrase in text:
                return Decision(False, f"blocked: command contains {phrase!r}")

        path = args.get(PATH_ARG.get(tool, ""), "") if tool in PATH_ARG else ""
        for pattern, allow in self.path_rules:
            if fnmatch.fnmatch(path, pattern):
                if not allow:
                    return Decision(False, f"blocked: path {path!r} matches deny rule {pattern!r}")
                break  # explicitly allowed

        # 2) Read-only tools are always fine.
        if tool in READ_ONLY_TOOLS:
            return Decision(True)

        # 3) Mode governs mutating tools.
        if self.mode is Mode.AUTO:
            return Decision(True)
        if self.mode is Mode.PLAN:
            return Decision(False, f"blocked: plan mode forbids mutating tool {tool!r}")
        # DEFAULT -> ask the approver
        if self.approver(tool, args):
            return Decision(True, "approved")
        return Decision(False, f"denied: approval refused for {tool!r}")


def cli_approver(tool: str, args: dict) -> bool:
    """Interactive approver: prompt the user y/n on the terminal."""
    print(f"\n[permission] allow {tool}({args})? [y/N] ", end="", flush=True)
    try:
        return input().strip().lower() in ("y", "yes")
    except EOFError:
        return False
