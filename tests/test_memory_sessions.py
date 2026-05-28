from __future__ import annotations

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


@pytest.mark.asyncio
async def test_save_session_returns_id(db):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        sid = await save_session(task="test task", steps=[], result="done")
    assert len(sid) == 12


@pytest.mark.asyncio
async def test_save_and_retrieve_session(db):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        await save_session(task="browse github", steps=[], result="found repo")
        sessions = await get_recent_sessions()
    assert len(sessions) == 1
    assert sessions[0]["task"] == "browse github"
    assert sessions[0]["result"] == "found repo"


@pytest.mark.asyncio
async def test_get_recent_sessions_ordered(db):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        await save_session(task="first", steps=[], result="r1")
        await save_session(task="second", steps=[], result="r2")
        sessions = await get_recent_sessions()
    assert len(sessions) == 2
    assert sessions[0]["task"] == "second"


@pytest.mark.asyncio
async def test_get_recent_sessions_limit(db):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        for i in range(15):
            await save_session(task=f"task {i}", steps=[], result="r")
        sessions = await get_recent_sessions(limit=5)
    assert len(sessions) == 5


@pytest.mark.asyncio
async def test_save_session_with_steps(db):
    steps = [
        {"action": "click", "observation": "button clicked"},
        {"action": "type", "observation": "text entered"},
    ]
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        await save_session(task="form fill", steps=steps, result="submitted")
        sessions = await get_recent_sessions()
    assert len(sessions) == 1
    assert sessions[0]["task"] == "form fill"


@pytest.mark.asyncio
async def test_search_sessions(db):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        await save_session(task="search for python tutorials", steps=[], result="found")
        await save_session(task="check weather", steps=[], result="sunny")
        results = await search_sessions("python")
    assert len(results) == 1
    assert "python" in results[0]["task"]


@pytest.mark.asyncio
async def test_search_sessions_no_match(db):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        await save_session(task="hello world", steps=[], result="done")
        results = await search_sessions("nonexistent")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_get_recent_sessions_empty(db):
    with patch("sediman.store.db.DEFAULT_DATA_DIR", db):
        sessions = await get_recent_sessions()
    assert sessions == []
