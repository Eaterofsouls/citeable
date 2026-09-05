import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = await context.new_page()
        
        # 1. Open documentation page
        print("Navigating to docs page...")
        await page.goto("http://127.0.0.1:8000/docs.html#page=scoring")
        await page.wait_for_timeout(1500)
        
        # Capture diagram card with the new Expand button
        print("Capturing diagram card in page...")
        await page.screenshot(path="screenshots/diagram_card_in_page.png")
        
        # 2. Click the expand button on the first diagram
        print("Clicking expand button...")
        expand_btn = page.locator(".docs-diagram-expand-btn").first
        await expand_btn.click()
        await page.wait_for_timeout(600)
        
        # Capture the fullscreen interactive canvas modal
        print("Capturing fullscreen modal...")
        await page.screenshot(path="screenshots/diagram_fullscreen_open.png")
        
        # 3. Test Zoom In button
        print("Zooming in via HUD...")
        await page.click("#docs-hud-zoom-in")
        await page.click("#docs-hud-zoom-in")
        await page.wait_for_timeout(300)
        await page.screenshot(path="screenshots/diagram_fullscreen_zoomed.png")
        
        # 4. Test Panning (Drag)
        print("Testing pan drag...")
        viewport = page.locator("#docs-fullscreen-viewport")
        box = await viewport.bounding_box()
        if box:
            await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            await page.mouse.down()
            await page.mouse.move(box["x"] + box["width"]/2 - 150, box["y"] + box["height"]/2 - 100)
            await page.mouse.up()
            await page.wait_for_timeout(300)
            await page.screenshot(path="screenshots/diagram_fullscreen_panned.png")
            
        # 5. Test Fit button
        print("Testing fit to screen...")
        await page.click("#docs-hud-fit")
        await page.wait_for_timeout(300)
        await page.screenshot(path="screenshots/diagram_fullscreen_fit.png")
        
        # 6. Test Esc key to close
        print("Testing Esc key...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(400)
        await page.screenshot(path="screenshots/diagram_fullscreen_closed.png")
        
        await browser.close()
        print("Verification complete! All screenshots captured.")

if __name__ == "__main__":
    asyncio.run(verify())
