"""Pydantic schemas for the visits service."""

from __future__ import annotations

from datetime import date as date_type

from pydantic import BaseModel, Field


class VisitSchema(BaseModel):
    """Response schema for visits — JSON keys: id, date, description, petId."""

    id: int
    pet_id: int = Field(..., alias="petId")
    visit_date: date_type = Field(..., alias="date")
    description: str | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class VisitCreateBody(BaseModel):
    """Request body for POST /owners/*/pets/{petId}/visits.

    petId comes from the path, not the body. date defaults to today.
    """

    date: date_type | None = None
    description: str | None = Field(None, max_length=8192)


class VisitCreateRequest(BaseModel):
    """Request schema for creating visits (includes petId for programmatic use)."""

    date: date_type | None = None
    description: str | None = Field(None, max_length=8192)
    pet_id: int = Field(..., alias="petId")

    model_config = {"populate_by_name": True}


class VisitsResponse(BaseModel):
    """Wrapper for batch visit queries — GET /pets/visits?petId=1,2,3."""

    items: list[VisitSchema] = []
