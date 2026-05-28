from __future__ import annotations

from unittest.mock import patch

import pytest

from sediman.memory.prompt import load_memory, save_memory, get_memory_size


class TestLoadMemory:
    def test_returns_empty_when_no_files(self, tmp_sediman_dir):
        assert load_memory() == ""

    def test_loads_memory_file(self, tmp_sediman_dir):
        mem_dir = tmp_sediman_dir / "memories"
        mem_dir.mkdir(parents=True, exist_ok=True)
        mem_file = mem_dir / "MEMORY.md"
        mem_file.write_text("some memory")
        assert "some memory" in load_memory()

    def test_loads_both_files(self, tmp_sediman_dir):
        mem_dir = tmp_sediman_dir / "memories"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "MEMORY.md").write_text("memory content")
        (mem_dir / "USER.md").write_text("user content")
        result = load_memory()
        assert "memory content" in result
        assert "user content" in result


class TestSaveMemory:
    def test_creates_memory_file(self, tmp_sediman_dir):
        save_memory("new fact")
        mem_file = tmp_sediman_dir / "memories" / "MEMORY.md"
        assert mem_file.exists()
        assert "new fact" in mem_file.read_text()

    def test_appends_to_existing(self, tmp_sediman_dir):
        mem_dir = tmp_sediman_dir / "memories"
        mem_dir.mkdir(parents=True, exist_ok=True)
        mem_file = mem_dir / "MEMORY.md"
        mem_file.write_text("existing")
        save_memory("added")
        content = mem_file.read_text()
        assert "existing" in content
        assert "added" in content

    def test_truncates_at_max_bytes(self, tmp_sediman_dir):
        save_memory("x" * 2000)
        mem_file = tmp_sediman_dir / "memories" / "MEMORY.md"
        assert mem_file.exists()
        assert len(mem_file.read_text().encode()) <= 2200

    def test_creates_parent_directory(self, tmp_path):
        mem_dir = tmp_path / "nested" / "memories"
        mem_file = mem_dir / "MEMORY.md"
        with patch("sediman.memory.store.MEMORY_DIR", mem_dir), \
             patch("sediman.memory.store.MEMORY_FILE", mem_file):
            save_memory("hello")
        assert mem_file.exists()


class TestGetMemorySize:
    def test_zero_when_no_file(self, tmp_sediman_dir):
        assert get_memory_size() == 0

    def test_returns_byte_length(self, tmp_sediman_dir):
        mem_dir = tmp_sediman_dir / "memories"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "MEMORY.md").write_text("hello")
        assert get_memory_size() == 5
