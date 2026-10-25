"""CRUD operations for sessions. The caller owns the SQLite transaction."""

import sqlite3
from datetime import date as calendar_date
from typing import TypedDict, cast
from uuid import uuid4


class SessionCreate(TypedDict):
    student_id: str
    original_therapist_id: str
    assigned_therapist_id: str | None
    date: str
    slot: str
    session_type: str
    status: str


class SessionRecord(SessionCreate):
    id: str


class ScheduleSessionRecord(SessionRecord):
    student_name: str
    therapist_id: str | None
    therapist_name: str | None
    therapist_seniority: str | None


class SessionUpdate(TypedDict, total=False):
    student_id: str
    original_therapist_id: str
    assigned_therapist_id: str | None
    date: str
    slot: str
    session_type: str
    status: str


SESSION_COLUMNS = (
    "student_id",
    "original_therapist_id",
    "assigned_therapist_id",
    "date",
    "slot",
    "session_type",
    "status",
)


def _validate_date(value: str) -> None:
    """Reject invalid dates and formats that SQLite's TEXT column cannot catch."""
    if not isinstance(value, str) or calendar_date.fromisoformat(value).isoformat() != value:
        raise ValueError("date must be a valid YYYY-MM-DD string")


def _row_to_record(row: sqlite3.Row) -> SessionRecord:
    return cast(SessionRecord, dict(row))


def create_session(db: sqlite3.Connection, data: SessionCreate) -> SessionRecord:
    """Insert a session with a generated UUID and return its stored row."""
    _validate_date(data["date"])
    session_id = str(uuid4())
    values = (session_id, *(data[column] for column in SESSION_COLUMNS))
    db.execute(
        """INSERT INTO sessions (
            id, student_id, original_therapist_id, assigned_therapist_id,
            date, slot, session_type, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        values,
    )
    created = get_session(db, session_id)
    assert created is not None
    return created


def get_session(db: sqlite3.Connection, session_id: str) -> SessionRecord | None:
    """Return one session, or None when the ID does not exist."""
    row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return _row_to_record(row) if row is not None else None


def list_sessions(
    db: sqlite3.Connection, *, limit: int = 100, offset: int = 0
) -> list[SessionRecord]:
    """Return sessions in date and slot order with simple pagination."""
    if not 1 <= limit <= 1000 or offset < 0:
        raise ValueError("limit must be 1–1000 and offset must be non-negative")
    rows = db.execute(
        "SELECT * FROM sessions ORDER BY date, slot, id LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_schedule_sessions(
    db: sqlite3.Connection, start_date: str, end_date: str
) -> list[ScheduleSessionRecord]:
    """Return sessions and display names in an inclusive date range."""
    rows = db.execute(
        """SELECT s.*, student.name AS student_name,
                  CASE WHEN s.status = 'CANCELLED' THEN NULL
                       ELSE COALESCE(s.assigned_therapist_id, s.original_therapist_id)
                  END AS therapist_id,
                  therapist.name AS therapist_name,
                  therapist.seniority AS therapist_seniority
           FROM sessions AS s
           JOIN students AS student ON student.id = s.student_id
           LEFT JOIN therapists AS therapist
             ON therapist.id = CASE WHEN s.status = 'CANCELLED' THEN NULL
                                  ELSE COALESCE(s.assigned_therapist_id, s.original_therapist_id)
                             END
           WHERE s.date BETWEEN ? AND ?
           ORDER BY s.date, s.slot, s.id""",
        (start_date, end_date),
    ).fetchall()
    return [cast(ScheduleSessionRecord, dict(row)) for row in rows]


def update_session(
    db: sqlite3.Connection, session_id: str, changes: SessionUpdate
) -> SessionRecord | None:
    """Apply selected fields; use None to clear assigned_therapist_id."""
    unknown = changes.keys() - SESSION_COLUMNS
    if unknown:
        raise ValueError(f"Unknown session fields: {', '.join(sorted(unknown))}")
    if not changes:
        return get_session(db, session_id)
    if "date" in changes:
        _validate_date(changes["date"])

    assignments = ", ".join(f"{column} = ?" for column in changes)
    cursor = db.execute(
        f"UPDATE sessions SET {assignments} WHERE id = ?",
        (*changes.values(), session_id),
    )
    return get_session(db, session_id) if cursor.rowcount else None


def delete_session(db: sqlite3.Connection, session_id: str) -> bool:
    """Delete a session and report whether a row existed."""
    cursor = db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return cursor.rowcount > 0
