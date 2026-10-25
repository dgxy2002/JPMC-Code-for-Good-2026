"""Session HTTP routes."""

import sqlite3
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..reallocation_service import SessionRecord, session_reallocate
from ..repositories.sessions import (
    ScheduleSessionRecord,
    create_session,
    list_schedule_sessions,
)
from ..server.db import get_db

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreateRequest(BaseModel):
    student_id: str
    therapist_id: str
    date: date
    slot: Literal["AM", "PM"]


class SessionReallocateRequest(BaseModel):
    therapist_id: str
    slot: Literal["AM", "PM"]
    reason: str | None = Field(default=None, min_length=1, max_length=200)


class SessionResponse(BaseModel):
    id: str
    student_id: str
    original_therapist_id: str
    assigned_therapist_id: str | None
    date: str
    slot: str
    session_type: str
    status: str


class ScheduleSessionResponse(SessionResponse):
    student_name: str
    therapist_id: str | None
    therapist_name: str | None
    therapist_seniority: str | None


@router.get("", response_model=list[ScheduleSessionResponse])
def list_schedule_sessions_route(
    start_date: date,
    end_date: date,
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> list[ScheduleSessionRecord]:
    """List sessions for an inclusive date range, with calendar display names."""
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    return list_schedule_sessions(connection, start_date.isoformat(), end_date.isoformat())


@router.post("", response_model=SessionResponse, status_code=201)
def create_session_route(
    request: SessionCreateRequest,
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict:
    """Create a scheduled clinic session for a student and therapist."""
    try:
        return create_session(
            connection,
            {
                "student_id": request.student_id,
                "original_therapist_id": request.therapist_id,
                "assigned_therapist_id": None,
                "date": request.date.isoformat(),
                "slot": request.slot,
                "session_type": "CLINIC",
                "status": "SCHEDULED",
            },
        )
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=422, detail="Student or therapist does not exist"
        ) from error


@router.post("/{session_id}/reallocate", response_model=SessionResponse)
def session_reallocate_route(
    session_id: str,
    request: SessionReallocateRequest,
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> SessionRecord:
    """Mark the therapist unavailable and reallocate sessions on that date."""
    try:
        session = session_reallocate(
            connection, session_id, request.therapist_id, request.slot, request.reason
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
