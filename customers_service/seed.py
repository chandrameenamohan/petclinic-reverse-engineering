"""Seed data for the customers service — 6 pet types, 10 owners, 13 pets.

Call ``seed_database(session_factory)`` on application startup.
The function is idempotent: it checks for existing data before inserting.
"""

from __future__ import annotations

from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from customers_service.models import Owner, Pet, PetType

PET_TYPES: list[dict[str, object]] = [
    {"id": 1, "name": "cat"},
    {"id": 2, "name": "dog"},
    {"id": 3, "name": "lizard"},
    {"id": 4, "name": "snake"},
    {"id": 5, "name": "bird"},
    {"id": 6, "name": "hamster"},
]

OWNERS: list[dict[str, object]] = [
    {
        "id": 1, "first_name": "George", "last_name": "Franklin",
        "address": "110 W. Liberty St.", "city": "Madison", "telephone": "6085551023",
    },
    {
        "id": 2, "first_name": "Betty", "last_name": "Davis",
        "address": "638 Cardinal Ave.", "city": "Sun Prairie", "telephone": "6085551749",
    },
    {
        "id": 3, "first_name": "Eduardo", "last_name": "Rodriquez",
        "address": "2693 Commerce St.", "city": "McFarland", "telephone": "6085558763",
    },
    {
        "id": 4, "first_name": "Harold", "last_name": "Davis",
        "address": "563 Friendly St.", "city": "Windsor", "telephone": "6085553198",
    },
    {
        "id": 5, "first_name": "Peter", "last_name": "McTavish",
        "address": "2387 S. Fair Way", "city": "Madison", "telephone": "6085552765",
    },
    {
        "id": 6, "first_name": "Jean", "last_name": "Coleman",
        "address": "105 N. Lake St.", "city": "Monona", "telephone": "6085552654",
    },
    {
        "id": 7, "first_name": "Jeff", "last_name": "Black",
        "address": "1450 Oak Blvd.", "city": "Monona", "telephone": "6085555387",
    },
    {
        "id": 8, "first_name": "Maria", "last_name": "Escobito",
        "address": "345 Maple St.", "city": "Madison", "telephone": "6085557683",
    },
    {
        "id": 9, "first_name": "David", "last_name": "Schroeder",
        "address": "2749 Blackhawk Trail", "city": "Madison", "telephone": "6085559435",
    },
    {
        "id": 10, "first_name": "Carlos", "last_name": "Estaban",
        "address": "2335 Independence La.", "city": "Waunakee", "telephone": "6085555487",
    },
]

PETS: list[dict[str, object]] = [
    {"id": 1, "name": "Leo", "birth_date": date(2010, 9, 7), "type_id": 1, "owner_id": 1},
    {"id": 2, "name": "Basil", "birth_date": date(2012, 8, 6), "type_id": 6, "owner_id": 2},
    {"id": 3, "name": "Rosy", "birth_date": date(2011, 4, 17), "type_id": 2, "owner_id": 3},
    {"id": 4, "name": "Jewel", "birth_date": date(2010, 3, 7), "type_id": 2, "owner_id": 3},
    {"id": 5, "name": "Iggy", "birth_date": date(2010, 11, 30), "type_id": 3, "owner_id": 4},
    {"id": 6, "name": "George", "birth_date": date(2010, 1, 20), "type_id": 4, "owner_id": 5},
    {"id": 7, "name": "Samantha", "birth_date": date(2012, 9, 4), "type_id": 1, "owner_id": 6},
    {"id": 8, "name": "Max", "birth_date": date(2012, 9, 4), "type_id": 1, "owner_id": 6},
    {"id": 9, "name": "Lucky", "birth_date": date(2011, 8, 6), "type_id": 5, "owner_id": 7},
    {"id": 10, "name": "Mulligan", "birth_date": date(2007, 2, 24), "type_id": 2, "owner_id": 8},
    {"id": 11, "name": "Freddy", "birth_date": date(2010, 3, 9), "type_id": 5, "owner_id": 9},
    {"id": 12, "name": "Lucky", "birth_date": date(2010, 6, 24), "type_id": 2, "owner_id": 10},
    {"id": 13, "name": "Sly", "birth_date": date(2012, 6, 8), "type_id": 1, "owner_id": 10},
]


async def seed_database(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Seed the customers DB with pet types, owners, and pets.

    Idempotent: skips seeding if pet types already exist.
    """
    async with session_factory() as session:
        result = await session.execute(select(PetType.id).limit(1))
        if result.scalar() is not None:
            logger.info("Customers seed data already present — skipping.")
            return

        for data in PET_TYPES:
            session.add(PetType(**data))
        await session.flush()

        for data in OWNERS:
            session.add(Owner(**data))
        await session.flush()

        for data in PETS:
            session.add(Pet(**data))

        await session.commit()
        logger.info("Customers seed data inserted: 6 pet types, 10 owners, 13 pets.")
