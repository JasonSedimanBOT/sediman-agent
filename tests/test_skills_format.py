from __future__ import annotations

import json
from pathlib import Path

import pytest

from sediman.skills.format import SkillData, parse_skill_md, parse_skill_json, load_skill


class TestSkillData:
    def test_defaults(self):
        s = SkillData(name="x", description="d", steps=["a"])
        assert s.version == 1
        assert s.category == "general"
        assert s.source == "local"
        assert s.steps == ["a"]

    def test_to_json(self):
        s = SkillData(name="test", description="desc", steps=["s1"], category="cat", version=2)
        j = s.to_json()
        assert j["name"] == "test"
        assert j["description"] == "desc"
        assert j["steps"] == ["s1"]
        assert j["category"] == "cat"
        assert j["version"] == 2

    def test_to_skill_md(self):
        s = SkillData(
            name="my-skill",
            description="Does something cool",
            steps=["step one", "step two"],
            variables=["QUERY"],
        )
        md = s.to_skill_md()
        assert "---" in md
        assert "name: my-skill" in md
        assert "description:" in md
        assert "Does something cool" in md
        assert "variables:" in md
        assert "QUERY" in md
        assert "1. step one" in md
        assert "2. step two" in md

    def test_to_skill_md_without_variables(self):
        s = SkillData(name="x", description="d", steps=["s"])
        md = s.to_skill_md()
        assert "variables" not in md

    def test_to_skill_md_with_schedule(self):
        s = SkillData(name="x", description="d", steps=["s"], schedule="0 9 * * *")
        md = s.to_skill_md()
        assert 'schedule: "0 9 * * *"' in md

    def test_to_json_roundtrip(self):
        s = SkillData(
            name="roundtrip",
            description="test roundtrip",
            steps=["a", "b"],
            category="test",
            variables=["X"],
            schedule="* * * * *",
            author="tester",
            license="MIT",
        )
        j = s.to_json()
        md = s.to_skill_md()
        assert j["name"] == s.name
        assert j["variables"] == ["X"]
        assert j["schedule"] == "* * * * *"
        assert "roundtrip" in md


class TestParseSkillMd:
    def test_parse_full_frontmatter(self):
        md = """---
name: google-search
description: Search Google
category: search
version: 2
variables:
  - QUERY
  - LIMIT
schedule: "0 * * * *"
author: alice
license: MIT
---

# Google Search

Search Google for stuff.

## Steps

1. Navigate to google.com
2. Type query
3. Extract results
"""
        s = parse_skill_md(md)
        assert s is not None
        assert s.name == "google-search"
        assert s.description == "Search Google"
        assert s.category == "search"
        assert s.version == 2
        assert s.variables == ["QUERY", "LIMIT"]
        assert s.schedule == "0 * * * *"
        assert s.author == "alice"
        assert s.license == "MIT"
        assert len(s.steps) == 3
        assert "Navigate to google.com" in s.steps[0]

    def test_parse_minimal_frontmatter(self):
        md = """---
name: minimal
description: Minimal skill
---

# Minimal

## Steps

1. Do something
"""
        s = parse_skill_md(md)
        assert s is not None
        assert s.name == "minimal"
        assert s.description == "Minimal skill"
        assert s.category == "general"
        assert s.version == 1
        assert s.variables == []

    def test_parse_no_frontmatter(self):
        md = "# Just a heading\n\nSome text without frontmatter"
        s = parse_skill_md(md)
        assert s is None

    def test_parse_missing_name(self):
        md = """---
description: No name field
---

# Skill
"""
        s = parse_skill_md(md)
        assert s is None

    def test_parse_empty_string(self):
        assert parse_skill_md("") is None


class TestParseSkillJson:
    def test_parse_valid_json(self):
        raw = json.dumps({
            "name": "test-skill",
            "description": "A test",
            "steps": ["s1", "s2"],
            "category": "testing",
            "version": 3,
            "variables": ["VAR1"],
            "schedule": "0 0 * * *",
        })
        s = parse_skill_json(raw)
        assert s is not None
        assert s.name == "test-skill"
        assert s.steps == ["s1", "s2"]
        assert s.version == 3
        assert s.variables == ["VAR1"]

    def test_parse_minimal_json(self):
        raw = json.dumps({"name": "x", "description": "d", "steps": []})
        s = parse_skill_json(raw)
        assert s is not None
        assert s.name == "x"
        assert s.version == 1
        assert s.category == "general"

    def test_parse_invalid_json(self):
        assert parse_skill_json("not json") is None

    def test_parse_missing_name(self):
        raw = json.dumps({"description": "d"})
        assert parse_skill_json(raw) is None


class TestLoadSkill:
    def test_prefers_skill_json_over_md(self, tmp_path: Path):
        skill_dir = tmp_path / "test"
        skill_dir.mkdir()
        (skill_dir / "skill.json").write_text(json.dumps({
            "name": "test",
            "description": "from json",
            "steps": ["a"],
        }))
        (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: from md\n---\n# test\n## Steps\n1. x\n")
        s = load_skill(skill_dir)
        assert s is not None
        assert s.description == "from json"

    def test_falls_back_to_skill_md(self, tmp_path: Path):
        skill_dir = tmp_path / "test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: from md\n---\n# test\n## Steps\n1. x\n")
        s = load_skill(skill_dir)
        assert s is not None
        assert s.description == "from md"

    def test_returns_none_for_empty_dir(self, tmp_path: Path):
        skill_dir = tmp_path / "empty"
        skill_dir.mkdir()
        assert load_skill(skill_dir) is None

    def test_returns_none_for_nonexistent_dir(self, tmp_path: Path):
        assert load_skill(tmp_path / "nope") is None
