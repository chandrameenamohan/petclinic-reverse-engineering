"""SQLAlchemy models for the customers service."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class PetType(Base):
    """Pet type entity — maps to the ``types`` table."""

    __tablename__ = "types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(80))

    pets: Mapped[list[Pet]] = relationship(back_populates="type")

    __table_args__ = (Index("types_name", "name"),)


class Owner(Base):
    """Owner entity — maps to the ``owners`` table."""

    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str | None] = mapped_column(String(30))
    last_name: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(80))
    telephone: Mapped[str | None] = mapped_column(String(12))

    pets: Mapped[list[Pet]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (Index("owners_last_name", "last_name"),)


class Pet(Base):
    """Pet entity — maps to the ``pets`` table."""

    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(30))
    birth_date: Mapped[date | None] = mapped_column(Date)
    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("types.id"), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("owners.id"), nullable=False)

    type: Mapped[PetType] = relationship(back_populates="pets", lazy="selectin")
    owner: Mapped[Owner] = relationship(back_populates="pets")

    __table_args__ = (Index("pets_name", "name"),)
