import asyncio
import os
from playwright.async_api import async_playwright

PAGES = [
    # External Pages
    "index",
    "architecture",
    "lifecycle",
    "scoring",
    "knowledge",
    "review",
    "ai-architecture",
    "security",
    "data-model",
    "api",
    "governance",
    # Internal Pages
    "00-orientation",
    "01-architecture",
    "02-repository-map",
    "03-audit-engine",
    "04-data-model",
    "05-evidence-findings",
    "06-scoring",
    "07-ai-llm",
    "08-frontend",
    "09-api-reference",
    "10-security",
    "11-governance",
    "12-testing-qa",
    "13-operations",
    "14-adrs",
    "15-known-issues",
    "16-historical",
    "17-how-to-change",
    "18-changelog"
]

os.makedirs("screenshots/diagrams", exist_ok=True)

async def capture_diagrams():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = await context.new_page()

        # Set admin token in sessionStorage so internal pages are accessible
        await page.goto("http://127.0.0.1:8000/docs.html#page=index")
        await page.evaluate("sessionStorage.setItem('areos_api_token', 'dev-token')")
        await page.reload()
        await page.wait_for_timeout(1000)

        total_captured = 0

        for page_id in PAGES:
            url = f"http://127.0.0.1:8000/docs.html#page={page_id}"
            print(f"Navigating to {page_id}...")
            await page.goto(url)
            await page.wait_for_timeout(800)

            # Find all diagram cards or svg containers
            diagram_cards = page.locator(".docs-diagram-card, .mermaid, pre.mermaid")
            count = await diagram_cards.count()

            if count > 0:
                print(f"  Found {count} diagram(s) on {page_id}")
                for i in range(count):
                    card = diagram_cards.nth(i)
                    # Ensure card is visible in viewport
                    await card.scroll_into_view_if_needed()
                    await page.wait_for_timeout(200)
                    out_path = f"screenshots/diagrams/{page_id}_diag_{i+1}.png"
                    await card.screenshot(path=out_path)
                    total_captured += 1
                    print(f"    Saved: {out_path}")

        await browser.close()
        print(f"\nCompleted! Total diagrams captured: {total_captured}")

if __name__ == "__main__":
    asyncio.run(capture_diagrams())
