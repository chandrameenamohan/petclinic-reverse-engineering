"""Unit tests for visits_service Pydantic schemas."""

from datetime import date

import pytest
from pydantic import ValidationError

from visits_service.schemas import (
    VisitCreateRequest,
    VisitSchema,
    VisitsResponse,
)

# ---------------------------------------------------------------------------
# VisitSchema
# ---------------------------------------------------------------------------


class TestVisitSchema:
    def test_from_dict_with_aliases(self) -> None:
        s = VisitSchema(id=1, petId=7, date="2013-01-01", description="rabies shot")  # type: ignore[call-arg]
        assert s.id == 1
        assert s.pet_id == 7
        assert s.visit_date == date(2013, 1, 1)
        assert s.description == "rabies shot"

    def test_from_dict_with_field_names(self) -> None:
        """populate_by_name allows using snake_case field names."""
        s = VisitSchema(id=1, pet_id=7, visit_date=date(2013, 1, 1), description="rabies shot")
        assert s.pet_id == 7
        assert s.visit_date == date(2013, 1, 1)

    def test_description_optional(self) -> None:
        s = VisitSchema(id=1, pet_id=7, visit_date=date(2013, 1, 1))
        assert s.description is None

    def test_serialization_uses_aliases(self) -> None:
        s = VisitSchema(id=1, pet_id=7, visit_date=date(2013, 1, 1), description="rabies shot")
        d = s.model_dump(by_alias=True)
        assert "petId" in d
        assert d["petId"] == 7
        assert "date" in d
        assert d["date"] == date(2013, 1, 1)

    def test_from_orm_object(self) -> None:
        """Verify from_attributes works with ORM-like objects."""

        class FakeVisit:
            id = 1
            pet_id = 7
            visit_date = date(2013, 1, 1)
            description = "rabies shot"

        s = VisitSchema.model_validate(FakeVisit(), from_attributes=True)
        assert s.id == 1
        assert s.pet_id == 7
        assert s.visit_date == date(2013, 1, 1)
        assert s.description == "rabies shot"

    def test_id_required(self) -> None:
        with pytest.raises(ValidationError):
            VisitSchema(pet_id=7, visit_date=date(2013, 1, 1))  # type: ignore[call-arg]

    def test_pet_id_required(self) -> None:
        with pytest.raises(ValidationError):
            VisitSchema(id=1, visit_date=date(2013, 1, 1))  # type: ignore[call-arg]

    def test_visit_date_required(self) -> None:
        with pytest.raises(ValidationError):
            VisitSchema(id=1, pet_id=7)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# VisitCreateRequest
# ---------------------------------------------------------------------------


class TestVisitCreateRequest:
    def test_valid_request_with_alias(self) -> None:
        r = VisitCreateRequest(petId=7, description="checkup")  # type: ignore[call-arg]
        assert r.pet_id == 7
        assert r.description == "checkup"
        assert r.date is None

    def test_valid_request_field_names(self) -> None:
        r = VisitCreateRequest(pet_id=7, date=date(2023, 1, 15), description="checkup")
        assert r.pet_id == 7
        assert r.date == date(2023, 1, 15)

    def test_date_optional_defaults_none(self) -> None:
        r = VisitCreateRequest(pet_id=7)
        assert r.date is None

    def test_description_optional_defaults_none(self) -> None:
        r = VisitCreateRequest(pet_id=7)
        assert r.description is None

    def test_description_max_length(self) -> None:
        """Description must not exceed 8192 characters."""
        r = VisitCreateRequest(pet_id=7, description="x" * 8192)
        assert len(r.description) == 8192  # type: ignore[arg-type]

    def test_description_too_long(self) -> None:
        with pytest.raises(ValidationError):
            VisitCreateRequest(pet_id=7, description="x" * 8193)

    def test_pet_id_required(self) -> None:
        with pytest.raises(ValidationError):
            VisitCreateRequest(description="checkup")  # type: ignore[call-arg]

    def test_serialization_uses_alias(self) -> None:
        r = VisitCreateRequest(pet_id=7, date=date(2023, 1, 15), description="checkup")
        d = r.model_dump(by_alias=True)
        assert "petId" in d
        assert d["petId"] == 7


# ---------------------------------------------------------------------------
# VisitsResponse
# ---------------------------------------------------------------------------


class TestVisitsResponse:
    def test_empty_items(self) -> None:
        r = VisitsResponse()
        assert r.items == []

    def test_with_items(self) -> None:
        visits = [
            VisitSchema(id=1, pet_id=7, visit_date=date(2013, 1, 1), description="rabies shot"),
            VisitSchema(id=2, pet_id=8, visit_date=date(2013, 1, 2), description="rabies shot"),
        ]
        r = VisitsResponse(items=visits)
        assert len(r.items) == 2
        assert r.items[0].pet_id == 7
        assert r.items[1].pet_id == 8

    def test_from_dict(self) -> None:
        """VisitsResponse can be parsed from a dict (as returned by visits-service API)."""
        data = {
            "items": [
                {"id": 1, "petId": 7, "date": "2013-01-01", "description": "rabies shot"},
                {"id": 2, "petId": 8, "date": "2013-01-02", "description": "rabies shot"},
            ]
        }
        r = VisitsResponse(**data)
        assert len(r.items) == 2
        assert r.items[0].visit_date == date(2013, 1, 1)

    def test_serialization(self) -> None:
        visits = [
            VisitSchema(id=1, pet_id=7, visit_date=date(2013, 1, 1), description="rabies shot"),
        ]
        r = VisitsResponse(items=visits)
        d = r.model_dump(by_alias=True)
        assert "items" in d
        assert len(d["items"]) == 1
        assert d["items"][0]["petId"] == 7
        assert d["items"][0]["date"] == date(2013, 1, 1)
