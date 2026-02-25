"""SQLAlchemy models for the vets service."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base

vet_specialties = Table(
    "vet_specialties",
    Base.metadata,
    Column("vet_id", Integer, ForeignKey("vets.id"), nullable=False),
    Column("specialty_id", Integer, ForeignKey("specialties.id"), nullable=False),
    UniqueConstraint("vet_id", "specialty_id"),
)


class Specialty(Base):
    """Specialty entity — maps to the ``specialties`` table."""

    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(80))

    __table_args__ = (Index("specialties_name", "name"),)


class Vet(Base):
    """Vet entity — maps to the ``vets`` table."""

    __tablename__ = "vets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str | None] = mapped_column(String(30))
    last_name: Mapped[str | None] = mapped_column(String(30))

    specialties: Mapped[list[Specialty]] = relationship(
        secondary=vet_specialties,
        lazy="selectin",
    )

    __table_args__ = (Index("vets_last_name", "last_name"),)
