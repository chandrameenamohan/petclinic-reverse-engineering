"""Seed data for the visits service — 4 visits (Samantha pet_id=7, Max pet_id=8).

Call ``seed_database(session_factory)`` on application startup.
The function is idempotent: it checks for existing data before inserting.
"""

from __future__ import annotations

from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from visits_service.models import Visit

VISITS: list[dict[str, object]] = [
    {"id": 1, "pet_id": 7, "visit_date": date(2013, 1, 1), "description": "rabies shot"},
    {"id": 2, "pet_id": 8, "visit_date": date(2013, 1, 2), "description": "rabies shot"},
    {"id": 3, "pet_id": 8, "visit_date": date(2013, 1, 3), "description": "neutered"},
    {"id": 4, "pet_id": 7, "visit_date": date(2013, 1, 4), "description": "spayed"},
]


async def seed_database(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Seed the visits DB with 4 sample visits.

    Idempotent: skips seeding if visits already exist.
    """
    async with session_factory() as session:
        result = await session.execute(select(Visit.id).limit(1))
        if result.scalar() is not None:
            logger.info("Visits seed data already present — skipping.")
            return

        for data in VISITS:
            session.add(Visit(**data))

        await session.commit()
        logger.info("Visits seed data inserted: 4 visits.")
