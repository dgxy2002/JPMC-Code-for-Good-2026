"""Build a SQLite database populated with the mock reallocation fixture."""

import sqlite3
from pathlib import Path


TESTING_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = TESTING_DIR.parent / "app" / "server" / "schema.sql"
MOCK_DATA_PATH = TESTING_DIR / "mock_data.sql"
DEFAULT_DB_PATH = TESTING_DIR / "mock_reallocation.sqlite3"


def create_mock_database(
    path: str | Path = ":memory:", *, replace: bool = False
) -> sqlite3.Connection:
    """Create, populate, and return a mock database connection."""
    if path != ":memory:":
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if replace and path.exists():
            path.unlink()

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.executescript(MOCK_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        connection.close()
        raise
    return connection


if __name__ == "__main__":
    database = create_mock_database(DEFAULT_DB_PATH, replace=True)
    database.close()
    print(f"Created mock database at {DEFAULT_DB_PATH}")
