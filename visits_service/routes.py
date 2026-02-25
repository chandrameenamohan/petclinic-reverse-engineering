"""REST API routes for the visits service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from visits_service.models import Visit
from visits_service.schemas import VisitCreateBody, VisitSchema, VisitsResponse


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Placeholder dependency — overridden by app startup via dependency_overrides."""
    raise RuntimeError("Database session not configured")
    yield  # noqa: RET504  # pragma: no cover


router = APIRouter(tags=["visits"])


@router.post(
    "/owners/{owner_id}/pets/{pet_id}/visits",
    response_model=VisitSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_visit(
    body: VisitCreateBody,
    pet_id: int = Path(ge=1),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Visit:
    """Create a visit for a pet. petId from path overrides body; date defaults to today."""
    visit = Visit(
        pet_id=pet_id,
        visit_date=body.date or date.today(),
        description=body.description,
    )
    db.add(visit)
    await db.flush()
    await db.refresh(visit)
    return visit


@router.get(
    "/owners/{owner_id}/pets/{pet_id}/visits",
    response_model=list[VisitSchema],
)
async def get_visits_for_pet(
    pet_id: int = Path(ge=1),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[Visit]:
    """List all visits for a single pet."""
    result = await db.execute(select(Visit).where(Visit.pet_id == pet_id))
    return list(result.scalars().all())


@router.get(
    "/pets/visits",
    response_model=VisitsResponse,
)
async def get_visits_for_pets(
    pet_id: str = Query(alias="petId"),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> VisitsResponse:
    """Batch query: GET /pets/visits?petId=7,8 — returns {items: [...]}."""
    pet_ids = [int(pid) for pid in pet_id.split(",")]
    result = await db.execute(select(Visit).where(Visit.pet_id.in_(pet_ids)))
    return VisitsResponse(items=list(result.scalars().all()))
