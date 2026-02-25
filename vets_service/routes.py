"""REST API routes for the vets service — single GET /vets endpoint with TTL cache."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from cachetools import TTLCache
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vets_service.models import Vet
from vets_service.schemas import VetSchema


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Placeholder dependency — overridden by app startup via dependency_overrides."""
    raise RuntimeError("Database session not configured")
    yield  # noqa: RET504  # pragma: no cover


router = APIRouter(tags=["vets"])

# Cache vets list for 1 hour (equivalent to @Cacheable("vets") in Spring)
vets_cache: TTLCache[str, list[VetSchema]] = TTLCache(maxsize=1, ttl=3600)

_CACHE_KEY = "vets"


@router.get("/vets", response_model=list[VetSchema])
async def list_vets(db: AsyncSession = Depends(get_db)) -> list[VetSchema]:  # noqa: B008
    """Return all vets with specialties sorted alphabetically. Results are cached for 1 hour."""
    cached = vets_cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Vet).options(selectinload(Vet.specialties))
    )
    vets = list(result.scalars().all())

    # Sort each vet's specialties alphabetically by name
    schemas = []
    for vet in vets:
        vet.specialties = sorted(vet.specialties, key=lambda s: (s.name or ""))
        schemas.append(VetSchema.model_validate(vet))

    vets_cache[_CACHE_KEY] = schemas
    return schemas
