"""SQLAlchemy models for the visits service."""

from datetime import date as date_type

from sqlalchemy import Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class Visit(Base):
    """Visit entity — maps to the ``visits`` table.

    ``pet_id`` is a plain integer (no FK constraint) because pets live
    in the customers-service database.  An index on ``pet_id`` supports
    the batch-fetch query ``GET /pets/visits?petId=…``.
    """

    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(Integer, nullable=False)
    visit_date: Mapped[date_type | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(String(8192))

    __table_args__ = (Index("visits_pet_id", "pet_id"),)
