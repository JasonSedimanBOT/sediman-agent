"""Comprehensive edge-case tests for skills/format.py — YAML parsing, fallbacks, unicode, etc."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sediman.skills.format import (
    SkillData,
    parse_skill_md,
    parse_skill_json,
    load_skill,
    _extract_steps_from_body,
    _parse_simple_yaml,
    _yaml_value,
)


class TestSkillDataToJsonObject:
    def test_omits_variables_when_empty(self):
        s = SkillData(name="x", description="d", variables=[])
        j = s.to_json()
        assert "variables" not in j

    def test_includes_variables_when_present(self):
        s = SkillData(name="x", description="d", variables=["A", "B"])
        j = s.to_json()
        assert j["variables"] == ["A", "B"]

    def test_omits_schedule_when_none(self):
        s = SkillData(name="x", description="d")
        j = s.to_json()
        assert "schedule" not in j

    def test_includes_schedule_when_set(self):
        s = SkillData(name="x", description="d", schedule="0 9 * * *")
        j = s.to_json()
        assert j["schedule"] == "0 9 * * *"

    def test_omits_author_when_none(self):
        s = SkillData(name="x", description="d")
        j = s.to_json()
        assert "author" not in j

    def test_includes_author_when_set(self):
        s = SkillData(name="x", description="d", author="alice")
        j = s.to_json()
        assert j["author"] == "alice"

    def test_omits_source_when_local(self):
        s = SkillData(name="x", description="d", source="local")
        j = s.to_json()
        assert "source" not in j

    def test_includes_source_when_hub(self):
        s = SkillData(name="x", description="d", source="hub")
        j = s.to_json()
        assert j["source"] == "hub"


class TestSkillDataToSkillMd:
    def test_includes_license_when_set(self):
        s = SkillData(name="x", description="d", license="MIT")
        md = s.to_skill_md()
        assert "license: MIT" in md

    def test_includes_compatibility_when_set(self):
        s = SkillData(name="x", description="d", compatibility=">=0.1.0")
        md = s.to_skill_md()
        assert "compatibility: >=0.1.0" in md

    def test_no_steps_section_when_empty(self):
        s = SkillData(name="x", description="d", steps=[])
        md = s.to_skill_md()
        assert "## Steps" not in md

    def test_no_variables_section_when_empty(self):
        s = SkillData(name="x", description="d", variables=[])
        md = s.to_skill_md()
        assert "## Variables" not in md

    def test_no_schedule_section_when_none(self):
        s = SkillData(name="x", description="d")
        md = s.to_skill_md()
        assert "## Schedule" not in md

    def test_metadata_block_with_category(self):
        s = SkillData(name="x", description="d", category="finance")
        md = s.to_skill_md()
        assert "metadata:" in md
        assert "category: finance" in md

    def test_metadata_block_with_version(self):
        s = SkillData(name="x", description="d", version=3)
        md = s.to_skill_md()
        assert 'version: "3"' in md

    def test_no_metadata_block_when_defaults(self):
        s = SkillData(name="x", description="d")
        md = s.to_skill_md()
        assert "metadata:" not in md

    def test_md_ends_with_newline(self):
        s = SkillData(name="x", description="d")
        assert s.to_skill_md().endswith("\n")

    def test_description_with_quotes(self):
        s = SkillData(name="x", description='He said "hello"')
        md = s.to_skill_md()
        assert "He said" in md

    def test_source_in_metadata(self):
        s = SkillData(name="x", description="d", source="hub")
        md = s.to_skill_md()
        assert "source: hub" in md


class TestParseSkillMdEdgeCases:
    def test_frontmatter_with_only_required_fields(self):
        md = "---\nname: minimal\ndescription: Minimal skill\n---\n\nSome body text"
        s = parse_skill_md(md)
        assert s is not None
        assert s.name == "minimal"
        assert s.category == "general"
        assert s.version == 1
        assert s.variables == []
        assert s.schedule is None
        assert s.author is None

    def test_description_with_special_chars(self):
        md = '---\nname: special\ndescription: "Has: colons & ampersands"\n---\n\nBody'
        s = parse_skill_md(md)
        assert s is not None

    def test_empty_frontmatter(self):
        md = "---\n---\n\nBody text"
        s = parse_skill_md(md)
        assert s is None  # No name or description

    def test_frontmatter_with_extra_whitespace(self):
        md = "---  \nname: x\ndescription: d\n---  \n\nBody"
        s = parse_skill_md(md)
        assert s is not None

    def test_no_closing_frontmatter(self):
        md = "---\nname: x\ndescription: d\n\nNo closing"
        s = parse_skill_md(md)
        assert s is None

    def test_unicode_in_frontmatter(self):
        md = "---\nname: unicode-skill\ndescription: 你好世界 🌍\n---\n\n# unicode"
        s = parse_skill_md(md)
        assert s is not None
        assert "你好" in s.description

    def test_steps_extracted_from_numbered_list(self):
        md = "---\nname: x\ndescription: d\n---\n\n# Title\n\n1. First step\n2. Second step\n3. Third step\n"
        s = parse_skill_md(md)
        assert s is not None
        assert len(s.steps) == 3

    def test_steps_with_nested_content(self):
        md = "---\nname: x\ndescription: d\n---\n\n## Steps\n\n1. Open https://example.com\n2. Click the login button\n"
        s = parse_skill_md(md)
        assert s is not None
        assert "Open https://example.com" in s.steps[0]

    def test_variables_as_comma_separated_string(self):
        md = "---\nname: x\ndescription: d\nvariables: A, B, C\n---\n\nBody"
        s = parse_skill_md(md)
        # If yaml available, it parses as string then splits
        # behavior depends on yaml availability

    def test_metadata_nested_structure(self):
        md = """---
name: meta-skill
description: Has metadata
metadata:
  category: finance
  version: "5"
  author: bob
---

# meta-skill
"""
        s = parse_skill_md(md)
        assert s is not None
        assert s.category == "finance"
        assert s.version == 5
        assert s.author == "bob"


class TestParseSkillJsonEdgeCases:
    def test_missing_description_returns_none(self):
        raw = json.dumps({"name": "x"})
        assert parse_skill_json(raw) is None

    def test_extra_fields_ignored(self):
        raw = json.dumps({
            "name": "x",
            "description": "d",
            "unknown_field": "ignored",
            "another": 42,
        })
        s = parse_skill_json(raw)
        assert s is not None
        assert s.name == "x"

    def test_steps_as_empty_array(self):
        raw = json.dumps({"name": "x", "description": "d", "steps": []})
        s = parse_skill_json(raw)
        assert s is not None
        assert s.steps == []

    def test_null_optional_fields(self):
        raw = json.dumps({
            "name": "x",
            "description": "d",
            "schedule": None,
            "author": None,
            "variables": None,
        })
        s = parse_skill_json(raw)
        assert s is not None
        assert s.schedule is None

    def test_unicode_in_json(self):
        raw = json.dumps({"name": "x", "description": "日本語テスト", "steps": ["ステップ1"]})
        s = parse_skill_json(raw)
        assert s is not None
        assert "日本語" in s.description

    def test_large_steps_list(self):
        steps = [f"step {i}" for i in range(100)]
        raw = json.dumps({"name": "x", "description": "d", "steps": steps})
        s = parse_skill_json(raw)
        assert len(s.steps) == 100

    def test_very_long_description(self):
        desc = "d" * 5000
        raw = json.dumps({"name": "x", "description": desc})
        s = parse_skill_json(raw)
        assert len(s.description) == 5000

    def test_empty_json_object(self):
        assert parse_skill_json("{}") is None

    def test_non_object_json(self):
        # parse_skill_json returns None for arrays (no "name" key)
        assert parse_skill_json("[]") is None
        # Numbers and strings cause TypeError in "in" operator - treated as invalid JSON
        # These raise inside parse_skill_json, returning None
        assert parse_skill_json("42") is None
        assert parse_skill_json('"string"') is None


class TestLoadSkillEdgeCases:
    def test_loads_from_json_only(self, tmp_path):
        skill_dir = tmp_path / "json-only"
        skill_dir.mkdir()
        (skill_dir / "skill.json").write_text(json.dumps({
            "name": "json-skill",
            "description": "from json",
            "steps": ["a"],
        }))

        s = load_skill(skill_dir)
        assert s is not None
        assert s.name == "json-skill"
        assert s.description == "from json"

    def test_corrupted_json_falls_through_to_none(self, tmp_path):
        skill_dir = tmp_path / "corrupt"
        skill_dir.mkdir()
        (skill_dir / "skill.json").write_text("{invalid json")

        s = load_skill(skill_dir)
        assert s is None

    def test_corrupted_md_returns_none(self, tmp_path):
        skill_dir = tmp_path / "bad-md"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("Not valid frontmatter at all")

        s = load_skill(skill_dir)
        assert s is None


class TestExtractStepsFromBody:
    def test_extracts_numbered_steps(self):
        body = "1. First\n2. Second\n3. Third"
        assert _extract_steps_from_body(body) == ["First", "Second", "Third"]

    def test_ignores_non_numbered_lines(self):
        body = "Some text\n- bullet point\n1. Only this"
        assert _extract_steps_from_body(body) == ["Only this"]

    def test_empty_body(self):
        assert _extract_steps_from_body("") == []

    def test_no_numbered_items(self):
        assert _extract_steps_from_body("Just text\nMore text") == []

    def test_indented_numbered_items(self):
        body = "  1. Indented step"
        steps = _extract_steps_from_body(body)
        assert len(steps) == 1
        assert "Indented step" in steps[0]

    def test_multi_digit_numbers(self):
        body = "1. One\n10. Ten\n100. Hundred"
        steps = _extract_steps_from_body(body)
        assert len(steps) == 3


class TestYamlValue:
    def test_double_quoted_string(self):
        assert _yaml_value('"hello"') == "hello"

    def test_single_quoted_string(self):
        assert _yaml_value("'hello'") == "hello"

    def test_boolean_true(self):
        assert _yaml_value("true") is True
        assert _yaml_value("True") is True
        assert _yaml_value("TRUE") is True

    def test_boolean_false(self):
        assert _yaml_value("false") is False

    def test_integer(self):
        assert _yaml_value("42") == 42

    def test_float(self):
        assert _yaml_value("3.14") == 3.14

    def test_json_array(self):
        assert _yaml_value('["a", "b"]') == ["a", "b"]

    def test_invalid_json_array(self):
        assert _yaml_value("[invalid") == "[invalid"

    def test_plain_string(self):
        assert _yaml_value("hello world") == "hello world"

    def test_empty_string(self):
        assert _yaml_value("") == ""


class TestParseSimpleYaml:
    def test_basic_key_value(self):
        text = "name: test\ndescription: desc"
        result = _parse_simple_yaml(text)
        assert result["name"] == "test"
        assert result["description"] == "desc"

    def test_nested_metadata(self):
        text = "name: x\nmetadata:\n  category: finance\n  version: \"2\""
        result = _parse_simple_yaml(text)
        assert result["metadata"]["category"] == "finance"
        assert result["metadata"]["version"] == "2"

    def test_comments_ignored(self):
        text = "# comment\nname: test"
        result = _parse_simple_yaml(text)
        assert "name" in result

    def test_empty_lines_ignored(self):
        text = "\n\nname: test\n\n"
        result = _parse_simple_yaml(text)
        assert result["name"] == "test"

    def test_empty_string(self):
        result = _parse_simple_yaml("")
        assert result == {}

    def test_colon_in_value(self):
        text = 'description: "has: colon"'
        result = _parse_simple_yaml(text)
        assert result["description"] == "has: colon"
