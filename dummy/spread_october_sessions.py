"""Spread seeded sessions across October 2026 and complete past sessions.

Run after populating the database. The update is transactional and safe to rerun.
"""

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "backend/data/reallocation.sqlite3"
SEED_FILE = ROOT / "dummy/sessions.json"
FEATURED_THERAPIST_ID = "810bdd70-e4a4-5e78-a754-536119e1a21f"
FEATURED_THERAPIST_DATES = ("2026-10-07", "2026-10-21")


def allow_completed_status(connection: sqlite3.Connection) -> None:
    """Upgrade older local databases whose sessions CHECK omits COMPLETED."""
    schema_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
    ).fetchone()
    if schema_row is None:
        raise ValueError("Database has no sessions table")
    if "COMPLETED" in schema_row["sql"]:
        return

    connection.execute("""
        CREATE TABLE sessions_october_upgrade (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL REFERENCES students(id),
            original_therapist_id TEXT NOT NULL REFERENCES therapists(id),
            assigned_therapist_id TEXT REFERENCES therapists(id),
            date TEXT NOT NULL CHECK (
                length(date) = 10 AND
                date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            ),
            slot TEXT NOT NULL CHECK (slot IN ('AM', 'PM')),
            session_type TEXT NOT NULL CHECK (session_type IN ('CLINIC', 'HOME', 'SCHOOL')),
            status TEXT NOT NULL CHECK (
                status IN ('SCHEDULED', 'NEEDS_REPLACEMENT', 'REALLOCATED',
                           'CANCELLED', 'COMPLETED')
            )
        )
    """)
    connection.execute("""
        INSERT INTO sessions_october_upgrade
        SELECT id, student_id, original_therapist_id, assigned_therapist_id,
               date, slot, session_type, status FROM sessions
    """)
    connection.execute("DROP TABLE sessions")
    connection.execute("ALTER TABLE sessions_october_upgrade RENAME TO sessions")
    connection.execute("CREATE INDEX idx_sessions_date_slot ON sessions(date, slot)")
    connection.execute(
        "CREATE INDEX idx_sessions_assigned_date_slot "
        "ON sessions(assigned_therapist_id, date, slot)"
    )


def planned_dates(seed_sessions: list[dict]) -> dict[str, str]:
    """Place one session on every day, then fill selected later days."""
    featured = [
        session
        for session in seed_sessions
        if session["original_therapist_id"] == FEATURED_THERAPIST_ID
    ]
    if len(featured) != 2:
        raise ValueError(
            f"Expected two featured therapist sessions, found {len(featured)}"
        )

    plan = {
        session["id"]: day
        for session, day in zip(featured, FEATURED_THERAPIST_DATES)
    }
    others = [
        session
        for session in seed_sessions
        if session["original_therapist_id"] != FEATURED_THERAPIST_ID
    ]
    if len(others) != 45:
        raise ValueError(f"Expected 45 other seed sessions, found {len(others)}")
    for index, session in enumerate(others):
        day = index + 1 if index < 31 else index - 31 + 16
        plan[session["id"]] = f"2026-10-{day:02d}"
    if len(plan) != len(seed_sessions):
        raise ValueError("Duplicate session IDs in seed data")
    return plan


def spread(db_path: Path, as_of: date) -> tuple[int, int]:
    if not db_path.is_file():
        raise ValueError(f"Database does not exist: {db_path}")
    seed_sessions = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    plan = planned_dates(seed_sessions)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            therapist = connection.execute(
                "SELECT name FROM therapists WHERE id = ?", (FEATURED_THERAPIST_ID,)
            ).fetchone()
            if therapist is None or therapist["name"] != "Therapist 02":
                raise ValueError("Featured therapist ID is missing or has changed")

            ids = set(plan)
            rows = connection.execute(
                "SELECT id, student_id, original_therapist_id, assigned_therapist_id, "
                "date, slot, status FROM sessions"
            ).fetchall()
            by_id = {row["id"]: row for row in rows}
            if not ids <= by_id.keys():
                raise ValueError(f"Missing {len(ids - by_id.keys())} seed sessions in database")

            seed_by_id = {session["id"]: session for session in seed_sessions}
            for session_id in ids:
                row = by_id[session_id]
                if (
                    row["student_id"] != seed_by_id[session_id]["student_id"]
                    or row["original_therapist_id"] != seed_by_id[session_id]["original_therapist_id"]
                    or row["status"] not in (
                        ("SCHEDULED", "COMPLETED", "REALLOCATED")
                        if row["original_therapist_id"] == FEATURED_THERAPIST_ID
                        else ("SCHEDULED", "COMPLETED")
                    )
                    or (
                        row["status"] == "REALLOCATED"
                        and row["date"] != "2026-10-19"
                    )
                ):
                    raise ValueError(f"Session {session_id} differs from the expected seed record")

            # Check the final schedule before changing any rows.
            occupied_therapists = set()
            occupied_students = set()
            for row in rows:
                session_id = row["id"]
                session_date = plan.get(session_id, row["date"])
                assigned = (
                    FEATURED_THERAPIST_ID
                    if session_id in ids
                    and row["original_therapist_id"] == FEATURED_THERAPIST_ID
                    else row["assigned_therapist_id"]
                )
                if row["status"] == "CANCELLED":
                    continue
                student_key = (session_date, row["slot"], row["student_id"])
                therapist_key = (session_date, row["slot"], assigned)
                if student_key in occupied_students or (
                    assigned is not None and therapist_key in occupied_therapists
                ):
                    raise ValueError(f"Schedule conflict involving session {session_id}")
                occupied_students.add(student_key)
                if assigned is not None:
                    occupied_therapists.add(therapist_key)

            allow_completed_status(connection)
            completed = 0
            for session_id, session_date in plan.items():
                status = "COMPLETED" if date.fromisoformat(session_date) < as_of else "SCHEDULED"
                completed += status == "COMPLETED"
                assigned = (
                    FEATURED_THERAPIST_ID
                    if by_id[session_id]["original_therapist_id"]
                    == FEATURED_THERAPIST_ID
                    else by_id[session_id]["assigned_therapist_id"]
                )
                connection.execute(
                    "UPDATE sessions SET date = ?, status = ?, assigned_therapist_id = ? "
                    "WHERE id = ?",
                    (session_date, status, assigned, session_id),
                )
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Foreign key check failed")
    return len(plan), completed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--as-of", type=date.fromisoformat, default=date.today(),
        help="Date used to mark earlier sessions completed (default: today)",
    )
    args = parser.parse_args()
    try:
        total, completed = spread(args.db.expanduser().resolve(), args.as_of)
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(1, f"Schedule update failed: {error}\n")
    print(f"Spread {total} sessions across October 2026; {completed} completed before {args.as_of}")


if __name__ == "__main__":
    main()
