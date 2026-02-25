"""Capture fully-styled screenshots of the running Petclinic application using Playwright."""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


SCREENSHOTS_DIR = Path("docs/screenshots")
BASE_URL = "http://localhost:8080"

PAGES = [
    {
        "name": "01-welcome-page",
        "url": "/",
        "full_page": False,
        "description": "Welcome / Home page",
    },
    {
        "name": "02-owners-list",
        "url": "/owners",
        "full_page": True,
        "description": "Owners list (all 10 owners)",
    },
    {
        "name": "03-owner-detail",
        "url": "/owners/details/1",
        "full_page": True,
        "description": "Owner detail - George Franklin",
    },
    {
        "name": "04-vets-list",
        "url": "/vets",
        "full_page": True,
        "description": "Veterinarians list",
    },
    {
        "name": "05-new-owner-form",
        "url": "/owners/new",
        "full_page": False,
        "description": "Register new owner form",
    },
    {
        "name": "06-add-pet-form",
        "url": "/owners/1/new-pet",
        "full_page": False,
        "description": "Add pet form (owner 1)",
    },
    {
        "name": "07-add-visit-form",
        "url": "/owners/1/pets/1/visits",
        "full_page": False,
        "description": "Add visit form (owner 1, pet 1)",
    },
]


async def capture() -> None:  # noqa: ANN201
    """Capture screenshots of all key pages."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        for entry in PAGES:
            url = f"{BASE_URL}{entry['url']}"
            output_path = SCREENSHOTS_DIR / f"{entry['name']}.png"
            print(f"Capturing {entry['name']} ({entry['description']})...")  # noqa: T201
            print(f"  URL: {url}")  # noqa: T201

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                # Extra wait for CSS/JS to fully render
                await asyncio.sleep(3)
                await page.screenshot(
                    path=str(output_path),
                    full_page=entry["full_page"],
                )
                print(f"  Saved: {output_path}")  # noqa: T201
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR capturing {entry['name']}: {exc}")  # noqa: T201

        await browser.close()
        print("\nAll screenshots captured successfully!")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(capture())
