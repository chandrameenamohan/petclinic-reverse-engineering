"""Pydantic schemas for the customers service."""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator


class PetTypeSchema(BaseModel):
    """Response schema for pet types."""

    id: int
    name: str | None = None

    model_config = {"from_attributes": True}


class PetSchema(BaseModel):
    """Response schema for pets (nested inside OwnerSchema)."""

    id: int
    name: str | None = None
    birth_date: date | None = Field(None, alias="birthDate")
    type: PetTypeSchema | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class OwnerSchema(BaseModel):
    """Response schema for owners with nested pets."""

    id: int
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    address: str
    city: str
    telephone: str
    pets: list[PetSchema] = []

    model_config = {"from_attributes": True, "populate_by_name": True}


class OwnerCreateRequest(BaseModel):
    """Request schema for creating/updating owners."""

    first_name: str = Field(..., min_length=1, alias="firstName")
    last_name: str = Field(..., min_length=1, alias="lastName")
    address: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    telephone: str = Field(..., min_length=1)

    @field_validator("telephone")
    @classmethod
    def telephone_must_be_digits(cls, v: str) -> str:
        """Validate telephone is 1-12 digits only."""
        if not re.match(r"^\d{1,12}$", v):
            raise ValueError("Telephone must be 1-12 digits")
        return v

    model_config = {"populate_by_name": True}


class PetCreateRequest(BaseModel):
    """Request schema for creating/updating pets."""

    id: int | None = None
    name: str | None = None
    birth_date: date | None = Field(None, alias="birthDate")
    type_id: int = Field(..., alias="typeId")

    model_config = {"populate_by_name": True}


class PetDetailsSchema(BaseModel):
    """Response schema for GET /owners/*/pets/{petId} — includes owner as denormalized string."""

    id: int
    name: str | None = None
    owner: str  # "firstName lastName" concatenated
    birth_date: date | None = Field(None, alias="birthDate")
    type: PetTypeSchema | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}
