"""Load the dummy JSON data into an empty local SQLite database."""

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "backend" / "app" / "server" / "schema.sql"
DEFAULT_DB_PATH = ROOT / "backend" / "data" / "reallocation.sqlite3"

TABLE_COLUMNS = {
    "therapists": ("id", "name", "seniority", "employment_type", "unavailability"),
    "students": ("id", "name", "required_seniority"),
    "student_therapists": ("id", "student_id", "therapist_id", "relationship"),
    "sessions": (
        "id",
        "student_id",
        "original_therapist_id",
        "assigned_therapist_id",
        "date",
        "slot",
        "session_type",
        "status",
    ),
}


def _check_date(value: object) -> None:
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError(f"Invalid YYYY-MM-DD date: {value!r}")


def _load_rows(table: str) -> list[dict]:
    path = DATA_DIR / f"{table}.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    allowed = set(TABLE_COLUMNS[table])
    required = allowed - ({"unavailability"} if table == "therapists" else set())
    for number, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or required - row.keys() or row.keys() - allowed:
            raise ValueError(f"{path.name} row {number} has missing or unknown fields")
        try:
            UUID(row["id"])
            if table == "sessions":
                _check_date(row["date"])
            if table == "therapists" and "unavailability" in row:
                periods = row["unavailability"]
                if not isinstance(periods, list):
                    raise ValueError("unavailability must be an array")
                for period in periods:
                    if not isinstance(period, dict) or set(period) != {"start", "end"}:
                        raise ValueError("unavailability periods need start and end")
                    _check_date(period["start"])
                    _check_date(period["end"])
                    if period["start"] > period["end"]:
                        raise ValueError("unavailability end precedes start")
        except (TypeError, ValueError, KeyError) as error:
            raise ValueError(f"{path.name} row {number}: {error}") from error
    return rows


def populate(db_path: Path) -> dict[str, int]:
    """Create missing tables and insert all four JSON files as one transaction."""
    data = {table: _load_rows(table) for table in TABLE_COLUMNS}
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        existing = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLE_COLUMNS
        }
        if any(existing.values()):
            raise ValueError(
                f"Database already has data {existing}; use an empty database"
            )

        with connection:
            for table, rows in data.items():
                for number, row in enumerate(rows, start=1):
                    columns = [column for column in TABLE_COLUMNS[table] if column in row]
                    placeholders = ", ".join("?" for _ in columns)
                    values = [
                        json.dumps(row[column]) if column == "unavailability" else row[column]
                        for column in columns
                    ]
                    try:
                        connection.execute(
                            f"INSERT INTO {table} ({', '.join(columns)}) "
                            f"VALUES ({placeholders})",
                            values,
                        )
                    except sqlite3.Error as error:
                        raise ValueError(
                            f"{table}.json row {number}: {error}"
                        ) from error
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Foreign key check failed")
    return {table: len(rows) for table, rows in data.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite file to populate (default: {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args()
    try:
        counts = populate(args.db.expanduser().resolve())
    except (ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Population failed: {error}\n")
    print(f"Populated {args.db} with " + ", ".join(
        f"{count} {table}" for table, count in counts.items()
    ))


if __name__ == "__main__":
    main()
