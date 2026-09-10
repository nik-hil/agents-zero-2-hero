#!/usr/bin/env python3
"""Stamp README.md from lessons.yml for the current git tag.

The README has two generated regions marked with HTML comments:

    <!-- BEGIN:checkpoint --> ... <!-- END:checkpoint -->
    <!-- BEGIN:roadmap -->    ... <!-- END:roadmap -->

This script rewrites what's between those markers based on:
  * lessons.yml   (the curriculum)
  * the current git tag (git describe), or --tag / $LESSON_TAG override

Because the README is committed at each tag, `git checkout <tag>` then shows the
README as of that lesson — that's what makes the README "dynamic per tag".

Usage:
    python scripts/stamp_readme.py            # detect tag from git
    python scripts/stamp_readme.py --tag v0.2-new-tools
    python scripts/stamp_readme.py --check    # non-zero exit if out of date

Requires PyYAML:  pip install -r requirements-dev.txt
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install -r requirements-dev.txt")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS = os.path.join(ROOT, "lessons.yml")
README = os.path.join(ROOT, "README.md")

PILLARS = {
    "loop": "🔄 Agent Loop",
    "providers": "🔌 Providers",
    "toolkit": "🔧 Toolkit",
    "context": "🧠 Context & Memory",
    "governance": "🛡️ Governance",
    "swarm": "🤝 Swarm",
}
MARK = {"done": "✅", "next": "🚧", "planned": "○"}


def current_tag(override: str | None) -> str | None:
    if override:
        return override
    if os.environ.get("LESSON_TAG"):
        return os.environ["LESSON_TAG"]
    for cmd in (["git", "describe", "--tags", "--exact-match"],
                ["git", "describe", "--tags", "--abbrev=0"]):
        try:
            out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except FileNotFoundError:
            return None
    return None


def load_lessons() -> list[dict]:
    with open(LESSONS, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["lessons"]


def checkpoint_md(lessons: list[dict], tag: str | None) -> str:
    idx = next((i for i, l in enumerate(lessons) if l["tag"] == tag), None)
    if idx is None:
        # On master (or an unknown tag): the newest shipped lesson is "current".
        done = [i for i, l in enumerate(lessons) if l["status"] == "done"]
        idx = done[-1] if done else 0
    l = lessons[idx]
    pillar = PILLARS.get(l["pillar"], l["pillar"])
    return (
        f"**You are on `{l['tag']}` — lesson {idx + 1} of {len(lessons)}.**\n\n"
        f"### {l['title']}\n\n"
        f"- **Pillar:** {pillar}\n"
        f"- **Adds:** `{l['component']}`\n\n"
        f"{l['concept'].strip()}\n\n"
        f"```bash\n{l['run']}\n```"
    )


def roadmap_md(lessons: list[dict], tag: str | None) -> str:
    rows = ["| | Tag | Lesson | Adds | Pillar |",
            "|---|---|---|---|---|"]
    for l in lessons:
        mark = "👉" if l["tag"] == tag else MARK.get(l["status"], "○")
        pillar = PILLARS.get(l["pillar"], l["pillar"])
        rows.append(
            f"| {mark} | `{l['tag']}` | {l['title']} | `{l['component']}` | {pillar} |"
        )
    legend = "\n\n👉 you are here · ✅ shipped · 🚧 building next · ○ planned"
    return "\n".join(rows) + legend


def replace_region(text: str, name: str, body: str) -> str:
    begin, end = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"
    if begin not in text or end not in text:
        sys.exit(f"Marker <!-- BEGIN/END:{name} --> missing from README.md")
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{begin}\n{body}\n{end}{tail}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if README is not up to date (for CI)")
    args = ap.parse_args()

    lessons = load_lessons()
    tag = current_tag(args.tag)

    with open(README, encoding="utf-8") as fh:
        original = fh.read()

    updated = replace_region(original, "checkpoint", checkpoint_md(lessons, tag))
    updated = replace_region(updated, "roadmap", roadmap_md(lessons, tag))

    if args.check:
        if updated != original:
            print("README.md is out of date. Run: python scripts/stamp_readme.py")
            return 1
        print("README.md is up to date.")
        return 0

    with open(README, "w", encoding="utf-8") as fh:
        fh.write(updated)
    print(f"Stamped README.md for tag: {tag or '(no tag / master)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
