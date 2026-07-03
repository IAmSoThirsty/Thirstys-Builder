"""Unit tests for the CLI core modules: config, session, skills, confirm.

Run: PYTHONPATH=thirsty-ai-builder/cli python -m unittest thirsty-ai-builder.backend.tests.test_cli
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


# Make the CLI package importable.
CLI_PKG = Path(__file__).resolve().parents[2] / "cli" / "thirsty_ai_builder_cli"
sys.path.insert(0, str(CLI_PKG.parent))

from thirsty_ai_builder_cli import config as cli_config
from thirsty_ai_builder_cli import confirm, session, skills as cli_skills


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_config = cli_config.CONFIG_DIR
        self._old_skills = cli_config.SKILLS_DIR
        self._old_drafts = cli_config.DRAFTS_DIR
        self._old_sessions = cli_config.SESSIONS_DIR
        cli_config.CONFIG_DIR = Path(self._tmp.name) / ".thirsty-ai-builder"
        cli_config.SKILLS_DIR = cli_config.CONFIG_DIR / "skills"
        cli_config.DRAFTS_DIR = cli_config.SKILLS_DIR / "_drafts"
        cli_config.SESSIONS_DIR = cli_config.CONFIG_DIR / "sessions"

    def tearDown(self):
        cli_config.CONFIG_DIR = self._old_config
        cli_config.SKILLS_DIR = self._old_skills
        cli_config.DRAFTS_DIR = self._old_drafts
        cli_config.SESSIONS_DIR = self._old_sessions
        self._tmp.cleanup()

    def test_profiles_have_required_keys(self):
        for name, p in cli_config.PROFILES.items():
            self.assertIn("temperature", p)
            self.assertIn("num_ctx", p)
            self.assertIn("top_p", p)
            self.assertIn("description", p)
            self.assertGreaterEqual(p["temperature"], 0.0)
            self.assertLessEqual(p["temperature"], 2.0)

    def test_default_profile_is_balanced(self):
        self.assertEqual(cli_config.DEFAULT_PROFILE, "balanced")

    def test_load_returns_defaults_when_no_config(self):
        cfg = cli_config.load()
        self.assertEqual(cfg.profile, "balanced")
        self.assertEqual(cfg.model, "qwen2.5-coder:7b")

    def test_ensure_dirs_creates_tree(self):
        cli_config.ensure_dirs()
        self.assertTrue(cli_config.CONFIG_DIR.exists())
        self.assertTrue(cli_config.SKILLS_DIR.exists())
        self.assertTrue(cli_config.DRAFTS_DIR.exists())
        self.assertTrue(cli_config.SESSIONS_DIR.exists())


class TestConfirm(unittest.TestCase):
    def test_generate_returns_six_digits(self):
        code, expires = confirm.generate("write", {"path": "a.txt", "content": "x"})
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertGreater(expires, 0)

    def test_fingerprint_is_stable(self):
        a = confirm.fingerprint("write", {"path": "a.txt", "content": "x"})
        b = confirm.fingerprint("write", {"content": "x", "path": "a.txt"})
        self.assertEqual(a, b)  # sorted internally

    def test_fingerprint_differs_for_different_args(self):
        a = confirm.fingerprint("write", {"path": "a.txt"})
        b = confirm.fingerprint("write", {"path": "b.txt"})
        self.assertNotEqual(a, b)


class TestSession(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_session_has_unique_id(self):
        s1 = session.new_session("balanced", "qwen2.5-coder:7b")
        s2 = session.new_session("balanced", "qwen2.5-coder:7b")
        self.assertNotEqual(s1.session_id, s2.session_id)

    def test_session_round_trip(self):
        s = session.new_session("precise", "mistral")
        s.add_turn(session.Turn(user="hi", assistant="hello", tool_calls=[{"tool": "read", "args": {"path": "a.txt"}}]))
        path = session.save(s, self._dir)
        self.assertTrue(path.exists())
        loaded = session.load_recent(5, self._dir)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].model, "mistral")
        self.assertEqual(loaded[0].turns[0].user, "hi")

    def test_load_recent_isolated_from_other_dirs(self):
        # Sanity: load_recent(5, dirA) must not return files from dirB.
        s = session.new_session("balanced", "qwen2.5-coder:7b")
        s.add_turn(session.Turn(user="x", assistant="y"))
        other = Path(self._tmp.name) / "other"
        session.save(s, other)
        self.assertEqual(len(session.load_recent(5, Path(self._tmp.name))), 0)
        self.assertEqual(len(session.load_recent(5, other)), 1)

    def test_tool_sequence_categorises_by_arg_shape(self):
        s = session.new_session("balanced", "qwen2.5-coder:7b")
        s.add_turn(session.Turn(user="x", assistant="y", tool_calls=[
            {"tool": "read", "args": {"path": "a"}},
            {"tool": "grep", "args": {"pattern": "x"}},
        ]))
        s.add_turn(session.Turn(user="p", assistant="q", tool_calls=[
            {"tool": "read", "args": {"path": "b"}},
        ]))
        seqs = session.tool_sequence(s)
        self.assertEqual(len(seqs), 2)
        self.assertEqual(seqs[0], ("read:path", "grep:pattern"))
        self.assertEqual(seqs[1], ("read:path",))


class TestSkills(unittest.TestCase):
    def test_parse_skill_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "demo"
            d.mkdir()
            (d / "SKILL.md").write_text(
                "---\nname: demo\ndescription: a demo skill\ntools: [read, grep]\n---\n# body\n",
                encoding="utf-8",
            )
            s = cli_skills.parse_skill_file(d / "SKILL.md")
            self.assertIsNotNone(s)
            self.assertEqual(s.name, "demo")
            self.assertEqual(s.tools, ["read", "grep"])

    def test_parse_skill_returns_none_on_garbage(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "bad"
            d.mkdir()
            (d / "SKILL.md").write_text("no frontmatter here", encoding="utf-8")
            self.assertIsNone(cli_skills.parse_skill_file(d / "SKILL.md"))

    def test_match_skill_picks_best_overlap(self):
        skills = [
            cli_skills.Skill(name="code-review", description="review code for security and style", tools=[], body="", path=Path("/x")),
            cli_skills.Skill(name="refactor",   description="refactor messy code into clean modules", tools=[], body="", path=Path("/x")),
        ]
        s = cli_skills.match_skill(skills, "please refactor the messy module")
        self.assertIsNotNone(s)
        self.assertEqual(s.name, "refactor")

    def test_match_skill_returns_none_when_no_overlap(self):
        skills = [cli_skills.Skill(name="x", description="nothing related", tools=[], body="", path=Path("/x"))]
        self.assertIsNone(cli_skills.match_skill(skills, "the quick brown fox"))

    def test_load_all_skips_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            sd = Path(tmp) / "skills"
            (sd / "live").mkdir(parents=True)
            (sd / "live" / "SKILL.md").write_text("---\nname: live\ndescription: live\ntools: []\n---\n", encoding="utf-8")
            dd = sd / "_drafts"
            (dd / "draft1").mkdir(parents=True)
            (dd / "draft1" / "SKILL.md").write_text("---\nname: draft1\ndescription: draft\ntools: []\n---\n", encoding="utf-8")
            loaded = cli_skills.load_all(sd)
            drafts = cli_skills.load_drafts(dd)
            self.assertEqual([s.name for s in loaded], ["live"])
            self.assertEqual([s.name for s in drafts], ["draft1"])

    def test_render_skill_round_trips(self):
        s = cli_skills.Skill(name="t", description="d", tools=["a", "b"], body="# body", path=Path("/x"))
        text = cli_skills.render_skill(s)
        self.assertIn("name: t", text)
        self.assertIn("tools: [a, b]", text)
        self.assertIn("# body", text)


if __name__ == "__main__":
    unittest.main()
