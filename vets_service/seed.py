"""Seed data for the vets service — 6 vets, 3 specialties, 5 vet-specialty links.

Call ``seed_database(session_factory)`` on application startup.
The function is idempotent: it checks for existing data before inserting.
"""

from __future__ import annotations

from loguru import logger
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vets_service.models import Specialty, Vet, vet_specialties

VETS: list[dict[str, object]] = [
    {"id": 1, "first_name": "James", "last_name": "Carter"},
    {"id": 2, "first_name": "Helen", "last_name": "Leary"},
    {"id": 3, "first_name": "Linda", "last_name": "Douglas"},
    {"id": 4, "first_name": "Rafael", "last_name": "Ortega"},
    {"id": 5, "first_name": "Henry", "last_name": "Stevens"},
    {"id": 6, "first_name": "Sharon", "last_name": "Jenkins"},
]

SPECIALTIES: list[dict[str, object]] = [
    {"id": 1, "name": "radiology"},
    {"id": 2, "name": "surgery"},
    {"id": 3, "name": "dentistry"},
]

VET_SPECIALTIES: list[dict[str, int]] = [
    {"vet_id": 2, "specialty_id": 1},  # Helen Leary — radiology
    {"vet_id": 3, "specialty_id": 2},  # Linda Douglas — surgery
    {"vet_id": 3, "specialty_id": 3},  # Linda Douglas — dentistry
    {"vet_id": 4, "specialty_id": 2},  # Rafael Ortega — surgery
    {"vet_id": 5, "specialty_id": 1},  # Henry Stevens — radiology
]


async def seed_database(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Seed the vets DB with vets, specialties, and associations.

    Idempotent: skips seeding if vets already exist.
    """
    async with session_factory() as session:
        result = await session.execute(select(Vet.id).limit(1))
        if result.scalar() is not None:
            logger.info("Vets seed data already present — skipping.")
            return

        for data in SPECIALTIES:
            session.add(Specialty(**data))
        await session.flush()

        for data in VETS:
            session.add(Vet(**data))
        await session.flush()

        for link in VET_SPECIALTIES:
            await session.execute(insert(vet_specialties).values(**link))

        await session.commit()
        logger.info("Vets seed data inserted: 6 vets, 3 specialties, 5 links.")
