"""Capture fully-styled screenshots of the running Petclinic application using Playwright.

Captures standard page screenshots, the GenAI chat widget with a live conversation,
and the Grafana Petclinic Metrics dashboard.
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


SCREENSHOTS_DIR = Path("docs/screenshots")
BASE_URL = "http://localhost:8080"
GRAFANA_URL = "http://localhost:13030"

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


async def capture_chat_screenshot(page, output_path: Path) -> None:  # noqa: ANN001
    """Capture the chat widget with a live conversation."""
    print("Capturing 08-chat-widget (GenAI chat conversation)...")  # noqa: T201
    print(f"  URL: {BASE_URL}/")  # noqa: T201

    await page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
    await asyncio.sleep(2)

    # Click the chat header to expand the widget
    await page.click("#chatbox-header")
    await asyncio.sleep(1)

    # Send first message: "hello"
    await page.fill("#chatbox-input", "hello")
    await page.click("#chatbox-send-btn")
    # Wait for the bot response
    await page.wait_for_selector(".chat-bubble.bot", timeout=30000)
    await asyncio.sleep(2)

    # Send second message: "Who has dogs?"
    await page.fill("#chatbox-input", "Who has dogs?")
    await page.click("#chatbox-send-btn")
    # Wait for a second bot response (there should now be 2 bot bubbles)
    await page.wait_for_function(
        "document.querySelectorAll('.chat-bubble.bot').length >= 2",
        timeout=60000,
    )
    await asyncio.sleep(2)

    # Screenshot just the chatbox element for a focused view
    chatbox = page.locator("#chatbox")
    await chatbox.screenshot(path=str(output_path))
    print(f"  Saved: {output_path}")  # noqa: T201


async def capture_grafana_screenshot(page, output_path: Path) -> None:  # noqa: ANN001
    """Capture the Grafana Petclinic Metrics dashboard."""
    print("Capturing 09-grafana-dashboard (Grafana metrics)...")  # noqa: T201
    dashboard_url = f"{GRAFANA_URL}/d/petclinic/spring-petclinic-metrics?orgId=1&refresh=5s"
    print(f"  URL: {dashboard_url}")  # noqa: T201

    await page.goto(dashboard_url, wait_until="networkidle", timeout=60000)
    # Wait for Grafana panels to render with data
    await asyncio.sleep(10)

    await page.screenshot(path=str(output_path), full_page=False)
    print(f"  Saved: {output_path}")  # noqa: T201


async def capture() -> None:  # noqa: ANN201
    """Capture screenshots of all key pages."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # Capture standard page screenshots
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

        # Capture chat widget with live conversation
        try:
            await capture_chat_screenshot(
                page, SCREENSHOTS_DIR / "08-chat-widget.png"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR capturing chat widget: {exc}")  # noqa: T201

        # Capture Grafana dashboard
        try:
            await capture_grafana_screenshot(
                page, SCREENSHOTS_DIR / "09-grafana-dashboard.png"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR capturing Grafana dashboard: {exc}")  # noqa: T201

        await browser.close()
        print("\nAll screenshots captured successfully!")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(capture())
