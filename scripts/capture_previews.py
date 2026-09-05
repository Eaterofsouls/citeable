import asyncio
import os
from playwright.async_api import async_playwright

async def capture_previews():
    os.makedirs("screenshots/previews", exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = await context.new_page()

        # Set admin token and analyst id to dismiss all overlay modals
        await page.goto("http://127.0.0.1:8000/docs.html#page=index")
        await page.evaluate("""() => {
            sessionStorage.setItem('areos_api_token', 'dev-token');
            localStorage.setItem('areos_analyst_id', 'Alice S.');
            localStorage.setItem('areos_help_tour_dismissed', 'true');
        }""")
        await page.reload()
        await page.wait_for_timeout(1000)

        # 1. Preview Index Architecture
        print("Capturing preview: Index Architecture...")
        await page.goto("http://127.0.0.1:8000/docs.html#page=index")
        await page.wait_for_timeout(1200)
        card1 = page.locator(".docs-diagram-card").first
        await card1.scroll_into_view_if_needed()
        await page.wait_for_timeout(300)
        await card1.screenshot(path="screenshots/previews/preview_index_architecture.png")

        # Open in fullscreen canvas
        expand_btn = card1.locator(".docs-diagram-expand-btn")
        await expand_btn.click()
        await page.wait_for_timeout(600)
        await page.screenshot(path="screenshots/previews/preview_index_fullscreen.png")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        # 2. Preview Scoring 5-Layer Model & Gate Hierarchy
        print("Capturing preview: Scoring...")
        await page.goto("http://127.0.0.1:8000/docs.html#page=scoring")
        await page.wait_for_timeout(1200)
        card2 = page.locator(".docs-diagram-card").nth(0) # 5-layer
        await card2.scroll_into_view_if_needed()
        await card2.screenshot(path="screenshots/previews/preview_scoring_layers.png")

        card3 = page.locator(".docs-diagram-card").nth(1) # deductions
        await card3.scroll_into_view_if_needed()
        await card3.screenshot(path="screenshots/previews/preview_scoring_deductions.png")

        card4 = page.locator(".docs-diagram-card").nth(2) # gate hierarchy
        await card4.scroll_into_view_if_needed()
        await card4.screenshot(path="screenshots/previews/preview_scoring_gate_hierarchy.png")

        # 3. Preview Security 4-Layer Perimeter & SSRF
        print("Capturing preview: Security...")
        await page.goto("http://127.0.0.1:8000/docs.html#page=security")
        await page.wait_for_timeout(1200)
        card5 = page.locator(".docs-diagram-card").nth(0) # SSRF
        await card5.scroll_into_view_if_needed()
        await card5.screenshot(path="screenshots/previews/preview_security_ssrf.png")

        card6 = page.locator(".docs-diagram-card").nth(1) # 4-layer
        await card6.scroll_into_view_if_needed()
        await card6.screenshot(path="screenshots/previews/preview_security_perimeter.png")

        await browser.close()
        print("All previews captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_previews())
