"""CRUD operations for therapists. The caller owns the SQLite transaction."""

import json
import sqlite3
from datetime import date
from typing import TypedDict, cast
from uuid import uuid4


class _UnavailabilityPeriodRequired(TypedDict):
    start: str
    end: str


class UnavailabilityPeriod(_UnavailabilityPeriodRequired, total=False):
    reason: str


class TherapistFields(TypedDict):
    name: str
    seniority: str
    employment_type: str


class TherapistCreate(TherapistFields, total=False):
    unavailability: list[UnavailabilityPeriod]


class TherapistRecord(TherapistFields):
    id: str
    unavailability: list[UnavailabilityPeriod]


class TherapistUpdate(TypedDict, total=False):
    name: str
    seniority: str
    employment_type: str
    unavailability: list[UnavailabilityPeriod]


THERAPIST_COLUMNS = ("name", "seniority", "employment_type", "unavailability")


def _validate_period(period: UnavailabilityPeriod) -> None:
    try:
        start = date.fromisoformat(period["start"])
        end = date.fromisoformat(period["end"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("unavailability periods need YYYY-MM-DD start and end dates") from error
    if start.isoformat() != period["start"] or end.isoformat() != period["end"] or end < start:
        raise ValueError("unavailability periods need valid start and end dates")
    reason = period.get("reason")
    if reason is not None and (not isinstance(reason, str) or not 1 <= len(reason) <= 200):
        raise ValueError("reason must be a non-empty string of at most 200 characters")


def _encode_periods(periods: list[UnavailabilityPeriod]) -> str:
    for period in periods:
        _validate_period(period)
    return json.dumps(periods)


def _row_to_record(row: sqlite3.Row) -> TherapistRecord:
    record = dict(row)
    record["unavailability"] = json.loads(record["unavailability"])
    return cast(TherapistRecord, record)


def create_therapist(db: sqlite3.Connection, data: TherapistCreate) -> TherapistRecord:
    """Insert a therapist with a generated UUID."""
    therapist_id = str(uuid4())
    db.execute(
        """INSERT INTO therapists (id, name, seniority, employment_type, unavailability)
        VALUES (?, ?, ?, ?, ?)""",
        (
            therapist_id,
            data["name"],
            data["seniority"],
            data["employment_type"],
            _encode_periods(data.get("unavailability", [])),
        ),
    )
    created = get_therapist(db, therapist_id)
    assert created is not None
    return created


def get_therapist(db: sqlite3.Connection, therapist_id: str) -> TherapistRecord | None:
    row = db.execute("SELECT * FROM therapists WHERE id = ?", (therapist_id,)).fetchone()
    return _row_to_record(row) if row is not None else None


def list_therapists(
    db: sqlite3.Connection, *, limit: int = 100, offset: int = 0
) -> list[TherapistRecord]:
    if not 1 <= limit <= 1000 or offset < 0:
        raise ValueError("limit must be 1–1000 and offset must be non-negative")
    rows = db.execute(
        "SELECT * FROM therapists ORDER BY name, id LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def find_therapists_by_name(db: sqlite3.Connection, name: str) -> list[dict[str, str]]:
    """Return IDs and names for an exact, case-insensitive name match."""
    rows = db.execute(
        "SELECT id, name FROM therapists WHERE name = ? COLLATE NOCASE ORDER BY id",
        (name,),
    ).fetchall()
    return [dict(row) for row in rows]


def update_therapist(
    db: sqlite3.Connection, therapist_id: str, changes: TherapistUpdate
) -> TherapistRecord | None:
    unknown = changes.keys() - THERAPIST_COLUMNS
    if unknown:
        raise ValueError(f"Unknown therapist fields: {', '.join(sorted(unknown))}")
    if not changes:
        return get_therapist(db, therapist_id)
    values = dict(changes)
    if "unavailability" in values:
        values["unavailability"] = _encode_periods(values["unavailability"])
    assignments = ", ".join(f"{column} = ?" for column in values)
    cursor = db.execute(
        f"UPDATE therapists SET {assignments} WHERE id = ?",
        (*values.values(), therapist_id),
    )
    return get_therapist(db, therapist_id) if cursor.rowcount else None


def delete_therapist(db: sqlite3.Connection, therapist_id: str) -> bool:
    """Delete an unreferenced therapist; SQLite rejects referenced therapists."""
    cursor = db.execute("DELETE FROM therapists WHERE id = ?", (therapist_id,))
    return cursor.rowcount > 0


def add_unavailability_period(
    db: sqlite3.Connection, therapist_id: str, period: UnavailabilityPeriod
) -> TherapistRecord | None:
    """Append a period unless the therapist is already unavailable throughout it."""
    _validate_period(period)
    therapist = get_therapist(db, therapist_id)
    if therapist is None:
        return None
    covered = any(
        isinstance(existing, dict)
        and isinstance(existing.get("start"), str)
        and isinstance(existing.get("end"), str)
        and existing["start"] <= period["start"]
        and existing["end"] >= period["end"]
        for existing in therapist["unavailability"]
    )
    if covered and "reason" not in period:
        return therapist
    if covered:
        for existing in therapist["unavailability"]:
            if (
                isinstance(existing, dict)
                and existing.get("start") == period["start"]
                and existing.get("end") == period["end"]
            ):
                existing["reason"] = period["reason"]
                return update_therapist(
                    db, therapist_id, {"unavailability": therapist["unavailability"]}
                )
    periods = [*therapist["unavailability"], period]
    return update_therapist(db, therapist_id, {"unavailability": periods})
