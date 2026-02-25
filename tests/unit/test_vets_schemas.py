"""Unit tests for vets_service Pydantic schemas."""

import pytest
from pydantic import ValidationError

from vets_service.schemas import SpecialtySchema, VetSchema

# ---------------------------------------------------------------------------
# SpecialtySchema
# ---------------------------------------------------------------------------


class TestSpecialtySchema:
    def test_from_dict(self) -> None:
        s = SpecialtySchema(id=1, name="radiology")
        assert s.id == 1
        assert s.name == "radiology"

    def test_name_optional(self) -> None:
        s = SpecialtySchema(id=1)
        assert s.name is None

    def test_id_required(self) -> None:
        with pytest.raises(ValidationError):
            SpecialtySchema(name="radiology")  # type: ignore[call-arg]

    def test_from_orm_object(self) -> None:
        """Verify from_attributes works with ORM-like objects."""

        class FakeSpecialty:
            id = 1
            name = "radiology"

        s = SpecialtySchema.model_validate(FakeSpecialty(), from_attributes=True)
        assert s.id == 1
        assert s.name == "radiology"

    def test_serialization(self) -> None:
        s = SpecialtySchema(id=1, name="radiology")
        d = s.model_dump()
        assert d == {"id": 1, "name": "radiology"}


# ---------------------------------------------------------------------------
# VetSchema
# ---------------------------------------------------------------------------


class TestVetSchema:
    def test_from_dict_with_aliases(self) -> None:
        v = VetSchema(id=1, firstName="James", lastName="Carter")  # type: ignore[call-arg]
        assert v.id == 1
        assert v.first_name == "James"
        assert v.last_name == "Carter"
        assert v.specialties == []

    def test_from_dict_with_field_names(self) -> None:
        """populate_by_name allows using snake_case field names."""
        v = VetSchema(id=1, first_name="James", last_name="Carter")
        assert v.first_name == "James"
        assert v.last_name == "Carter"

    def test_specialties_default_empty(self) -> None:
        v = VetSchema(id=1, first_name="James", last_name="Carter")
        assert v.specialties == []

    def test_with_specialties(self) -> None:
        specs = [
            SpecialtySchema(id=1, name="radiology"),
            SpecialtySchema(id=2, name="surgery"),
        ]
        v = VetSchema(id=3, first_name="Linda", last_name="Douglas", specialties=specs)
        assert len(v.specialties) == 2
        assert v.specialties[0].name == "radiology"
        assert v.specialties[1].name == "surgery"

    def test_serialization_uses_aliases(self) -> None:
        v = VetSchema(
            id=1,
            first_name="James",
            last_name="Carter",
            specialties=[SpecialtySchema(id=1, name="radiology")],
        )
        d = v.model_dump(by_alias=True)
        assert "firstName" in d
        assert d["firstName"] == "James"
        assert "lastName" in d
        assert d["lastName"] == "Carter"
        assert len(d["specialties"]) == 1

    def test_from_orm_object(self) -> None:
        """Verify from_attributes works with ORM-like objects."""

        class FakeSpecialty:
            id = 1
            name = "radiology"

        class FakeVet:
            id = 2
            first_name = "Helen"
            last_name = "Leary"
            specialties = [FakeSpecialty()]

        v = VetSchema.model_validate(FakeVet(), from_attributes=True)
        assert v.id == 2
        assert v.first_name == "Helen"
        assert v.last_name == "Leary"
        assert len(v.specialties) == 1
        assert v.specialties[0].name == "radiology"

    def test_id_required(self) -> None:
        with pytest.raises(ValidationError):
            VetSchema(first_name="James", last_name="Carter")  # type: ignore[call-arg]

    def test_first_name_required(self) -> None:
        with pytest.raises(ValidationError):
            VetSchema(id=1, last_name="Carter")  # type: ignore[call-arg]

    def test_last_name_required(self) -> None:
        with pytest.raises(ValidationError):
            VetSchema(id=1, first_name="James")  # type: ignore[call-arg]

    def test_from_json_with_nested_specialties(self) -> None:
        """Parse from JSON-like dict (as returned by vets-service API)."""
        data = {
            "id": 3,
            "firstName": "Linda",
            "lastName": "Douglas",
            "specialties": [
                {"id": 2, "name": "surgery"},
                {"id": 3, "name": "dentistry"},
            ],
        }
        v = VetSchema(**data)
        assert v.first_name == "Linda"
        assert len(v.specialties) == 2
        assert v.specialties[0].name == "surgery"
