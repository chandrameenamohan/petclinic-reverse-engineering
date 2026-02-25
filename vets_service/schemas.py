"""Pydantic schemas for the vets service."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class SpecialtySchema(BaseModel):
    """Response schema for vet specialties."""

    id: int
    name: str | None = None

    model_config = {"from_attributes": True}


class VetSchema(BaseModel):
    """Response schema for vets with nested specialties."""

    id: int
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    specialties: list[SpecialtySchema] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def nrOfSpecialties(self) -> int:  # noqa: N802
        """Number of specialties — matches Spring Petclinic JSON contract."""
        return len(self.specialties)

    model_config = {"from_attributes": True, "populate_by_name": True}
