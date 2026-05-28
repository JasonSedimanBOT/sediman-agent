from __future__ import annotations

from unittest.mock import patch

import pytest

from sediman.store.db import init_db, get_db_path, get_connection


class TestGetDbPath:
    def test_returns_path_under_data_dir(self, tmp_sediman_dir):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", tmp_sediman_dir):
            path = get_db_path()
        assert path == tmp_sediman_dir / "state.db"


class TestInitDb:
    @pytest.mark.asyncio
    async def test_creates_database_file(self, tmp_sediman_dir):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", tmp_sediman_dir):
            await init_db()
        assert (tmp_sediman_dir / "state.db").exists()

    @pytest.mark.asyncio
    async def test_creates_data_directory(self, tmp_path):
        new_dir = tmp_path / "new_sediman"
        with patch("sediman.store.db.DEFAULT_DATA_DIR", new_dir):
            await init_db()
        assert new_dir.is_dir()

    @pytest.mark.asyncio
    async def test_idempotent(self, tmp_sediman_dir):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", tmp_sediman_dir):
            await init_db()
            await init_db()
        assert (tmp_sediman_dir / "state.db").exists()


class TestGetConnection:
    @pytest.mark.asyncio
    async def test_yields_connection(self, tmp_sediman_dir):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", tmp_sediman_dir):
            await init_db()
            async with get_connection() as conn:
                assert conn is not None

    @pytest.mark.asyncio
    async def test_connection_has_row_factory(self, tmp_sediman_dir):
        with patch("sediman.store.db.DEFAULT_DATA_DIR", tmp_sediman_dir):
            await init_db()
            async with get_connection() as conn:
                import aiosqlite
                assert conn.row_factory == aiosqlite.Row
