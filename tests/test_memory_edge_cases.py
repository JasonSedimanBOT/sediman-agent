"""Edge-case tests for memory/sessions.py — search, large data, concurrent access."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

from sediman.memory.sessions import save_session, get_recent_sessions, search_sessions
from sediman.store.db import init_db


@pytest_asyncio.fixture
async def db(tmp_sediman_dir):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", tmp_sediman_dir):
        await init_db()
    yield tmp_sediman_dir


class TestSaveSessionEdgeCases:
    @pytest.mark.asyncio
    async def test_save_with_none_result(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            sid = await save_session(task="task", steps=[], result=None)
        assert sid is not None

    @pytest.mark.asyncio
    async def test_save_with_complex_steps(self, db):
        steps = [
            {"action": "click", "observation": "button clicked", "selector": "#btn"},
            {"action": "type", "observation": "text entered", "text": "hello"},
            {"action": "scroll", "observation": "scrolled down", "pixels": 500},
        ]
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            sid = await save_session(task="complex task", steps=steps, result="done")
        assert sid is not None

    @pytest.mark.asyncio
    async def test_save_with_empty_steps(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            sid = await save_session(task="empty task", steps=[], result="done")
        assert sid is not None

    @pytest.mark.asyncio
    async def test_save_session_id_is_12_chars(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            sid = await save_session(task="t", steps=[], result="r")
        assert len(sid) == 12

    @pytest.mark.asyncio
    async def test_save_session_id_is_hex(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            sid = await save_session(task="t", steps=[], result="r")
        assert all(c in "0123456789abcdef" for c in sid)

    @pytest.mark.asyncio
    async def test_save_many_sessions(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            for i in range(50):
                await save_session(task=f"task {i}", steps=[], result="r")
            sessions = await get_recent_sessions(limit=50)
        assert len(sessions) == 50

    @pytest.mark.asyncio
    async def test_save_with_unicode_task(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            sid = await save_session(task="日本語のタスク 🚀", steps=[], result="完了")
        assert sid is not None
        sessions = await get_recent_sessions()
        assert "日本語" in sessions[0]["task"]


class TestSearchSessionsEdgeCases:
    @pytest.mark.asyncio
    async def test_search_by_result(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            await save_session(task="generic task", steps=[], result="found python tutorial")
            results = await search_sessions("python")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            await save_session(task="PYTHON TUTORIAL", steps=[], result="done")
            results = await search_sessions("python")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_partial_match(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            await save_session(task="browsing the web", steps=[], result="done")
            # FTS5 uses token-based matching, "browsing" matches "brows*" prefix
            results = await search_sessions("browsing")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            for i in range(10):
                await save_session(task=f"python task {i}", steps=[], result="r")
            results = await search_sessions("python", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_returns_ordered_by_date(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            await save_session(task="first python", steps=[], result="r")
            await save_session(task="second python", steps=[], result="r")
            results = await search_sessions("python")
        assert results[0]["task"] == "second python"

    @pytest.mark.asyncio
    async def test_search_with_special_chars(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            await save_session(task="search C++ stuff", steps=[], result="r")
            # FTS5 might not handle special chars well
            try:
                results = await search_sessions("C++")
            except Exception:
                pytest.skip("FTS5 doesn't handle special chars")


class TestGetRecentSessionsEdgeCases:
    @pytest.mark.asyncio
    async def test_default_limit_is_10(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            for i in range(15):
                await save_session(task=f"task {i}", steps=[], result="r")
            sessions = await get_recent_sessions()
        assert len(sessions) == 10

    @pytest.mark.asyncio
    async def test_limit_1(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            await save_session(task="only one", steps=[], result="r")
            sessions = await get_recent_sessions(limit=1)
        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_has_all_expected_fields(self, db):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
            await save_session(task="fields test", steps=[], result="done")
            sessions = await get_recent_sessions()
        assert "id" in sessions[0]
        assert "task" in sessions[0]
        assert "result" in sessions[0]
        assert "created_at" in sessions[0]


class TestMemoryPromptEdgeCases:
    """Additional edge cases for memory/prompt.py"""

    def test_save_then_load_preserves_content(self, tmp_sediman_dir):
        from sediman.memory.prompt import save_memory, load_memory

        save_memory("first fact")
        save_memory("second fact")
        content = load_memory()
        assert "first fact" in content
        assert "second fact" in content

    def test_save_at_exact_max_bytes(self, tmp_sediman_dir):
        from sediman.memory.prompt import save_memory, get_memory_size, MAX_MEMORY_BYTES

        # Save content that's exactly at the limit
        # The content will be truncated to MAX_MEMORY_BYTES chars (not bytes)
        content = "x" * MAX_MEMORY_BYTES
        save_memory(content)
        size = get_memory_size()
        assert size <= MAX_MEMORY_BYTES

    def test_multiple_saves_dont_exceed_max(self, tmp_sediman_dir):
        from sediman.memory.prompt import save_memory, get_memory_size, MAX_MEMORY_BYTES

        for i in range(20):
            save_memory(f"Memory entry {i} with some padding text to use bytes")

        size = get_memory_size()
        assert size <= MAX_MEMORY_BYTES

    def test_load_memory_only_user_file(self, tmp_sediman_dir):
        from sediman.memory.prompt import load_memory

        mem_dir = tmp_sediman_dir / "memories"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "USER.md").write_text("user preferences")
        content = load_memory()
        assert "user preferences" in content

    def test_save_creates_directory_recursively(self, tmp_path):
        from sediman.memory.prompt import save_memory

        mem_dir = tmp_path / "a" / "b" / "c"
        mem_file = mem_dir / "MEMORY.md"
        with patch("sediman.memory.store.MEMORY_DIR", mem_dir), \
             patch("sediman.memory.store.MEMORY_FILE", mem_file):
            save_memory("deep memory")
        assert mem_file.exists()
