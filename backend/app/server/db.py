"""SQLite connection and schema setup for the local MVP database."""

import sqlite3
from collections.abc import Generator
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "reallocation.sqlite3"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect_db(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection with foreign keys enabled and rows accessible by name."""
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(path: Path = DB_PATH) -> None:
    """Create the database and missing tables on application startup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect_db(path)) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a connection for a future FastAPI route via Depends(get_db)."""
    connection = connect_db()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
