"""Therapist lookup used by the demo login."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..repositories.therapists import find_therapists_by_name
from ..server.db import get_db

router = APIRouter(prefix="/therapists", tags=["therapists"])


class TherapistLookupResponse(BaseModel):
    id: str
    name: str


@router.get("", response_model=list[TherapistLookupResponse])
def find_therapists_route(
    name: Annotated[str, Query(min_length=1)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> list[dict[str, str]]:
    return find_therapists_by_name(connection, name)
