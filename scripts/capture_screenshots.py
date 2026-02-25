"""Capture screenshots of the running Petclinic application using Playwright."""

import asyncio
from playwright.async_api import async_playwright


async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # 1. Welcome page
        print("Capturing 01-welcome-page...")
        await page.goto("http://localhost:8080/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path="docs/screenshots/01-welcome-page.png", full_page=False
        )

        # 2. Owners list
        print("Capturing 02-owners-list...")
        await page.goto("http://localhost:8080/owners")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)  # wait for data to load
        await page.screenshot(
            path="docs/screenshots/02-owners-list.png", full_page=True
        )

        # 3. Owner detail (owner 1 - George Franklin)
        print("Capturing 03-owner-detail...")
        await page.goto("http://localhost:8080/owners/details/1")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        await page.screenshot(
            path="docs/screenshots/03-owner-detail.png", full_page=True
        )

        # 4. Vets list
        print("Capturing 04-vets-list...")
        await page.goto("http://localhost:8080/vets")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        await page.screenshot(
            path="docs/screenshots/04-vets-list.png", full_page=True
        )

        # 5. New Owner form
        print("Capturing 05-new-owner-form...")
        await page.goto("http://localhost:8080/owners/new")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path="docs/screenshots/05-new-owner-form.png", full_page=False
        )

        # 6. Add Pet form (for owner 1)
        print("Capturing 06-add-pet-form...")
        await page.goto("http://localhost:8080/owners/1/new-pet")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path="docs/screenshots/06-add-pet-form.png", full_page=False
        )

        # 7. Add Visit form (for owner 1, pet 1)
        print("Capturing 07-add-visit-form...")
        await page.goto("http://localhost:8080/owners/1/pets/1/visits")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path="docs/screenshots/07-add-visit-form.png", full_page=False
        )

        await browser.close()
        print("All screenshots captured successfully!")


asyncio.run(capture())
