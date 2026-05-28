from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sediman.agent.soul import load_soul, save_soul, reset_soul, DEFAULT_SOUL, SOUL_FILE


class TestLoadSoul:
    def test_returns_default_when_no_file(self, tmp_sediman_dir):
        with patch("sediman.agent.soul.SOUL_FILE", tmp_sediman_dir / "SOUL.md"):
            result = load_soul()
        assert result == DEFAULT_SOUL
        assert "Sediman" in result

    def test_loads_custom_soul(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        soul_file.write_text("You are a pirate agent. Arrr!")
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            result = load_soul()
        assert result == "You are a pirate agent. Arrr!"

    def test_loads_empty_soul_file(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        soul_file.write_text("")
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            result = load_soul()
        assert result == ""

    def test_loads_multiline_soul(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        soul_file.write_text("Line 1\nLine 2\nLine 3")
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            result = load_soul()
        assert "Line 1" in result
        assert "Line 3" in result

    def test_default_soul_contains_key_behaviors(self):
        assert "pragmatic" in DEFAULT_SOUL
        assert "concise" in DEFAULT_SOUL
        assert "browser" in DEFAULT_SOUL.lower()


class TestSaveSoul:
    def test_creates_soul_file(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            save_soul("New personality")
        assert soul_file.exists()
        assert soul_file.read_text() == "New personality"

    def test_overwrites_existing_soul(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        soul_file.write_text("Old personality")
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            save_soul("Updated personality")
        assert soul_file.read_text() == "Updated personality"

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        soul_file = nested / "SOUL.md"
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            save_soul("Nested soul")
        assert soul_file.exists()
        assert soul_file.read_text() == "Nested soul"

    def test_saves_empty_content(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            save_soul("")
        assert soul_file.exists()
        assert soul_file.read_text() == ""

    def test_saves_unicode_content(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            save_soul("You are a helpful agent. 你好世界 🤖")
        assert "你好世界" in soul_file.read_text()
        assert "🤖" in soul_file.read_text()

    def test_saves_very_long_content(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        long_content = "x" * 10000
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            save_soul(long_content)
        assert len(soul_file.read_text()) == 10000


class TestResetSoul:
    def test_deletes_existing_soul(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        soul_file.write_text("Custom soul")
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            reset_soul()
        assert not soul_file.exists()

    def test_no_error_when_no_file(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            reset_soul()  # Should not raise

    def test_reset_then_load_returns_default(self, tmp_sediman_dir):
        soul_file = tmp_sediman_dir / "SOUL.md"
        soul_file.write_text("Custom")
        with patch("sediman.agent.soul.SOUL_FILE", soul_file):
            reset_soul()
            result = load_soul()
        assert result == DEFAULT_SOUL
