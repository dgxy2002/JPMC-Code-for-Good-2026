"""Database adapter for the therapist reallocation rules."""

import json
import sqlite3
from dataclasses import dataclass

from .reallocate import reallocate_therapist
from .repositories.sessions import get_session, update_session
from .repositories.therapists import add_unavailability_period


REALLOCATABLE_SESSION_STATUSES = ("SCHEDULED", "NEEDS_REPLACEMENT", "REALLOCATED")


@dataclass
class SessionRecord:
    id: str
    student_id: str
    original_therapist_id: str
    assigned_therapist_id: str | None
    date: str
    slot: str
    session_type: str
    status: str


@dataclass(frozen=True)
class StudentRecord:
    id: str
    required_seniority: str


@dataclass(frozen=True)
class TherapistRecord:
    id: str
    seniority: str
    unavailability: tuple[dict, ...]


def _session_from_row(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord(**dict(row))


def _therapist_from_row(row: sqlite3.Row) -> TherapistRecord:
    return TherapistRecord(
        id=row["id"],
        seniority=row["seniority"],
        unavailability=tuple(json.loads(row["unavailability"])),
    )


def _is_unavailable(therapist: TherapistRecord, date: str) -> bool:
    """Return whether an ISO date falls in any inclusive unavailable period."""
    return any(
        isinstance(period, dict)
        and isinstance(period.get("start"), str)
        and isinstance(period.get("end"), str)
        and period["start"] <= date <= period["end"]
        for period in therapist.unavailability
    )


def reallocate_session(
    connection: sqlite3.Connection, session_id: str
) -> SessionRecord | None:
    """Reallocate one session and persist the resulting assignment and status.

    ``None`` is returned when the session does not exist. Calling this for a
    session that no longer needs replacement is safe and leaves it unchanged.
    """
    row = connection.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if row is None:
        return None

    session = _session_from_row(row)
    if session.status != "NEEDS_REPLACEMENT":
        return session

    student_row = connection.execute(
        "SELECT id, required_seniority FROM students WHERE id = ?",
        (session.student_id,),
    ).fetchone()
    # The foreign key guarantees this for valid database state.
    if student_row is None:
        raise ValueError(f"Student {session.student_id!r} does not exist")
    student = StudentRecord(**dict(student_row))

    therapists = [
        _therapist_from_row(therapist_row)
        for therapist_row in connection.execute(
            "SELECT id, seniority, unavailability FROM therapists ORDER BY id"
        )
    ]
    therapists_by_id = {therapist.id: therapist for therapist in therapists}

    student_team = {
        team_row["therapist_id"]
        for team_row in connection.execute(
            """
            SELECT therapist_id
            FROM student_therapists
            WHERE student_id = ? AND relationship = 'TEAM'
            """,
            (student.id,),
        )
    }
    past_sessions = [
        _session_from_row(past_row)
        for past_row in connection.execute(
            """
            SELECT *
            FROM sessions
            WHERE student_id = ? AND status = 'COMPLETED' AND id != ?
            ORDER BY date DESC, id
            """,
            (student.id, session.id),
        )
    ]

    def is_available(therapist_id: str, date: str, slot: str) -> bool:
        therapist = therapists_by_id[therapist_id]
        if _is_unavailable(therapist, date):
            return False

        conflict = connection.execute(
            """
            SELECT 1
            FROM sessions
            WHERE id != ?
              AND date = ?
              AND slot = ?
              AND status IN (?, ?, ?)
              AND COALESCE(assigned_therapist_id, original_therapist_id) = ?
            LIMIT 1
            """,
            (session.id, date, slot, *REALLOCATABLE_SESSION_STATUSES, therapist_id),
        ).fetchone()
        return conflict is None

    reallocate_therapist(
        session,
        student,
        therapists,
        student_team,
        past_sessions,
        is_available,
    )
    connection.execute(
        """
        UPDATE sessions
        SET assigned_therapist_id = ?, status = ?
        WHERE id = ?
        """,
        (session.assigned_therapist_id, session.status, session.id),
    )
    return session


def session_reallocate(
    connection: sqlite3.Connection,
    session_id: str,
    therapist_id: str,
    slot: str,
    reason: str | None = None,
) -> SessionRecord | None:
    """Record a therapist's unavailable day and reallocate affected sessions.

    The target session supplies the date. Because therapist unavailability is
    date-based, every reallocatable session assigned to that therapist on the date is
    reallocated, including sessions in the other slot.
    """
    target = get_session(connection, session_id)
    if target is None:
        return None
    if target["slot"] != slot:
        raise ValueError("Slot does not match the session")
    current_therapist_id = (
        target["assigned_therapist_id"] or target["original_therapist_id"]
    )
    if current_therapist_id != therapist_id:
        raise ValueError("Therapist is not assigned to this session")
    if target["status"] not in REALLOCATABLE_SESSION_STATUSES:
        raise ValueError("This session cannot be reallocated")

    affected_ids = [
        row["id"]
        for row in connection.execute(
            """SELECT id FROM sessions
            WHERE date = ?
              AND status IN (?, ?, ?)
              AND COALESCE(assigned_therapist_id, original_therapist_id) = ?
            ORDER BY slot, id""",
            (target["date"], *REALLOCATABLE_SESSION_STATUSES, therapist_id),
        )
    ]
    add_unavailability_period(
        connection,
        therapist_id,
        {
            "start": target["date"],
            "end": target["date"],
            **({"reason": reason} if reason is not None else {}),
        },
    )
    for affected_id in affected_ids:
        update_session(connection, affected_id, {"status": "NEEDS_REPLACEMENT"})

    result = None
    for affected_id in affected_ids:
        reallocated = reallocate_session(connection, affected_id)
        if affected_id == session_id:
            result = reallocated
    return result
