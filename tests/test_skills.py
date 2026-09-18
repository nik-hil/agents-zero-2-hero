"""Unit tests for skills.py (offline — always run, no key needed).

Builds a temp skills/ tree so the repo's real skills/ isn't required.

Run:
    python -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

from skills import SkillLibrary, _parse_frontmatter


SKILL_A = """\
---
name: alpha
description: The alpha skill.
---
# Alpha
Do the alpha thing.
"""

SKILL_B = """\
---
name: beta
description: The beta skill.
---
# Beta
Do the beta thing.
"""


class Frontmatter(unittest.TestCase):
    def test_parses_meta_and_body(self):
        meta, body = _parse_frontmatter(SKILL_A)
        self.assertEqual(meta["name"], "alpha")
        self.assertEqual(meta["description"], "The alpha skill.")
        self.assertIn("Do the alpha thing.", body)
        self.assertNotIn("---", body)         # frontmatter stripped

    def test_no_frontmatter_returns_whole_text(self):
        meta, body = _parse_frontmatter("# Just a heading")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Just a heading")


class Library(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "alpha").mkdir()
        (root / "alpha" / "SKILL.md").write_text(SKILL_A, encoding="utf-8")
        (root / "beta").mkdir()
        (root / "beta" / "SKILL.md").write_text(SKILL_B, encoding="utf-8")
        self.lib = SkillLibrary(root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_discovers_all_skills(self):
        self.assertEqual(set(self.lib.names()), {"alpha", "beta"})

    def test_catalog_has_names_and_descriptions(self):
        cat = self.lib.catalog()
        self.assertIn({"name": "alpha", "description": "The alpha skill."}, cat)

    def test_load_returns_body_only(self):
        out = self.lib.load("alpha")
        self.assertEqual(out["name"], "alpha")
        self.assertIn("Do the alpha thing.", out["content"])
        self.assertNotIn("description:", out["content"])   # not the frontmatter

    def test_load_unknown_returns_error(self):
        out = self.lib.load("nope")
        self.assertIn("error", out)
        self.assertIn("beta", out["available"])

    def test_missing_dir_is_empty_library(self):
        self.assertEqual(SkillLibrary(Path(self.tmp.name) / "does-not-exist").names(), [])


if __name__ == "__main__":
    unittest.main()
