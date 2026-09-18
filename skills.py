"""skills.py — on-demand skills (lesson v0.10).

A *skill* is a Markdown file of domain knowledge — how to write a good commit,
house Python style, a deploy runbook — that the agent loads **only when a task
needs it**. That's the key idea: you can have dozens of skills without paying for
them in every prompt. The agent always sees a cheap **catalog** (name +
description); it pulls the full body on demand via a tool.

Layout (Claude-style):

    skills/<name>/SKILL.md

Each SKILL.md starts with simple frontmatter, then the body:

    ---
    name: python-style
    description: How to write clean, idiomatic Python for this project.
    ---
    # Python style
    ...the actual guidance...
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a '--- ... ---' header from the body. Returns (meta, body)."""
    meta: dict = {}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            if ":" in lines[i]:
                k, v = lines[i].split(":", 1)
                meta[k.strip()] = v.strip()
            i += 1
        body = "\n".join(lines[i + 1:]).strip()  # skip the closing ---
        return meta, body
    return meta, text.strip()


@dataclass
class Skill:
    name: str
    description: str
    path: Path

    def body(self) -> str:
        """Load the full skill text on demand (frontmatter stripped)."""
        _, body = _parse_frontmatter(self.path.read_text(encoding="utf-8"))
        return body


class SkillLibrary:
    """Discovers skills under a directory; loads bodies only when asked."""

    def __init__(self, skills_dir):
        self.dir = Path(skills_dir)
        self.skills: dict[str, Skill] = {}
        self._discover()

    def _discover(self):
        if not self.dir.is_dir():
            return
        for sub in sorted(self.dir.iterdir()):
            md = sub / "SKILL.md" if sub.is_dir() else (sub if sub.suffix == ".md" else None)
            if not md or not md.is_file():
                continue
            meta, _ = _parse_frontmatter(md.read_text(encoding="utf-8"))
            name = meta.get("name") or sub.stem
            self.skills[name] = Skill(name, meta.get("description", ""), md)

    def names(self) -> list[str]:
        return list(self.skills)

    def catalog(self) -> list[dict]:
        """Cheap list of {name, description} — safe to keep in the prompt."""
        return [{"name": s.name, "description": s.description} for s in self.skills.values()]

    def catalog_text(self) -> str:
        return "\n".join(f"- {s['name']}: {s['description']}" for s in self.catalog())

    def load(self, name: str) -> dict:
        """Return the full body of one skill (the on-demand step)."""
        skill = self.skills.get(name)
        if not skill:
            return {"error": f"unknown skill: {name}", "available": self.names()}
        return {"name": name, "content": skill.body()}
