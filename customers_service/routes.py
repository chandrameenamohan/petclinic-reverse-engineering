"""REST API routes for the customers service."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from customers_service.models import Owner, Pet, PetType
from customers_service.schemas import (
    OwnerCreateRequest,
    OwnerSchema,
    PetCreateRequest,
    PetDetailsSchema,
    PetSchema,
    PetTypeSchema,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Placeholder dependency — overridden by app startup via dependency_overrides."""
    raise RuntimeError("Database session not configured")
    yield  # noqa: RET504  # pragma: no cover


router = APIRouter(tags=["owners"])


@router.get("/petTypes", response_model=list[PetTypeSchema])
async def get_pet_types(db: AsyncSession = Depends(get_db)) -> list[PetType]:  # noqa: B008
    """Return all pet types sorted alphabetically by name."""
    result = await db.execute(select(PetType).order_by(PetType.name))
    return list(result.scalars().all())


@router.get("/owners", response_model=list[OwnerSchema])
async def list_owners(db: AsyncSession = Depends(get_db)) -> list[Owner]:  # noqa: B008
    """Return all owners with eagerly loaded pets sorted alphabetically by name."""
    result = await db.execute(
        select(Owner).options(
            selectinload(Owner.pets).selectinload(Pet.type),
        )
    )
    owners = list(result.scalars().all())
    # Sort each owner's pets alphabetically by name (matching Java PropertyComparator)
    for owner in owners:
        owner.pets = sorted(owner.pets, key=lambda p: (p.name or ""))
    return owners


@router.get("/owners/{owner_id}", response_model=OwnerSchema | None)
async def get_owner(
    owner_id: int = Path(ge=1),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Owner | JSONResponse:
    """Return a single owner by ID, or null if not found (Java Optional behavior)."""
    result = await db.execute(
        select(Owner)
        .where(Owner.id == owner_id)
        .options(selectinload(Owner.pets).selectinload(Pet.type))
    )
    owner = result.scalar_one_or_none()
    if owner is None:
        return JSONResponse(content=None)
    # Sort pets alphabetically by name
    owner.pets = sorted(owner.pets, key=lambda p: (p.name or ""))
    return owner


@router.put("/owners/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_owner(
    request: OwnerCreateRequest,
    owner_id: int = Path(ge=1),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Update an existing owner by ID. Returns 204 on success, 404 if not found."""
    result = await db.execute(select(Owner).where(Owner.id == owner_id))
    owner = result.scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")
    for field, value in request.model_dump().items():
        setattr(owner, field, value)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/owners/{owner_id}/pets",
    response_model=PetSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_pet(
    request: PetCreateRequest,
    owner_id: int = Path(ge=1),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Pet:
    """Create a new pet for an existing owner. Returns 404 if owner not found."""
    result = await db.execute(select(Owner).where(Owner.id == owner_id))
    owner = result.scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")
    pet = Pet(
        name=request.name,
        birth_date=request.birth_date,
        type_id=request.type_id,
        owner_id=owner_id,
    )
    db.add(pet)
    await db.flush()
    await db.refresh(pet, attribute_names=["type"])
    return pet


@router.get(
    "/owners/{owner_id}/pets/{pet_id}",
    response_model=PetDetailsSchema,
)
async def get_pet(
    owner_id: int = Path(ge=1),  # noqa: B008, ARG001
    pet_id: int = Path(ge=1),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PetDetailsSchema:
    """Return pet details with owner as 'firstName lastName' string. 404 if not found."""
    result = await db.execute(
        select(Pet)
        .where(Pet.id == pet_id)
        .options(selectinload(Pet.type), selectinload(Pet.owner))
    )
    pet = result.scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return PetDetailsSchema(
        id=pet.id,
        name=pet.name,
        owner=f"{pet.owner.first_name} {pet.owner.last_name}",
        birth_date=pet.birth_date,
        type=PetTypeSchema(id=pet.type.id, name=pet.type.name) if pet.type else None,
    )


@router.put(
    "/owners/{owner_id}/pets/{pet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_pet(
    request: PetCreateRequest,
    owner_id: int = Path(ge=1),  # noqa: B008, ARG001
    pet_id: int = Path(ge=1),  # noqa: B008, ARG001
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Update a pet. ID comes from request body, not path (Java quirk). Returns 204 or 404."""
    if request.id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pet id required in body")
    result = await db.execute(select(Pet).where(Pet.id == request.id))
    pet = result.scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    pet.name = request.name
    pet.birth_date = request.birth_date
    pet.type_id = request.type_id
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/owners", response_model=OwnerSchema, status_code=status.HTTP_201_CREATED)
async def create_owner(
    request: OwnerCreateRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Owner:
    """Create a new owner with validation."""
    owner = Owner(**request.model_dump())
    db.add(owner)
    await db.flush()
    await db.refresh(owner, attribute_names=["pets"])
    return owner
