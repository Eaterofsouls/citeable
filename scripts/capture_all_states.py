import asyncio
import os
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"
SCREENSHOT_DIR = "screenshots"

async def setup_page(context):
    page = await context.new_page()
    await page.goto(f"{BASE_URL}/")
    await page.evaluate("""() => {
        localStorage.setItem('citeable_help_seen', 'true');
        localStorage.setItem('areos_analyst_id', 'ANALYST_PRIME');
        sessionStorage.setItem('areos_api_token', 'dev-token');
    }""")
    await page.reload()
    await page.wait_for_timeout(500)
    return page

async def capture():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,  # Retina resolution
        )
        
        page = await setup_page(context)
        
        # 1. Landing Tour & Studio Main
        print("Capturing 01_landing_tour...")
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_landing_tour.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_01_tour.png")

        # 2. Domain Validation Error
        print("Capturing 02_audit_input_validation...")
        await page.fill("#domain-input", "invalid..domain")
        # Trigger click or enter
        await page.press("#domain-input", "Enter")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_audit_input_validation.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_r2_04_domain_validation.png")

        # 3. Live Scan Execution Telemetry
        print("Capturing 03_live_scan_telemetry...")
        await page.fill("#domain-input", "madmarketers.in")
        await page.evaluate("() => document.getElementById('execution-monitor').style.display = 'block'")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_live_scan_telemetry.png")

        # 4. Results Dashboard
        print("Capturing 04_score_summary_dashboard...")
        await page.goto(f"{BASE_URL}/?tab=tab-results&run_id=RUN-20260902-657FCD")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/04_score_summary_dashboard.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_03_results.png")

        # 5. Guided Review Cards
        print("Capturing 05_guided_review_cards...")
        await page.goto(f"{BASE_URL}/?tab=tab-wizard&run_id=RUN-20260902-657FCD")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/05_guided_review_cards.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_04_wizard.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_r2_01_wizard_persist.png")

        # 6. Synthesis Final Report
        print("Capturing 06_synthesis_narrative...")
        await page.goto(f"{BASE_URL}/?tab=tab-synthesis&run_id=RUN-20260902-657FCD")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/06_synthesis_narrative.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_05_synthesis.png")

        # 7. Claims Browser
        print("Capturing 07_claims_browser_drawer...")
        await page.goto(f"{BASE_URL}/claims_browser.html")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/07_claims_browser_drawer.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_06_kb.png")

        # 8. Knowledge Explorer Graph
        print("Capturing 08_knowledge_explorer...")
        await page.goto(f"{BASE_URL}/knowledge_explorer.html")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/08_knowledge_explorer.png")

        # 9. BYOK Vault Modal & Page
        print("Capturing 09_byok_vault_modal...")
        await page.goto(f"{BASE_URL}/byok.html")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/09_byok_vault_modal.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_02_byok.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_r2_02_byok_error.png")

        # 10. Approvals Console (with admin auth)
        print("Capturing 10_approvals_console...")
        await page.goto(f"{BASE_URL}/approvals.html")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/10_approvals_console.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_r2_06_conflict.png")

        # 11. Prompts Editor
        print("Capturing 11_prompts_editor...")
        await page.goto(f"{BASE_URL}/prompts.html")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/11_prompts_editor.png")

        # 12. Remediation Plan
        print("Capturing 12_remediation_plan...")
        await page.goto(f"{BASE_URL}/remediation.html")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/12_remediation_plan.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_r2_05_export.png")

        # 13. Case Study & Outcome
        print("Capturing 13_case_study_outcome...")
        await page.goto(f"{BASE_URL}/case_study.html")
        await page.wait_for_timeout(800)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/13_case_study_outcome.png")

        # 14. Documentation Hub (External Docs)
        print("Capturing 14_docs_external_hub...")
        await page.goto(f"{BASE_URL}/docs.html#page=scoring")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/14_docs_external_hub.png")

        # 15. Documentation Hub (Internal Gated Docs)
        print("Capturing 15_docs_internal_gated...")
        await page.goto(f"{BASE_URL}/docs.html#page=int-architecture")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/15_docs_internal_gated.png")

        # 16. Command Palette (Cmd+K)
        print("Capturing 16_cmdk_palette_search...")
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_timeout(400)
        await page.keyboard.press("Control+k")
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/16_cmdk_palette_search.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_07_cmdk.png")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/alex_r2_03_cmdk_concurrent.png")

        # 17. Admin Auth Modal (Cmd+Shift+A)
        print("Capturing 17_admin_auth_modal...")
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_timeout(400)
        await page.keyboard.press("Control+Shift+A")
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/17_admin_auth_modal.png")

        # 18. Help Tour Modal
        print("Capturing 18_help_tour_modal...")
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_timeout(400)
        await page.evaluate("() => window.helpTour && window.helpTour.open()")
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/18_help_tour_modal.png")

        # 19. Mobile Viewport Responsive View
        print("Capturing 19_mobile_responsive_view...")
        mobile_page = await context.new_page()
        await mobile_page.set_viewport_size({"width": 390, "height": 844})
        await mobile_page.goto(f"{BASE_URL}/")
        await mobile_page.evaluate("""() => {
            localStorage.setItem('citeable_help_seen', 'true');
            localStorage.setItem('areos_analyst_id', 'ANALYST_PRIME');
        }""")
        await mobile_page.reload()
        await mobile_page.wait_for_timeout(800)
        await mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/19_mobile_responsive_view.png")
        await mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/alex_08_mobile.png")
        await mobile_page.close()

        await browser.close()
        print("All 19 states and features captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture())
