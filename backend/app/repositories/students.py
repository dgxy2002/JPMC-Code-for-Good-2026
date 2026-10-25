"""Database operations for students. The caller owns the transaction."""

import sqlite3
from typing import Literal, TypedDict, cast
from uuid import uuid4


RequiredSeniority = Literal["SENIOR", "JUNIOR", "ANY"]


class StudentCreate(TypedDict):
    name: str
    required_seniority: RequiredSeniority


class StudentRecord(StudentCreate):
    id: str


def _row_to_record(row: sqlite3.Row) -> StudentRecord:
    return cast(StudentRecord, dict(row))


def create_student(db: sqlite3.Connection, data: StudentCreate) -> StudentRecord:
    """Insert a student with a generated UUID and return the stored record."""
    name = data["name"].strip()
    if not 1 <= len(name) <= 100:
        raise ValueError("name must contain between 1 and 100 characters")
    if data["required_seniority"] not in {"SENIOR", "JUNIOR", "ANY"}:
        raise ValueError("required_seniority must be SENIOR, JUNIOR, or ANY")

    student_id = str(uuid4())
    db.execute(
        """
        INSERT INTO students (id, name, required_seniority)
        VALUES (?, ?, ?)
        """,
        (student_id, name, data["required_seniority"]),
    )
    created = get_student(db, student_id)
    assert created is not None
    return created


def get_student(db: sqlite3.Connection, student_id: str) -> StudentRecord | None:
    """Return one student, or ``None`` when the ID does not exist."""
    row = db.execute(
        "SELECT id, name, required_seniority FROM students WHERE id = ?",
        (student_id,),
    ).fetchone()
    return _row_to_record(row) if row is not None else None
