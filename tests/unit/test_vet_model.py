"""Tests for Vet, Specialty, and vet_specialties SQLAlchemy models — vets_service.models."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shared.database import Base, create_engine, create_session_factory
from vets_service.models import Specialty, Vet, vet_specialties


@pytest.fixture()
def engine() -> AsyncEngine:
    return create_engine("sqlite+aiosqlite:///:memory:")


@pytest.fixture()
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture()
async def tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # type: ignore[misc]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Vet model schema tests
# ---------------------------------------------------------------------------


class TestVetSchema:
    """Verify the Vet model maps to the 'vets' table with correct columns."""

    def test_tablename_is_vets(self) -> None:
        assert Vet.__tablename__ == "vets"

    def test_has_id_column(self) -> None:
        mapper = inspect(Vet)
        assert "id" in mapper.columns

    def test_id_is_primary_key(self) -> None:
        mapper = inspect(Vet)
        pk_cols = [c.name for c in mapper.columns if c.primary_key]
        assert "id" in pk_cols

    def test_has_first_name_column(self) -> None:
        mapper = inspect(Vet)
        assert "first_name" in mapper.columns

    def test_first_name_max_length_30(self) -> None:
        mapper = inspect(Vet)
        col = mapper.columns["first_name"]
        assert col.type.length == 30

    def test_has_last_name_column(self) -> None:
        mapper = inspect(Vet)
        assert "last_name" in mapper.columns

    def test_last_name_max_length_30(self) -> None:
        mapper = inspect(Vet)
        col = mapper.columns["last_name"]
        assert col.type.length == 30

    def test_index_on_last_name(self) -> None:
        indexes = Vet.__table__.indexes
        ln_indexes = [idx for idx in indexes if "last_name" in [c.name for c in idx.columns]]
        assert len(ln_indexes) >= 1
        assert ln_indexes[0].name == "vets_last_name"

    def test_inherits_from_base(self) -> None:
        assert issubclass(Vet, Base)


# ---------------------------------------------------------------------------
# Specialty model schema tests
# ---------------------------------------------------------------------------


class TestSpecialtySchema:
    """Verify the Specialty model maps to the 'specialties' table with correct columns."""

    def test_tablename_is_specialties(self) -> None:
        assert Specialty.__tablename__ == "specialties"

    def test_has_id_column(self) -> None:
        mapper = inspect(Specialty)
        assert "id" in mapper.columns

    def test_id_is_primary_key(self) -> None:
        mapper = inspect(Specialty)
        pk_cols = [c.name for c in mapper.columns if c.primary_key]
        assert "id" in pk_cols

    def test_has_name_column(self) -> None:
        mapper = inspect(Specialty)
        assert "name" in mapper.columns

    def test_name_max_length_80(self) -> None:
        mapper = inspect(Specialty)
        col = mapper.columns["name"]
        assert col.type.length == 80

    def test_name_is_nullable(self) -> None:
        mapper = inspect(Specialty)
        col = mapper.columns["name"]
        assert col.nullable is True

    def test_index_on_name(self) -> None:
        indexes = Specialty.__table__.indexes
        name_indexes = [idx for idx in indexes if "name" in [c.name for c in idx.columns]]
        assert len(name_indexes) >= 1
        assert name_indexes[0].name == "specialties_name"

    def test_inherits_from_base(self) -> None:
        assert issubclass(Specialty, Base)


# ---------------------------------------------------------------------------
# vet_specialties join table tests
# ---------------------------------------------------------------------------


class TestVetSpecialtiesTable:
    """Verify the vet_specialties join table has correct structure."""

    def test_table_name(self) -> None:
        assert vet_specialties.name == "vet_specialties"

    def test_has_vet_id_column(self) -> None:
        col_names = [c.name for c in vet_specialties.columns]
        assert "vet_id" in col_names

    def test_has_specialty_id_column(self) -> None:
        col_names = [c.name for c in vet_specialties.columns]
        assert "specialty_id" in col_names

    def test_vet_id_is_not_nullable(self) -> None:
        col = vet_specialties.c.vet_id
        assert col.nullable is False

    def test_specialty_id_is_not_nullable(self) -> None:
        col = vet_specialties.c.specialty_id
        assert col.nullable is False

    def test_vet_id_has_fk_to_vets(self) -> None:
        fks = vet_specialties.c.vet_id.foreign_keys
        fk_targets = [fk.target_fullname for fk in fks]
        assert "vets.id" in fk_targets

    def test_specialty_id_has_fk_to_specialties(self) -> None:
        fks = vet_specialties.c.specialty_id.foreign_keys
        fk_targets = [fk.target_fullname for fk in fks]
        assert "specialties.id" in fk_targets

    def test_unique_constraint_on_vet_specialty_pair(self) -> None:
        from sqlalchemy import UniqueConstraint

        unique_constraints = [
            c for c in vet_specialties.constraints
            if isinstance(c, UniqueConstraint)
        ]
        assert len(unique_constraints) >= 1
        uc = unique_constraints[0]
        assert {col.name for col in uc.columns} == {"vet_id", "specialty_id"}


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestVetCRUD:
    """Verify Vet rows can be created, read, and persisted."""

    async def test_insert_and_read(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            vet = Vet(first_name="James", last_name="Carter")
            session.add(vet)
            await session.commit()
            assert vet.id is not None

        async with session_factory() as session:
            loaded = await session.get(Vet, vet.id)
            assert loaded is not None
            assert loaded.first_name == "James"
            assert loaded.last_name == "Carter"

    async def test_autoincrement_ids(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            v1 = Vet(first_name="James", last_name="Carter")
            v2 = Vet(first_name="Helen", last_name="Leary")
            session.add_all([v1, v2])
            await session.commit()
            assert v1.id is not None
            assert v2.id is not None
            assert v2.id > v1.id


class TestSpecialtyCRUD:
    """Verify Specialty rows can be created, read, and persisted."""

    async def test_insert_and_read(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            spec = Specialty(name="radiology")
            session.add(spec)
            await session.commit()
            assert spec.id is not None

        async with session_factory() as session:
            loaded = await session.get(Specialty, spec.id)
            assert loaded is not None
            assert loaded.name == "radiology"

    async def test_insert_with_null_name(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            spec = Specialty(name=None)
            session.add(spec)
            await session.commit()
            assert spec.id is not None

        async with session_factory() as session:
            loaded = await session.get(Specialty, spec.id)
            assert loaded is not None
            assert loaded.name is None


class TestVetSpecialtyRelationship:
    """Verify M:N relationship between Vet and Specialty via vet_specialties."""

    async def test_vet_with_specialties(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            s1 = Specialty(name="surgery")
            s2 = Specialty(name="dentistry")
            vet = Vet(first_name="Linda", last_name="Douglas")
            vet.specialties = [s1, s2]
            session.add(vet)
            await session.commit()
            vet_id = vet.id

        async with session_factory() as session:
            loaded = await session.get(Vet, vet_id)
            assert loaded is not None
            spec_names = sorted([s.name for s in loaded.specialties])
            assert spec_names == ["dentistry", "surgery"]

    async def test_vet_without_specialties(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            vet = Vet(first_name="James", last_name="Carter")
            session.add(vet)
            await session.commit()
            vet_id = vet.id

        async with session_factory() as session:
            loaded = await session.get(Vet, vet_id)
            assert loaded is not None
            assert loaded.specialties == []

    async def test_unique_constraint_prevents_duplicate_link(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Inserting the same (vet_id, specialty_id) twice should raise IntegrityError."""
        from sqlalchemy import insert
        from sqlalchemy.exc import IntegrityError

        async with session_factory() as session:
            vet = Vet(first_name="Helen", last_name="Leary")
            spec = Specialty(name="radiology")
            session.add_all([vet, spec])
            await session.commit()
            vet_id = vet.id
            spec_id = spec.id

        async with session_factory() as session:
            await session.execute(
                insert(vet_specialties).values(vet_id=vet_id, specialty_id=spec_id)
            )
            await session.commit()

        with pytest.raises(IntegrityError):
            async with session_factory() as session:
                await session.execute(
                    insert(vet_specialties).values(vet_id=vet_id, specialty_id=spec_id)
                )
                await session.commit()

    async def test_specialty_shared_across_vets(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            radiology = Specialty(name="radiology")
            session.add(radiology)
            await session.commit()
            spec_id = radiology.id

        async with session_factory() as session:
            spec = await session.get(Specialty, spec_id)
            v1 = Vet(first_name="Helen", last_name="Leary")
            v1.specialties = [spec]  # type: ignore[list-item]
            v2 = Vet(first_name="Henry", last_name="Stevens")
            v2.specialties = [spec]  # type: ignore[list-item]
            session.add_all([v1, v2])
            await session.commit()
            v1_id, v2_id = v1.id, v2.id

        async with session_factory() as session:
            loaded1 = await session.get(Vet, v1_id)
            loaded2 = await session.get(Vet, v2_id)
            assert loaded1 is not None
            assert loaded2 is not None
            assert len(loaded1.specialties) == 1
            assert len(loaded2.specialties) == 1
            assert loaded1.specialties[0].name == "radiology"
            assert loaded2.specialties[0].name == "radiology"
