"""Student HTTP routes."""

import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..repositories.students import StudentRecord, create_student
from ..server.db import get_db


router = APIRouter(prefix="/students", tags=["students"])


class StudentCreateRequest(BaseModel):
    name: str = Field(max_length=100)
    required_seniority: Literal["SENIOR", "JUNIOR", "ANY"]

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("name must not be blank")
        return name


class StudentResponse(BaseModel):
    id: str
    name: str
    required_seniority: Literal["SENIOR", "JUNIOR", "ANY"]


@router.post("", response_model=StudentResponse, status_code=201)
def create_student_route(
    request: StudentCreateRequest,
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> StudentRecord:
    """Create and return a student."""
    try:
        return create_student(connection, request.model_dump())
    except (sqlite3.IntegrityError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
