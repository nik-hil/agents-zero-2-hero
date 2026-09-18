"""memory.py — context injection, persistent memory, and session resume (v0.8).

Until now the agent started every run as a blank slate. Real agents remember:

  * Project context — steady facts about *this* repo, written by a human in
    AGENTS.md / CLAUDE.md and injected into the system prompt every run.
  * Persistent memory — notes the agent chooses to keep across runs, appended to
    MEMORY.md via a `remember` tool and injected back on the next run.
  * Sessions — a saved transcript so a later run can resume with prior context.

All three are just files on disk. That's the whole trick: memory = files you read
into the prompt, plus a tool to write them.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

# Human-authored project context, checked into the repo.
CONTEXT_FILENAMES = ["AGENTS.md", "CLAUDE.md"]


@dataclass
class Memory:
    """Reads project-context files and manages the MEMORY.md note store."""

    base_dir: Path
    memory_file: str = "MEMORY.md"

    def __post_init__(self):
        self.base_dir = Path(self.base_dir)

    def load_context(self) -> str:
        """Concatenate any AGENTS.md / CLAUDE.md found in base_dir."""
        parts = []
        for name in CONTEXT_FILENAMES:
            p = self.base_dir / name
            if p.is_file():
                parts.append(f"### {name}\n{p.read_text(encoding='utf-8').strip()}")
        return "\n\n".join(parts)

    def load_memory(self) -> str:
        """The current contents of MEMORY.md (empty string if none yet)."""
        p = self.base_dir / self.memory_file
        return p.read_text(encoding="utf-8").strip() if p.is_file() else ""

    def remember(self, note: str) -> dict:
        """Append one timestamped note to MEMORY.md so future runs recall it."""
        note = note.strip()
        if not note:
            return {"error": "empty note"}
        p = self.base_dir / self.memory_file
        stamp = time.strftime("%Y-%m-%d %H:%M")
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"- ({stamp}) {note}\n")
        return {"remembered": note, "file": p.name}

    def system_addendum(self) -> str:
        """The text to append to the system prompt: context + remembered notes."""
        blocks = []
        ctx = self.load_context()
        if ctx:
            blocks.append("## Project context\n" + ctx)
        mem = self.load_memory()
        if mem:
            blocks.append("## Remembered notes (persistent memory)\n" + mem)
        return "\n\n".join(blocks).strip()


@dataclass
class SessionStore:
    """Saves/loads a plain-text transcript so a run can be resumed later."""

    base_dir: Path
    dirname: str = ".agent_sessions"

    def __post_init__(self):
        self.dir = Path(self.base_dir) / self.dirname

    def _path(self, name: str) -> Path:
        return self.dir / f"{name}.json"

    def save(self, name: str, transcript: list[dict]) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self._path(name)
        p.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
        return p

    def load(self, name: str) -> list[dict] | None:
        p = self._path(name)
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def as_text(self, transcript: list[dict]) -> str:
        """Render a transcript as 'role: content' lines for prompt injection."""
        return "\n".join(f"{m['role']}: {m['content']}" for m in transcript)
