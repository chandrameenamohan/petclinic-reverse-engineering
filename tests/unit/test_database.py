"""Tests for shared.database — async SQLAlchemy engine, session, Base, get_db dependency."""

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base, create_engine, create_session_factory, get_db_dependency


# ---------------------------------------------------------------------------
# A throwaway model used only inside these tests
# ---------------------------------------------------------------------------
class _Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def engine() -> AsyncEngine:
    return create_engine("sqlite+aiosqlite:///:memory:")


@pytest.fixture()
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture()
async def _tables(engine: AsyncEngine) -> None:
    """Create all tables before the test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # type: ignore[misc]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Tests: create_engine
# ---------------------------------------------------------------------------
class TestCreateEngine:
    def test_returns_async_engine(self, engine: AsyncEngine) -> None:
        assert isinstance(engine, AsyncEngine)

    def test_engine_url_matches(self) -> None:
        eng = create_engine("sqlite+aiosqlite:///:memory:")
        assert str(eng.url) == "sqlite+aiosqlite:///:memory:"

    def test_echo_kwarg_forwarded(self) -> None:
        eng = create_engine("sqlite+aiosqlite:///:memory:", echo=True)
        assert eng.echo is True


# ---------------------------------------------------------------------------
# Tests: create_session_factory
# ---------------------------------------------------------------------------
class TestCreateSessionFactory:
    def test_returns_async_sessionmaker(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        assert isinstance(session_factory, async_sessionmaker)


# ---------------------------------------------------------------------------
# Tests: Base (DeclarativeBase)
# ---------------------------------------------------------------------------
class TestBase:
    def test_widget_table_in_metadata(self) -> None:
        assert "widgets" in Base.metadata.tables

    async def test_create_tables(self, engine: AsyncEngine) -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Verify we can round-trip a row
        sf = create_session_factory(engine)
        async with sf() as session:
            session.add(_Widget(name="sprocket"))
            await session.commit()

        async with sf() as session:
            result = await session.get(_Widget, 1)
            assert result is not None
            assert result.name == "sprocket"


# ---------------------------------------------------------------------------
# Tests: get_db_dependency
# ---------------------------------------------------------------------------
class TestGetDbDependency:
    async def test_yields_async_session(
        self, session_factory: async_sessionmaker[AsyncSession], _tables: None
    ) -> None:
        get_db = get_db_dependency(session_factory)
        gen = get_db()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
        # clean up the generator
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    async def test_commits_on_success(
        self, session_factory: async_sessionmaker[AsyncSession], _tables: None
    ) -> None:
        get_db = get_db_dependency(session_factory)

        async for session in get_db():
            session.add(_Widget(name="auto-commit"))

        # Verify the row was committed
        async with session_factory() as verify_session:
            widget = await verify_session.get(_Widget, 1)
            assert widget is not None
            assert widget.name == "auto-commit"

    async def test_rolls_back_on_exception(
        self, session_factory: async_sessionmaker[AsyncSession], _tables: None
    ) -> None:
        get_db = get_db_dependency(session_factory)

        with pytest.raises(RuntimeError, match="boom"):
            async for session in get_db():
                session.add(_Widget(name="should-rollback"))
                raise RuntimeError("boom")

        # Verify the row was NOT committed
        async with session_factory() as verify_session:
            widget = await verify_session.get(_Widget, 1)
            assert widget is None
