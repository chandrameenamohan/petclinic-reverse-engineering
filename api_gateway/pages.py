"""API Gateway — server-side rendered page routes.

Jinja2 + HTMX pages served by the gateway (welcome, owners, vets, etc.).
"""

from __future__ import annotations

import datetime as _dt
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from api_gateway.bff import GatewayOwnerDetails, get_owner_details

if TYPE_CHECKING:
    from shared.config import BaseServiceSettings

_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _format_date(value: str | None) -> str:
    """Format ISO date (yyyy-mm-dd) to 'yyyy MMM dd' display format."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")  # noqa: DTZ007
        return dt.strftime("%Y %b %d")
    except (ValueError, TypeError):
        return value


templates.env.filters["format_date"] = _format_date

# Module-level service URLs — configurable via configure_pages().
CUSTOMERS_URL = "http://localhost:8081"
VISITS_URL = "http://localhost:8082"
VETS_URL = "http://localhost:8083"

router = APIRouter()


def configure_pages(settings: BaseServiceSettings) -> None:
    """Update backend service URLs from settings."""
    global CUSTOMERS_URL, VISITS_URL, VETS_URL  # noqa: PLW0603
    CUSTOMERS_URL = settings.customers_service_url
    VISITS_URL = settings.visits_service_url
    VETS_URL = settings.vets_service_url


@router.get("/", response_class=HTMLResponse)
async def welcome(request: Request) -> HTMLResponse:
    """Render the Welcome / Home page."""
    return templates.TemplateResponse(request, "welcome.html")


@router.get("/owners", response_class=HTMLResponse)
async def owners_list(request: Request) -> HTMLResponse:
    """Render the Owners list page — fetches owners from customers service."""
    owners: list[dict[str, object]] = []
    error = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CUSTOMERS_URL}/owners")
            resp.raise_for_status()
            owners = resp.json()
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to fetch owners from customers service")
        error = True

    return templates.TemplateResponse(
        request,
        "owners_list.html",
        {"owners": owners, "error": error},
    )


@router.get("/vets", response_class=HTMLResponse)
async def vets_list(request: Request) -> HTMLResponse:
    """Render the Veterinarians list page — fetches vets from vets service."""
    vets: list[dict[str, object]] = []
    error = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{VETS_URL}/vets")
            resp.raise_for_status()
            vets = resp.json()
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to fetch vets from vets service")
        error = True

    return templates.TemplateResponse(
        request,
        "vets_list.html",
        {"vets": vets, "error": error},
    )


@router.get("/owners/details/{owner_id}", response_class=HTMLResponse)
async def owner_details(request: Request, owner_id: int) -> HTMLResponse:
    """Render the Owner details page — fetches owner+visits via BFF."""
    owner_data: dict[str, object] | None = None
    error = False
    try:
        result = await get_owner_details(owner_id)
        if isinstance(result, GatewayOwnerDetails):
            owner_data = result.model_dump(by_alias=True)
        else:
            # JSONResponse with 502 = backend error
            if hasattr(result, "status_code") and result.status_code >= 500:
                error = True
    except Exception:
        logger.warning("Failed to fetch owner details for {}", owner_id)
        error = True

    return templates.TemplateResponse(
        request,
        "owner_details.html",
        {"owner": owner_data, "error": error},
    )


def _validate_owner_form(
    first_name: str,
    last_name: str,
    address: str,
    city: str,
    telephone: str,
) -> dict[str, str]:
    """Validate owner form fields, return dict of field→error message."""
    errors: dict[str, str] = {}
    if not first_name.strip():
        errors["firstName"] = "First name is required."
    if not last_name.strip():
        errors["lastName"] = "Last name is required."
    if not address.strip():
        errors["address"] = "Address is required."
    if not city.strip():
        errors["city"] = "City is required."
    if not telephone.strip():
        errors["telephone"] = "Telephone is required."
    elif not re.match(r"^\d{1,12}$", telephone.strip()):
        errors["telephone"] = "Telephone must be 1-12 digits only."
    return errors


@router.get("/owners/new", response_class=HTMLResponse)
async def owner_new_form(request: Request) -> HTMLResponse:
    """Render the Create Owner form."""
    return templates.TemplateResponse(
        request,
        "owner_form.html",
        {"owner": None, "errors": None, "edit_mode": False, "error": False},
    )


@router.post("/owners/new", response_model=None)
async def owner_new_submit(
    request: Request,
    firstName: str = Form(""),  # noqa: N803
    lastName: str = Form(""),  # noqa: N803
    address: str = Form(""),
    city: str = Form(""),
    telephone: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    """Handle Create Owner form submission."""
    errors = _validate_owner_form(firstName, lastName, address, city, telephone)
    form_data = {
        "firstName": firstName,
        "lastName": lastName,
        "address": address,
        "city": city,
        "telephone": telephone,
    }

    if errors:
        return templates.TemplateResponse(
            request,
            "owner_form.html",
            {"owner": form_data, "errors": errors, "edit_mode": False, "error": False},
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{CUSTOMERS_URL}/owners",
                json=form_data,
            )
            resp.raise_for_status()
            created_owner = resp.json()
            owner_id = created_owner.get("id", "")
            return RedirectResponse(
                url=f"/owners/details/{owner_id}",
                status_code=303,
            )
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to create owner via customers service")
        return templates.TemplateResponse(
            request,
            "owner_form.html",
            {
                "owner": form_data,
                "errors": {"_form": "Could not create owner. Please try again."},
                "edit_mode": False,
                "error": False,
            },
        )


# ---------------------------------------------------------------------------
# Pet form routes
# ---------------------------------------------------------------------------


def _validate_pet_form(name: str, birth_date: str) -> dict[str, str]:
    """Validate pet form fields, return dict of field→error message."""
    errors: dict[str, str] = {}
    if not name.strip():
        errors["name"] = "Name is required."
    if not birth_date.strip():
        errors["birthDate"] = "Birth date is required."
    return errors


async def _fetch_pet_types() -> list[dict[str, object]]:
    """Fetch pet types from customers service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CUSTOMERS_URL}/petTypes")
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to fetch pet types from customers service")
        return []


async def _fetch_owner_name(owner_id: int) -> str:
    """Fetch owner and return 'firstName lastName' string."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CUSTOMERS_URL}/owners/{owner_id}")
            resp.raise_for_status()
            data = resp.json()
            if data:
                return f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to fetch owner {} for pet form", owner_id)
    return ""


@router.get("/owners/{owner_id}/new-pet", response_class=HTMLResponse)
async def pet_new_form(request: Request, owner_id: int) -> HTMLResponse:
    """Render the Create Pet form — fetches owner name and pet types."""
    owner_name = await _fetch_owner_name(owner_id)
    pet_types = await _fetch_pet_types()
    return templates.TemplateResponse(
        request,
        "pet_form.html",
        {
            "pet": None,
            "errors": None,
            "edit_mode": False,
            "error": False,
            "owner_name": owner_name,
            "owner_id": owner_id,
            "pet_types": pet_types,
        },
    )


@router.post("/owners/{owner_id}/new-pet", response_model=None)
async def pet_new_submit(
    request: Request,
    owner_id: int,
    name: str = Form(""),
    birthDate: str = Form(""),  # noqa: N803
    typeId: str = Form("1"),  # noqa: N803
) -> HTMLResponse | RedirectResponse:
    """Handle Create Pet form submission."""
    errors = _validate_pet_form(name, birthDate)
    form_data = {"name": name, "birthDate": birthDate, "typeId": typeId}

    if errors:
        owner_name = await _fetch_owner_name(owner_id)
        pet_types = await _fetch_pet_types()
        return templates.TemplateResponse(
            request,
            "pet_form.html",
            {
                "pet": form_data,
                "errors": errors,
                "edit_mode": False,
                "error": False,
                "owner_name": owner_name,
                "owner_id": owner_id,
                "pet_types": pet_types,
            },
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{CUSTOMERS_URL}/owners/{owner_id}/pets",
                json={"name": name, "birthDate": birthDate, "typeId": int(typeId)},
            )
            resp.raise_for_status()
            return RedirectResponse(
                url=f"/owners/details/{owner_id}",
                status_code=303,
            )
    except (httpx.HTTPError, httpx.HTTPStatusError, ValueError):
        logger.warning("Failed to create pet for owner {}", owner_id)
        owner_name = await _fetch_owner_name(owner_id)
        pet_types = await _fetch_pet_types()
        return templates.TemplateResponse(
            request,
            "pet_form.html",
            {
                "pet": form_data,
                "errors": {"_form": "Could not create pet. Please try again."},
                "edit_mode": False,
                "error": False,
                "owner_name": owner_name,
                "owner_id": owner_id,
                "pet_types": pet_types,
            },
        )


@router.get("/owners/{owner_id}/pets/{pet_id}", response_class=HTMLResponse)
async def pet_edit_form(
    request: Request, owner_id: int, pet_id: int
) -> HTMLResponse:
    """Render the Edit Pet form — fetches pet data and pet types."""
    pet_data: dict[str, object] | None = None
    owner_name = ""
    error = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{CUSTOMERS_URL}/owners/{owner_id}/pets/{pet_id}"
            )
            resp.raise_for_status()
            pet_data = resp.json()
            if pet_data:
                owner_name = str(pet_data.get("owner", ""))
                # Map type.id → typeId for template select matching
                pet_type = pet_data.get("type")
                if isinstance(pet_type, dict):
                    pet_data["typeId"] = pet_type.get("id")
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to fetch pet {}/{} for editing", owner_id, pet_id)
        error = True

    pet_types = await _fetch_pet_types()
    return templates.TemplateResponse(
        request,
        "pet_form.html",
        {
            "pet": pet_data,
            "errors": None,
            "edit_mode": True,
            "error": error,
            "owner_name": owner_name,
            "owner_id": owner_id,
            "pet_id": pet_id,
            "pet_types": pet_types,
        },
    )


@router.post("/owners/{owner_id}/pets/{pet_id}", response_model=None)
async def pet_edit_submit(
    request: Request,
    owner_id: int,
    pet_id: int,
    name: str = Form(""),
    birthDate: str = Form(""),  # noqa: N803
    typeId: str = Form("1"),  # noqa: N803
) -> HTMLResponse | RedirectResponse:
    """Handle Edit Pet form submission."""
    errors = _validate_pet_form(name, birthDate)
    form_data = {"name": name, "birthDate": birthDate, "typeId": typeId}

    if errors:
        # Re-fetch owner name and pet types for re-render
        pet_detail: dict[str, object] | None = None
        owner_name = ""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{CUSTOMERS_URL}/owners/{owner_id}/pets/{pet_id}"
                )
                resp.raise_for_status()
                pet_detail = resp.json()
                if pet_detail:
                    owner_name = str(pet_detail.get("owner", ""))
        except (httpx.HTTPError, httpx.HTTPStatusError):
            pass
        pet_types = await _fetch_pet_types()
        return templates.TemplateResponse(
            request,
            "pet_form.html",
            {
                "pet": form_data,
                "errors": errors,
                "edit_mode": True,
                "error": False,
                "owner_name": owner_name,
                "owner_id": owner_id,
                "pet_id": pet_id,
                "pet_types": pet_types,
            },
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{CUSTOMERS_URL}/owners/{owner_id}/pets/{pet_id}",
                json={
                    "id": pet_id,
                    "name": name,
                    "birthDate": birthDate,
                    "typeId": int(typeId),
                },
            )
            resp.raise_for_status()
            return RedirectResponse(
                url=f"/owners/details/{owner_id}",
                status_code=303,
            )
    except (httpx.HTTPError, httpx.HTTPStatusError, ValueError):
        logger.warning("Failed to update pet {}/{}", owner_id, pet_id)
        pet_types = await _fetch_pet_types()
        return templates.TemplateResponse(
            request,
            "pet_form.html",
            {
                "pet": form_data,
                "errors": {"_form": "Could not update pet. Please try again."},
                "edit_mode": True,
                "error": False,
                "owner_name": "",
                "owner_id": owner_id,
                "pet_id": pet_id,
                "pet_types": pet_types,
            },
        )


@router.get("/owners/{owner_id}/edit", response_class=HTMLResponse)
async def owner_edit_form(request: Request, owner_id: int) -> HTMLResponse:
    """Render the Edit Owner form — pre-populated with existing data."""
    owner_data: dict[str, object] | None = None
    error = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CUSTOMERS_URL}/owners/{owner_id}")
            resp.raise_for_status()
            owner_data = resp.json()
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to fetch owner {} for editing", owner_id)
        error = True

    return templates.TemplateResponse(
        request,
        "owner_form.html",
        {"owner": owner_data, "errors": None, "edit_mode": True, "error": error},
    )


@router.post("/owners/{owner_id}/edit", response_model=None)
async def owner_edit_submit(
    request: Request,
    owner_id: int,
    firstName: str = Form(""),  # noqa: N803
    lastName: str = Form(""),  # noqa: N803
    address: str = Form(""),
    city: str = Form(""),
    telephone: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    """Handle Edit Owner form submission."""
    errors = _validate_owner_form(firstName, lastName, address, city, telephone)
    form_data = {
        "firstName": firstName,
        "lastName": lastName,
        "address": address,
        "city": city,
        "telephone": telephone,
    }

    if errors:
        return templates.TemplateResponse(
            request,
            "owner_form.html",
            {"owner": form_data, "errors": errors, "edit_mode": True, "error": False},
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{CUSTOMERS_URL}/owners/{owner_id}",
                json=form_data,
            )
            resp.raise_for_status()
            return RedirectResponse(
                url=f"/owners/details/{owner_id}",
                status_code=303,
            )
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to update owner {} via customers service", owner_id)
        return templates.TemplateResponse(
            request,
            "owner_form.html",
            {
                "owner": form_data,
                "errors": {"_form": "Could not update owner. Please try again."},
                "edit_mode": True,
                "error": False,
            },
        )


# ---------------------------------------------------------------------------
# Visit form routes
# ---------------------------------------------------------------------------


async def _fetch_previous_visits(
    owner_id: int, pet_id: int
) -> list[dict[str, object]]:
    """Fetch previous visits for a pet from visits service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{VISITS_URL}/owners/{owner_id}/pets/{pet_id}/visits"
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning("Failed to fetch visits for owner {}/pet {}", owner_id, pet_id)
        return []


@router.get("/owners/{owner_id}/pets/{pet_id}/visits", response_class=HTMLResponse)
async def visit_form(
    request: Request, owner_id: int, pet_id: int
) -> HTMLResponse:
    """Render the Add Visit form with previous visits list."""
    visits = await _fetch_previous_visits(owner_id, pet_id)
    today_str = _dt.date.today().isoformat()
    return templates.TemplateResponse(
        request,
        "visit_form.html",
        {
            "form_data": None,
            "errors": None,
            "visits": visits,
            "today": today_str,
            "owner_id": owner_id,
            "pet_id": pet_id,
        },
    )


@router.post("/owners/{owner_id}/pets/{pet_id}/visits", response_model=None)
async def visit_form_submit(
    request: Request,
    owner_id: int,
    pet_id: int,
    date: str = Form(""),  # noqa: A002
    description: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    """Handle Add Visit form submission."""
    errors: dict[str, str] = {}
    if not description.strip():
        errors["description"] = "Description is required."

    form_data = {"date": date, "description": description}

    if errors:
        visits = await _fetch_previous_visits(owner_id, pet_id)
        return templates.TemplateResponse(
            request,
            "visit_form.html",
            {
                "form_data": form_data,
                "errors": errors,
                "visits": visits,
                "today": date or _dt.date.today().isoformat(),
                "owner_id": owner_id,
                "pet_id": pet_id,
            },
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{VISITS_URL}/owners/{owner_id}/pets/{pet_id}/visits",
                json={"date": date, "description": description},
            )
            resp.raise_for_status()
            return RedirectResponse(
                url=f"/owners/details/{owner_id}",
                status_code=303,
            )
    except (httpx.HTTPError, httpx.HTTPStatusError):
        logger.warning(
            "Failed to create visit for owner {}/pet {}", owner_id, pet_id
        )
        visits = await _fetch_previous_visits(owner_id, pet_id)
        return templates.TemplateResponse(
            request,
            "visit_form.html",
            {
                "form_data": form_data,
                "errors": {"_form": "Could not create visit. Please try again."},
                "visits": visits,
                "today": date or "",
                "owner_id": owner_id,
                "pet_id": pet_id,
            },
        )
