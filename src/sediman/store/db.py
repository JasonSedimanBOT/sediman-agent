from __future__ import annotations

import aiosqlite
import structlog
from contextlib import asynccontextmanager
from pathlib import Path

logger = structlog.get_logger()

DEFAULT_DATA_DIR = Path.home() / ".sediman"
DB_NAME = "state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    steps_json TEXT NOT NULL DEFAULT '[]',
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    action TEXT NOT NULL,
    observation TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    id, task, result,
    content=sessions,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(rowid, id, task, result)
    VALUES (new.rowid, new.id, new.task, new.result);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, id, task, result)
    VALUES ('delete', old.rowid, old.id, old.task, old.result);
END;

CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, id, task, result)
    VALUES ('delete', old.rowid, old.id, old.task, old.result);
    INSERT INTO sessions_fts(rowid, id, task, result)
    VALUES (new.rowid, new.id, new.task, new.result);
END;
"""


def get_db_path() -> Path:
    return DEFAULT_DATA_DIR / DB_NAME


async def init_db() -> None:
    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("database_initialized", path=str(db_path))


@asynccontextmanager
async def get_connection() -> aiosqlite.Connection:
    """Yield a database connection that is automatically closed."""
    db_path = get_db_path()
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()
