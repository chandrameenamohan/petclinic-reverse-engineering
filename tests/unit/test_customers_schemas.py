"""Unit tests for customers_service Pydantic schemas."""

from datetime import date

import pytest
from pydantic import ValidationError

from customers_service.schemas import (
    OwnerCreateRequest,
    OwnerSchema,
    PetCreateRequest,
    PetDetailsSchema,
    PetSchema,
    PetTypeSchema,
)

# ---------------------------------------------------------------------------
# PetTypeSchema
# ---------------------------------------------------------------------------


class TestPetTypeSchema:
    def test_from_dict(self):
        s = PetTypeSchema(id=1, name="cat")
        assert s.id == 1
        assert s.name == "cat"

    def test_name_optional(self):
        s = PetTypeSchema(id=2)
        assert s.name is None

    def test_from_attributes(self):
        """Verify model_config from_attributes allows ORM objects."""

        class FakeORM:
            id = 3
            name = "dog"

        s = PetTypeSchema.model_validate(FakeORM(), from_attributes=True)
        assert s.id == 3
        assert s.name == "dog"

    def test_serialization(self):
        s = PetTypeSchema(id=1, name="cat")
        d = s.model_dump()
        assert d == {"id": 1, "name": "cat"}


# ---------------------------------------------------------------------------
# PetSchema
# ---------------------------------------------------------------------------


class TestPetSchema:
    def test_from_dict_with_alias(self):
        s = PetSchema(id=1, name="Leo", birthDate="2010-09-07", type={"id": 1, "name": "cat"})
        assert s.id == 1
        assert s.name == "Leo"
        assert s.birth_date == date(2010, 9, 7)
        assert s.type is not None
        assert s.type.name == "cat"

    def test_from_dict_with_field_name(self):
        """populate_by_name allows using birth_date instead of birthDate."""
        s = PetSchema(id=1, name="Leo", birth_date=date(2010, 9, 7))
        assert s.birth_date == date(2010, 9, 7)

    def test_optional_fields(self):
        s = PetSchema(id=1)
        assert s.name is None
        assert s.birth_date is None
        assert s.type is None

    def test_serialization_uses_alias(self):
        s = PetSchema(id=1, name="Leo", birth_date=date(2010, 9, 7), type=PetTypeSchema(id=1, name="cat"))
        d = s.model_dump(by_alias=True)
        assert "birthDate" in d
        assert d["birthDate"] == date(2010, 9, 7)

    def test_from_orm_object(self):
        class FakePetType:
            id = 1
            name = "cat"

        class FakePet:
            id = 1
            name = "Leo"
            birth_date = date(2010, 9, 7)
            type = FakePetType()

        s = PetSchema.model_validate(FakePet(), from_attributes=True)
        assert s.id == 1
        assert s.birth_date == date(2010, 9, 7)
        assert s.type is not None
        assert s.type.name == "cat"


# ---------------------------------------------------------------------------
# OwnerSchema
# ---------------------------------------------------------------------------


class TestOwnerSchema:
    def test_from_dict_with_aliases(self):
        s = OwnerSchema(
            id=1,
            firstName="George",
            lastName="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="6085551023",
        )
        assert s.first_name == "George"
        assert s.last_name == "Franklin"

    def test_from_dict_with_field_names(self):
        s = OwnerSchema(
            id=1,
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="6085551023",
        )
        assert s.first_name == "George"

    def test_pets_default_empty(self):
        s = OwnerSchema(
            id=1,
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="6085551023",
        )
        assert s.pets == []

    def test_with_nested_pets(self):
        s = OwnerSchema(
            id=1,
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="6085551023",
            pets=[{"id": 1, "name": "Leo", "birthDate": "2010-09-07", "type": {"id": 1, "name": "cat"}}],
        )
        assert len(s.pets) == 1
        assert s.pets[0].name == "Leo"

    def test_serialization_uses_aliases(self):
        s = OwnerSchema(
            id=1,
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="6085551023",
        )
        d = s.model_dump(by_alias=True)
        assert "firstName" in d
        assert "lastName" in d


# ---------------------------------------------------------------------------
# OwnerCreateRequest
# ---------------------------------------------------------------------------


class TestOwnerCreateRequest:
    def test_valid_request(self):
        r = OwnerCreateRequest(
            firstName="George",
            lastName="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="6085551023",
        )
        assert r.first_name == "George"
        assert r.telephone == "6085551023"

    def test_valid_request_field_names(self):
        r = OwnerCreateRequest(
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="123",
        )
        assert r.first_name == "George"

    def test_telephone_digits_only(self):
        with pytest.raises(ValidationError, match="Telephone must be 1-12 digits"):
            OwnerCreateRequest(
                first_name="George",
                last_name="Franklin",
                address="110 W. Liberty St.",
                city="Madison",
                telephone="abc",
            )

    def test_telephone_too_long(self):
        with pytest.raises(ValidationError, match="Telephone must be 1-12 digits"):
            OwnerCreateRequest(
                first_name="George",
                last_name="Franklin",
                address="110 W. Liberty St.",
                city="Madison",
                telephone="1234567890123",  # 13 digits
            )

    def test_telephone_empty(self):
        with pytest.raises(ValidationError):
            OwnerCreateRequest(
                first_name="George",
                last_name="Franklin",
                address="110 W. Liberty St.",
                city="Madison",
                telephone="",
            )

    def test_first_name_blank(self):
        with pytest.raises(ValidationError):
            OwnerCreateRequest(
                first_name="",
                last_name="Franklin",
                address="110 W. Liberty St.",
                city="Madison",
                telephone="123",
            )

    def test_last_name_blank(self):
        with pytest.raises(ValidationError):
            OwnerCreateRequest(
                first_name="George",
                last_name="",
                address="110 W. Liberty St.",
                city="Madison",
                telephone="123",
            )

    def test_address_blank(self):
        with pytest.raises(ValidationError):
            OwnerCreateRequest(
                first_name="George",
                last_name="Franklin",
                address="",
                city="Madison",
                telephone="123",
            )

    def test_city_blank(self):
        with pytest.raises(ValidationError):
            OwnerCreateRequest(
                first_name="George",
                last_name="Franklin",
                address="110 W. Liberty St.",
                city="",
                telephone="123",
            )

    def test_telephone_single_digit(self):
        """Min boundary: 1 digit is valid."""
        r = OwnerCreateRequest(
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="5",
        )
        assert r.telephone == "5"

    def test_telephone_twelve_digits(self):
        """Max boundary: 12 digits is valid."""
        r = OwnerCreateRequest(
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="123456789012",
        )
        assert r.telephone == "123456789012"


# ---------------------------------------------------------------------------
# PetCreateRequest
# ---------------------------------------------------------------------------


class TestPetCreateRequest:
    def test_valid_request_with_alias(self):
        r = PetCreateRequest(name="Leo", birthDate="2010-09-07", typeId=1)
        assert r.name == "Leo"
        assert r.birth_date == date(2010, 9, 7)
        assert r.type_id == 1

    def test_valid_request_field_names(self):
        r = PetCreateRequest(name="Leo", birth_date=date(2010, 9, 7), type_id=1)
        assert r.type_id == 1

    def test_id_optional_defaults_none(self):
        r = PetCreateRequest(name="Leo", type_id=1)
        assert r.id is None

    def test_id_can_be_set(self):
        r = PetCreateRequest(id=5, name="Leo", type_id=1)
        assert r.id == 5

    def test_name_optional(self):
        r = PetCreateRequest(type_id=1)
        assert r.name is None

    def test_birth_date_optional(self):
        r = PetCreateRequest(name="Leo", type_id=1)
        assert r.birth_date is None

    def test_type_id_required(self):
        with pytest.raises(ValidationError):
            PetCreateRequest(name="Leo")

    def test_serialization_uses_alias(self):
        r = PetCreateRequest(name="Leo", birth_date=date(2010, 9, 7), type_id=1)
        d = r.model_dump(by_alias=True)
        assert "birthDate" in d
        assert "typeId" in d


# ---------------------------------------------------------------------------
# PetDetailsSchema
# ---------------------------------------------------------------------------


class TestPetDetailsSchema:
    def test_from_dict(self):
        s = PetDetailsSchema(
            id=1,
            name="Leo",
            owner="George Franklin",
            birthDate="2010-09-07",
            type={"id": 1, "name": "cat"},
        )
        assert s.id == 1
        assert s.owner == "George Franklin"
        assert s.birth_date == date(2010, 9, 7)

    def test_from_field_names(self):
        s = PetDetailsSchema(
            id=1,
            name="Leo",
            owner="George Franklin",
            birth_date=date(2010, 9, 7),
            type=PetTypeSchema(id=1, name="cat"),
        )
        assert s.birth_date == date(2010, 9, 7)

    def test_serialization_alias(self):
        s = PetDetailsSchema(
            id=1,
            name="Leo",
            owner="George Franklin",
            birth_date=date(2010, 9, 7),
            type=PetTypeSchema(id=1, name="cat"),
        )
        d = s.model_dump(by_alias=True)
        assert "birthDate" in d
        assert d["owner"] == "George Franklin"

    def test_owner_is_string(self):
        """owner is a denormalized 'firstName lastName' string, not a nested object."""
        s = PetDetailsSchema(
            id=1,
            name="Leo",
            owner="George Franklin",
            birth_date=date(2010, 9, 7),
            type=PetTypeSchema(id=1, name="cat"),
        )
        assert isinstance(s.owner, str)
