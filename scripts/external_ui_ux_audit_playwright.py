#!/usr/bin/env python3
"""
scripts/external_ui_ux_audit_playwright.py
--------------------------------------------------------------------------------
Comprehensive External UI/UX Audit Playwright Suite for AREOS / Citeable.
Demonstrates every possible Playwright screenshot and context configuration
for both Desktop and Mobile layouts across all application pages and states.

Usage:
    python scripts/external_ui_ux_audit_playwright.py
    python scripts/external_ui_ux_audit_playwright.py --base-url http://127.0.0.1:8000 --output-dir screenshots/ui_ux_audit
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Locator

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_OUTPUT_DIR = "screenshots/ui_ux_audit"
DEFAULT_ADMIN_TOKEN = "dev-token"
DEFAULT_RUN_ID = "RUN-20260810-0B5C06"

# Manifest of captured screenshots
audit_manifest: List[Dict[str, Any]] = []

def record_capture(
    path: str,
    category: str,
    layout: str,
    page_name: str,
    state_description: str,
    playwright_configs: Dict[str, Any],
    audit_focus: str,
):
    """Log screenshot to manifest."""
    rel_path = os.path.relpath(path, os.getcwd())
    audit_manifest.append({
        "file": rel_path.replace("\\", "/"),
        "category": category,
        "layout": layout,
        "page": page_name,
        "state_description": state_description,
        "playwright_configs": playwright_configs,
        "audit_focus": audit_focus,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    print(f"  [+] Captured: {rel_path} ({category} | {layout})")


async def init_page_storage(page: Page, token: str, analyst_id: str = "Alice S.", dismiss_tour: bool = True):
    """Seed localStorage and sessionStorage for authenticated & stable UI states."""
    await page.evaluate(f"""() => {{
        localStorage.setItem('areos_analyst_id', '{analyst_id}');
        sessionStorage.setItem('areos_api_token', '{token}');
        localStorage.setItem('areos_byok_vault', JSON.stringify({{
            'OpenAI': {{ 'key': 'sk-test-live-mock-01928374', 'status': 'valid' }},
            'Anthropic': {{ 'key': 'sk-ant-test-mock-99887766', 'status': 'valid' }}
        }}));
        if ({str(dismiss_tour).lower()}) {{
            localStorage.setItem('citeable_help_seen', 'true');
            localStorage.setItem('areos_help_tour_dismissed', 'true');
        }} else {{
            localStorage.removeItem('citeable_help_seen');
            localStorage.removeItem('areos_help_tour_dismissed');
        }}
    }}""")


async def safe_goto(page: Page, url: str, wait_selector: Optional[str] = None, timeout: int = 15000):
    """Navigate to URL with fallback and wait for fonts and optional selector."""
    try:
        await page.goto(url, wait_until="networkidle", timeout=timeout)
    except Exception:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        except Exception as e:
            print(f"      [!] Warning: Navigation to {url} encountered: {e}")
    
    # Wait for document fonts to eliminate font-swap layout shift in snapshots
    try:
        await page.evaluate("() => document.fonts.ready")
    except Exception:
        pass

    if wait_selector:
        try:
            await page.wait_for_selector(wait_selector, timeout=4000)
        except Exception:
            pass
    await page.wait_for_timeout(400)


# ==============================================================================
# AUDIT SUITE EXECUTION
# ==============================================================================

async def run_desktop_audit(browser: Browser, base_url: str, output_dir: str, token: str, run_id: str):
    """Desktop layout audit (1440x900 standard Retina and 1920x1080 full HD)."""
    print("\n" + "="*70)
    print(">>> EXECUTING DESKTOP AUDIT SUITE (1440x900 @ 2x DPR)")
    print("="*70)

    out_desktop = Path(output_dir) / "desktop"
    out_desktop.mkdir(parents=True, exist_ok=True)

    # 1. Standard Desktop Context (Retina HiDPI, Light/Default)
    context = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=2,  # Retina 2x scale
        color_scheme="light",
        locale="en-US",
        timezone_id="America/New_York",
    )
    page = await context.new_page()
    await safe_goto(page, f"{base_url}/")
    await init_page_storage(page, token=token)
    await page.reload()
    await page.wait_for_timeout(500)

    # --- Page 01: Audit Studio - Landing & Search Hero ---
    await safe_goto(page, f"{base_url}/")
    path = str(out_desktop / "01_studio_landing_viewport.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
        caret="hide",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Viewport",
        page_name="index.html (Audit Studio)",
        state_description="Landing hero with domain search input, prompt selector, and KPI stats",
        playwright_configs={"full_page": False, "animations": "disabled", "caret": "hide", "device_scale_factor": 2},
        audit_focus="Above-the-fold CTA prominence, input readability, branding balance, and primary action affordance",
    )

    path_full = str(out_desktop / "01_studio_landing_fullpage.png")
    await page.screenshot(
        path=path_full,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path_full,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="index.html (Audit Studio)",
        state_description="Full vertical scroll of landing page including pipeline stages and baseline footer",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Full scroll rhythm, vertical breathing room, footer positioning, and whitespace balance",
    )

    # --- Page 02: Audit Studio - Form Validation Error State ---
    domain_input = page.locator("#domain-input")
    if await domain_input.count() > 0:
        await domain_input.fill("invalid..domain-test#error")
        await domain_input.press("Enter")
        await page.wait_for_timeout(400)
    path = str(out_desktop / "02_studio_domain_validation_error.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
        caret="initial",
    )
    record_capture(
        path=path,
        category="Desktop Interaction",
        layout="Desktop 1440x900 Viewport",
        page_name="index.html (Audit Studio)",
        state_description="Inline regex domain validation error feedback and active input border highlight",
        playwright_configs={"full_page": False, "animations": "disabled", "caret": "initial"},
        audit_focus="Clarity of error notification, accessibility of red/warning cues (WCAG 1.4.1 non-color reliance)",
    )

    # --- Page 03: Audit Studio - Live Scan Telemetry Monitor ---
    await page.evaluate("""() => {
        const mon = document.getElementById('execution-monitor');
        if (mon) {
            mon.style.display = 'block';
            const stages = mon.querySelectorAll('.pipeline-stage');
            if (stages.length > 2) {
                stages[0].classList.add('completed');
                stages[1].classList.add('active');
            }
        }
    }""")
    await page.wait_for_timeout(400)
    path = str(out_desktop / "03_studio_live_scan_telemetry.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Interaction",
        layout="Desktop 1440x900 Viewport",
        page_name="index.html (Audit Studio)",
        state_description="Real-time multi-phase diagnostic scan monitor with animated progress states",
        playwright_configs={"full_page": False, "animations": "disabled"},
        audit_focus="Cognitive anxiety reduction during long tasks, phase progress visibility, font legibility in terminal log",
    )

    # --- Page 04: Audit Studio - Score Summary Dashboard ---
    await safe_goto(page, f"{base_url}/?tab=tab-results&run_id={run_id}")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "04_studio_score_results_dashboard.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="index.html (?tab=tab-results)",
        state_description="Overall score gauge, 5-layer diagnostic breakdown (AP-01 to AP-05), and historical delta card",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Information density, color-coded score status badges (Pass/Warn/Fail), metric contrast, export button CTAs",
    )

    # --- Page 05: Audit Studio - Guided Review Hub (Verdict Cards) ---
    await safe_goto(page, f"{base_url}/?tab=tab-wizard&run_id={run_id}")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "05_studio_guided_review_cards.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="index.html (?tab=tab-wizard)",
        state_description="Interactive human-in-the-loop audit cards with verdict selection buttons (Pass/Warn/Fail)",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Tri-state verdict button contrast, keyboard tab order, expandable details drawer affordance",
    )

    # --- Page 06: Audit Studio - Synthesis Executive Narrative ---
    await safe_goto(page, f"{base_url}/?tab=tab-synthesis&run_id={run_id}")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "06_studio_synthesis_narrative.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="index.html (?tab=tab-synthesis)",
        state_description="Comprehensive generative synthesis narrative report, markdown rendering, and recommendations",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Typography readability, long-form editorial hierarchy, export formatting, bullet point styling",
    )

    # --- Page 07: Claims Browser Knowledge Base ---
    await safe_goto(page, f"{base_url}/claims_browser.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "07_claims_browser_page.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="claims_browser.html",
        state_description="Empirical claims registry with layer filters, search bar, and claim relationship cards",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Filter bar responsiveness, table/card layout readability, claim ID badges, citation link styling",
    )

    # --- Page 08: Knowledge Explorer Visual Graph ---
    await safe_goto(page, f"{base_url}/knowledge_explorer.html")
    await page.wait_for_timeout(1000)
    path = str(out_desktop / "08_knowledge_explorer_graph.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Viewport",
        page_name="knowledge_explorer.html",
        state_description="Interactive ontological graph matrix, node relationship canvas, and inspection sidebar",
        playwright_configs={"full_page": False, "animations": "disabled"},
        audit_focus="Canvas visual clarity, node contrast against background, zoom/pan tool controls usability",
    )

    # --- Page 09: Bring Your Own Key (BYOK) Security Vault ---
    await safe_goto(page, f"{base_url}/byok.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "09_byok_security_vault.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Viewport",
        page_name="byok.html",
        state_description="BYOK zero-retention encryption vault, provider key entry form, and active key table",
        playwright_configs={"full_page": False, "animations": "disabled"},
        audit_focus="Security reassurance messaging, password mask/reveal eye icon, key testing feedback badge",
    )

    # --- Page 10: Approvals Queue Console ---
    await safe_goto(page, f"{base_url}/approvals.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "10_approvals_console.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="approvals.html",
        state_description="Governance approvals console, pending sign-off queue, diff viewer, and audit log table",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Action button differentiation (Approve vs Reject), timestamp formatting, tabular data alignment",
    )

    # --- Page 11: Prompts Management Studio ---
    await safe_goto(page, f"{base_url}/prompts.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "11_prompts_editor.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="prompts.html",
        state_description="System prompt engineering interface, template parameter pills, and live preview drawer",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Monospace editor contrast, save indicator clarity, parameter token syntax highlighting",
    )

    # --- Page 12: Synthesis Prompts Workspace ---
    await safe_goto(page, f"{base_url}/synthesis_prompts.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "12_synthesis_prompts.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="synthesis_prompts.html",
        state_description="Synthesis pipeline model directives, reasoning chain templates, and output format specs",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Editor textarea sizing, version history dropdown, validation badges",
    )

    # --- Page 13: Technical Remediation Sequence Plan ---
    await safe_goto(page, f"{base_url}/remediation.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "13_remediation_plan.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="remediation.html",
        state_description="Prioritized remediation checklist, effort vs impact matrix, and code snippet exports",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Priority badge hierarchy (P0/P1/P2), code block copy button feedback, checkbox touch targets",
    )

    # --- Page 14: Case Study & Citation Velocity Explorer ---
    await safe_goto(page, f"{base_url}/case_study.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "14_case_study_benchmarks.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="case_study.html",
        state_description="Citation velocity graphs, competitor comparison bars, and methodology disclaimer",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Chart color readability, legend alignment, legal disclaimer callout legibility",
    )

    # --- Page 15: Outcome Verification Report ---
    await safe_goto(page, f"{base_url}/outcome.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "15_outcome_report.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="outcome.html",
        state_description="Post-audit verification summary, pass/fail status cards, and verification telemetry",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Pass/Fail stamp clarity, metrics visual grouping, breadcrumb navigation",
    )

    # --- Page 16: Manual Review Worksheet ---
    await safe_goto(page, f"{base_url}/manual_review.html")
    await page.wait_for_timeout(800)
    path = str(out_desktop / "16_manual_review_worksheet.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="manual_review.html",
        state_description="Analyst manual scoring worksheet with rubric guidelines and observational notes",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Form field spacing, rubric instruction typography, submit CTA positioning",
    )

    # --- Page 17: Documentation Hub - Public Scoring Guide ---
    await safe_goto(page, f"{base_url}/docs.html#page=scoring")
    await page.wait_for_timeout(1000)
    path = str(out_desktop / "17_docs_scoring_ontology.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="docs.html (#page=scoring)",
        state_description="Technical documentation on the 5-layer scoring model, formulas, and deduction tiers",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Documentation sidebar navigation, heading anchor hierarchy, code snippet syntax highlighting",
    )

    # --- Page 18: Documentation Hub - Gated Internal Engineering Docs ---
    await safe_goto(page, f"{base_url}/docs.html#page=int-architecture")
    await page.wait_for_timeout(1000)
    path = str(out_desktop / "18_docs_internal_architecture.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Standard",
        layout="Desktop 1440x900 Full-Page",
        page_name="docs.html (#page=int-architecture)",
        state_description="Internal engineering architecture, async task pipelines, and database topology with token auth",
        playwright_configs={"full_page": True, "animations": "disabled"},
        audit_focus="Security banner treatment, diagram placement, deep technical readability",
    )

    # --- Page 19: Fullscreen Interactive Diagram Canvas ---
    expand_btn = page.locator(".docs-diagram-expand-btn").first
    if await expand_btn.count() > 0:
        await expand_btn.click()
        await page.wait_for_timeout(600)
        path = str(out_desktop / "19_docs_diagram_fullscreen_canvas.png")
        await page.screenshot(
            path=path,
            full_page=False,
            animations="disabled",
        )
        record_capture(
            path=path,
            category="Desktop Modal",
            layout="Desktop 1440x900 Viewport",
            page_name="docs.html (Diagram Modal)",
            state_description="Expanded fullscreen diagram canvas viewer with pan/zoom toolbar and grid pattern",
            playwright_configs={"full_page": False, "animations": "disabled"},
            audit_focus="Canvas contrast, floating zoom controls accessibility, Escape key dismissal affordance",
        )
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

    # --- Global Overlay 20: Command Palette (Ctrl+K) ---
    await safe_goto(page, f"{base_url}/")
    await page.keyboard.press("Control+k")
    await page.wait_for_timeout(500)
    path = str(out_desktop / "20_global_cmdk_palette.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Modal",
        layout="Desktop 1440x900 Viewport",
        page_name="Global (Ctrl+K)",
        state_description="Global command palette search modal with instant page jumping and KB search results",
        playwright_configs={"full_page": False, "animations": "disabled"},
        audit_focus="Backdrop dimming intensity, input auto-focus, keyboard navigation indicator, search results grouping",
    )
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)

    # --- Global Overlay 21: Admin Auth Modal (Ctrl+Shift+A) ---
    await page.keyboard.press("Control+Shift+A")
    await page.wait_for_timeout(500)
    path = str(out_desktop / "21_global_admin_auth_modal.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Modal",
        layout="Desktop 1440x900 Viewport",
        page_name="Global (Ctrl+Shift+A)",
        state_description="Admin authentication token modal for unlocking gated engineering routes and prompts",
        playwright_configs={"full_page": False, "animations": "disabled"},
        audit_focus="Modal focus trapping, clear security messaging, password field styling, submit action button",
    )
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)

    # --- Global Overlay 22: First-Time Help Tour Modal ---
    await page.evaluate("""() => {
        if (window.helpTour && typeof window.helpTour.open === 'function') {
            window.helpTour.open();
        }
    }""")
    await page.wait_for_timeout(500)
    path = str(out_desktop / "22_global_help_tour_modal.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Desktop Modal",
        layout="Desktop 1440x900 Viewport",
        page_name="Global (Help Tour)",
        state_description="First-time user onboarding modal explaining AEO auditing and platform navigation",
        playwright_configs={"full_page": False, "animations": "disabled"},
        audit_focus="Onboarding cognitive load, step pagination dots, dismiss button tap target, visual illustration",
    )

    await context.close()


async def run_mobile_audit(browser: Browser, base_url: str, output_dir: str, token: str, run_id: str):
    """Mobile layout audit (390x844 iPhone 14/15 standard and 844x390 landscape)."""
    print("\n" + "="*70)
    print(">>> EXECUTING MOBILE AUDIT SUITE (390x844 @ 3x DPR with Touch Emulation)")
    print("="*70)

    out_mobile = Path(output_dir) / "mobile"
    out_mobile.mkdir(parents=True, exist_ok=True)

    # 1. Standard Mobile Portrait Context
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=3,  # Modern smartphone Super Retina OLED
        is_mobile=True,
        has_touch=True,
        color_scheme="light",
        locale="en-US",
    )
    page = await context.new_page()
    await safe_goto(page, f"{base_url}/")
    await init_page_storage(page, token=token)
    await page.reload()
    await page.wait_for_timeout(500)

    # --- Mobile 01: Studio Landing (Portrait Viewport) ---
    path = str(out_mobile / "01_mobile_studio_landing_viewport.png")
    await page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Mobile Portrait",
        layout="Mobile 390x844 Viewport",
        page_name="index.html (Audit Studio)",
        state_description="Mobile initial viewport: topbar branding, hamburger toggle, and mobile hero CTA",
        playwright_configs={"full_page": False, "is_mobile": True, "has_touch": True, "device_scale_factor": 3},
        audit_focus="Single-column reflow, topbar compactness, touch target spacing for domain input and scan button",
    )

    # --- Mobile 02: Studio Landing (Full Scroll) ---
    path_full = str(out_mobile / "02_mobile_studio_landing_fullpage.png")
    await page.screenshot(
        path=path_full,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path_full,
        category="Mobile Portrait",
        layout="Mobile 390x844 Full-Page",
        page_name="index.html (Audit Studio)",
        state_description="Complete vertical reflow of landing page on mobile screen",
        playwright_configs={"full_page": True, "is_mobile": True, "has_touch": True},
        audit_focus="Excessive vertical scroll fatigue, card stacking order, horizontal scroll leakage (overflow-x check)",
    )

    # --- Mobile 03: Hamburger Drawer Open State ---
    menu_btn = page.locator("#mobile-menu-btn")
    if await menu_btn.count() > 0:
        await menu_btn.click()
        await page.wait_for_timeout(500)
        path = str(out_mobile / "03_mobile_hamburger_drawer_open.png")
        await page.screenshot(
            path=path,
            full_page=False,
            animations="disabled",
        )
        record_capture(
            path=path,
            category="Mobile Navigation",
            layout="Mobile 390x844 Viewport",
            page_name="Global Nav (Mobile Sidebar)",
            state_description="Slide-out drawer navigation menu showing all primary application links and BYOK status",
            playwright_configs={"full_page": False, "is_mobile": True},
            audit_focus="Drawer backdrop dismissal, touch target heights (>= 48px), icon clarity, active route highlighting",
        )
        backdrop = page.locator("#sidebar-backdrop")
        if await backdrop.count() > 0:
            await backdrop.click(position={"x": 350, "y": 200})
            await page.wait_for_timeout(400)

    # --- Mobile 04: Results Score Dashboard ---
    await safe_goto(page, f"{base_url}/?tab=tab-results&run_id={run_id}")
    await page.wait_for_timeout(800)
    path = str(out_mobile / "04_mobile_score_dashboard_fullpage.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Mobile Portrait",
        layout="Mobile 390x844 Full-Page",
        page_name="index.html (?tab=tab-results)",
        state_description="Mobile score gauge card, stacked layer deduction pills, and export buttons",
        playwright_configs={"full_page": True, "is_mobile": True},
        audit_focus="Gauge SVG responsiveness, score visibility on small screens, button wrapping without text truncation",
    )

    # --- Mobile 05: Guided Review Cards (Mobile Touch Verifying) ---
    await safe_goto(page, f"{base_url}/?tab=tab-wizard&run_id={run_id}")
    await page.wait_for_timeout(800)
    path = str(out_mobile / "05_mobile_guided_review_cards.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Mobile Portrait",
        layout="Mobile 390x844 Full-Page",
        page_name="index.html (?tab=tab-wizard)",
        state_description="Card-by-card audit flow stacked vertically with responsive verdict button rows",
        playwright_configs={"full_page": True, "is_mobile": True},
        audit_focus="Thumb zone ergonomics for Pass/Warn/Fail buttons, expandable drawer ease on mobile",
    )

    # --- Mobile 06: BYOK Vault (Mobile Dialog) ---
    await safe_goto(page, f"{base_url}/byok.html")
    await page.wait_for_timeout(800)
    path = str(out_mobile / "06_mobile_byok_vault.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Mobile Portrait",
        layout="Mobile 390x844 Full-Page",
        page_name="byok.html",
        state_description="BYOK mobile configuration screen with compact inputs and credential table",
        playwright_configs={"full_page": True, "is_mobile": True},
        audit_focus="Mobile keyboard friendly inputs, table horizontal scrolling or stacking, eye icon hit area",
    )

    # --- Mobile 07: Claims Browser on Small Screen ---
    await safe_goto(page, f"{base_url}/claims_browser.html")
    await page.wait_for_timeout(800)
    path = str(out_mobile / "07_mobile_claims_browser.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Mobile Portrait",
        layout="Mobile 390x844 Full-Page",
        page_name="claims_browser.html",
        state_description="Claims table reflowed into mobile-friendly stacked list",
        playwright_configs={"full_page": True, "is_mobile": True},
        audit_focus="Text truncation versus readability, filter chips wrap behavior, search input responsiveness",
    )

    # --- Mobile 08: Documentation Hub on Mobile ---
    await safe_goto(page, f"{base_url}/docs.html#page=scoring")
    await page.wait_for_timeout(800)
    path = str(out_mobile / "08_mobile_docs_scoring.png")
    await page.screenshot(
        path=path,
        full_page=True,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Mobile Portrait",
        layout="Mobile 390x844 Full-Page",
        page_name="docs.html (#page=scoring)",
        state_description="Documentation layout on mobile with collapsible sidebar and inline code blocks",
        playwright_configs={"full_page": True, "is_mobile": True},
        audit_focus="Code block overflow scrolling, table of contents access on mobile, font legibility",
    )

    # --- Mobile 09: Landscape Orientation (844x390) ---
    landscape_page = await context.new_page()
    await landscape_page.set_viewport_size({"width": 844, "height": 390})
    await safe_goto(landscape_page, f"{base_url}/?tab=tab-results&run_id={run_id}")
    await landscape_page.wait_for_timeout(600)
    path = str(out_mobile / "09_mobile_landscape_results_viewport.png")
    await landscape_page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Mobile Landscape",
        layout="Mobile 844x390 Landscape Viewport",
        page_name="index.html (?tab=tab-results)",
        state_description="Results dashboard rendered in horizontal phone orientation",
        playwright_configs={"full_page": False, "viewport": {"width": 844, "height": 390}},
        audit_focus="Vertical compression handling, fixed header height crowding, sticky element overlap issues",
    )
    await landscape_page.close()

    await context.close()


async def run_specialized_configs_audit(browser: Browser, base_url: str, output_dir: str, token: str, run_id: str):
    """
    Exhibits every advanced Playwright screenshot and emulation configuration:
      - Dark Mode (color_scheme='dark')
      - Forced Colors / Windows High Contrast (forced_colors='active')
      - Reduced Motion (reduced_motion='reduce')
      - Element Masking (mask=[locators], mask_color='#FF00FF')
      - Region Clipping (clip={'x', 'y', 'width', 'height'})
      - Transparent Background (omit_background=True)
      - Lossy JPEG Compression (type='jpeg', quality=75)
      - Element-Only Component Screenshot (locator.screenshot())
      - Custom Style Injection (style='...')
      - Scale comparison (scale='css' vs scale='device')
    """
    print("\n" + "="*70)
    print(">>> EXECUTING ADVANCED PLAYWRIGHT CONFIGS & ACCESSIBILITY AUDIT")
    print("="*70)

    out_adv = Path(output_dir) / "specialized_configs"
    out_adv.mkdir(parents=True, exist_ok=True)

    # 1. Light Hybrid Scheme Baseline (Task 6 Option B: Dark Mode out-of-scope)
    light_ctx = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        color_scheme="light",
    )
    light_page = await light_ctx.new_page()
    await safe_goto(light_page, f"{base_url}/?tab=tab-results&run_id={run_id}")
    await init_page_storage(light_page, token=token)
    await light_page.reload()
    await light_page.wait_for_timeout(600)
    path = str(out_adv / "config_01_light_scheme_contrast.png")
    await light_page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="Desktop Light Scheme",
        page_name="index.html (?tab=tab-results)",
        state_description="Light Hybrid theme baseline validation (Task 6 Option B)",
        playwright_configs={"color_scheme": "light", "animations": "disabled"},
        audit_focus="WCAG AA 4.5:1 text-on-surface contrast compliance in calibrated light design system",
    )
    await light_ctx.close()

    # 2. Forced Colors (High Contrast Accessibility Mode)
    hc_ctx = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        forced_colors="active",
    )
    hc_page = await hc_ctx.new_page()
    await safe_goto(hc_page, f"{base_url}/")
    await init_page_storage(hc_page, token=token)
    await hc_page.reload()
    await hc_page.wait_for_timeout(600)
    path = str(out_adv / "config_02_forced_colors_high_contrast.png")
    await hc_page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="High Contrast (Accessibility)",
        page_name="index.html (Audit Studio)",
        state_description="Windows High Contrast Mode simulation via forced_colors='active'",
        playwright_configs={"forced_colors": "active"},
        audit_focus="Verification that interactive borders, buttons, and focus outlines remain perceivable",
    )
    await hc_ctx.close()

    # 3. Reduced Motion Emulation
    rm_ctx = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        reduced_motion="reduce",
    )
    rm_page = await rm_ctx.new_page()
    await safe_goto(rm_page, f"{base_url}/")
    path = str(out_adv / "config_03_reduced_motion_emulation.png")
    await rm_page.screenshot(
        path=path,
        full_page=False,
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="Reduced Motion",
        page_name="index.html (Audit Studio)",
        state_description="Vestibular motion sensitivity simulation via prefers-reduced-motion: reduce",
        playwright_configs={"reduced_motion": "reduce", "animations": "disabled"},
        audit_focus="Ensures pulsing animations and sliding carousels respect user accessibility preferences",
    )
    await rm_ctx.close()

    # Standard context for granular screenshot options
    std_ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await std_ctx.new_page()
    await safe_goto(page, f"{base_url}/?tab=tab-results&run_id={run_id}")
    await init_page_storage(page, token=token)
    await page.reload()
    await page.wait_for_timeout(600)

    # 4. Element Masking (mask=[locators], mask_color="#FF00FF")
    # Masks dynamic elements (e.g. run ID header or date stamps) for regression stability
    mask_targets = []
    run_label = page.locator("#res-funnel-label")
    if await run_label.count() > 0:
        mask_targets.append(run_label)
    
    path = str(out_adv / "config_04_element_masking_pink.png")
    await page.screenshot(
        path=path,
        full_page=False,
        mask=mask_targets,
        mask_color="#FF00FF",
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="Desktop 1440x900",
        page_name="index.html (?tab=tab-results)",
        state_description="Masked volatile timestamps / session identifiers using mask=[locators] and mask_color",
        playwright_configs={"mask": "[#res-funnel-label]", "mask_color": "#FF00FF"},
        audit_focus="Stabilizes visual regression testing by masking dynamic or sensitive data",
    )

    # 5. Region / Bounding Box Clipping (clip={'x', 'y', 'width', 'height'})
    path = str(out_adv / "config_05_region_clipped_header_kpis.png")
    await page.screenshot(
        path=path,
        clip={"x": 260, "y": 20, "width": 1140, "height": 380},
        animations="disabled",
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="Clipped Rectangle",
        page_name="index.html (?tab=tab-results)",
        state_description="Isolated rectangular clip of the results header banner and score card",
        playwright_configs={"clip": {"x": 260, "y": 20, "width": 1140, "height": 380}},
        audit_focus="Enables targeted inspection of specific viewport coordinates without full DOM overhead",
    )

    # 6. Component-Only Isolated Screenshot (locator.screenshot())
    studio_results = page.locator("#studio-results")
    if await studio_results.count() > 0:
        path = str(out_adv / "config_06_component_isolated_locator.png")
        await studio_results.screenshot(
            path=path,
            animations="disabled",
        )
        record_capture(
            path=path,
            category="Advanced Config",
            layout="Isolated Element",
            page_name="index.html (#studio-results)",
            state_description="Direct locator-level screenshot of the entire results component box",
            playwright_configs={"locator": "#studio-results", "method": "locator.screenshot()"},
            audit_focus="Component design system cataloging and atomic UI testing in isolation",
        )

    # 7. Transparent Background (omit_background=True)
    export_btn = page.locator("#btn-export-report")
    if await export_btn.count() > 0:
        path = str(out_adv / "config_07_transparent_background_button.png")
        try:
            await export_btn.screenshot(
                path=path,
                omit_background=True,
                timeout=5000,
            )
            record_capture(
                path=path,
                category="Advanced Config",
                layout="Isolated Transparent Component",
                page_name="index.html (#btn-export-report)",
                state_description="Component screenshot rendered with transparent alpha channel via omit_background=True",
                playwright_configs={"omit_background": True},
                audit_focus="Validating button border radius anti-aliasing and drop shadows on arbitrary backgrounds",
            )
        except Exception as e:
            print(f"      [!] Warning: config_07 screenshot skipped: {e}")

    # 8. Lossy JPEG Format with Quality Tuning (type='jpeg', quality=75)
    path = str(out_adv / "config_08_lossy_jpeg_quality75.jpeg")
    await page.screenshot(
        path=path,
        type="jpeg",
        quality=75,
        full_page=False,
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="Compressed JPEG",
        page_name="index.html (?tab=tab-results)",
        state_description="JPEG capture at quality=75 for high-efficiency reporting and lightweight asset delivery",
        playwright_configs={"type": "jpeg", "quality": 75},
        audit_focus="Demonstrates bandwidth vs visual clarity tradeoff for large automated audit runs",
    )

    # 9. Custom CSS Style Injection Prior to Capture
    # Injects red accessibility outlines around all interactive buttons and inputs
    audit_style = """
        button, a, input, select, textarea {
            outline: 2px dashed #06b6d4 !important;
            outline-offset: 2px !important;
        }
    """
    path = str(out_adv / "config_09_injected_style_focus_audit.png")
    await page.screenshot(
        path=path,
        full_page=False,
        style=audit_style,
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="Injected CSS Style",
        page_name="index.html (Focus Outlines)",
        state_description="Custom CSS injected at capture time highlighting all interactable hit areas",
        playwright_configs={"style": "outline: 2px dashed #06b6d4 !important"},
        audit_focus="Instant visual verification of interactive element boundaries, tap targets, and hit areas",
    )

    # 10. CSS Grid Scale vs Device Hardware Scale
    # Demonstrates scale='css'
    path = str(out_adv / "config_10_scale_css_grid.png")
    await page.screenshot(
        path=path,
        full_page=False,
        scale="css",
    )
    record_capture(
        path=path,
        category="Advanced Config",
        layout="Scale CSS (1:1 Layout Pixels)",
        page_name="index.html",
        state_description="Screenshot scaled 1:1 with CSS layout dimensions (scale='css')",
        playwright_configs={"scale": "css"},
        audit_focus="Allows exact pixel ruler layout inspection regardless of display hardware density",
    )

    await std_ctx.close()


async def main():
    parser = argparse.ArgumentParser(description="External Playwright UI/UX Audit Screenshot Suite")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Target application base URL")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Destination directory for screenshots")
    parser.add_argument("--token", default=DEFAULT_ADMIN_TOKEN, help="Admin token for gated routes")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID, help="Audit run ID for populated dashboard state")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    args = parser.parse_args()

    print("\n" + "#"*70)
    print("  AREOS / CITEABLE EXTERNAL PLAYWRIGHT UI/UX AUDIT ENGINE")
    print(f"  Target:     {args.base_url}")
    print(f"  Output Dir: {args.output_dir}")
    print(f"  Run ID:     {args.run_id}")
    print("#"*70)

    os.makedirs(args.output_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        
        # 1. Desktop Audit (Full spectrum)
        await run_desktop_audit(browser, args.base_url, args.output_dir, args.token, args.run_id)

        # 2. Mobile Audit (Portrait, Landscape, Touch, Drawer)
        await run_mobile_audit(browser, args.base_url, args.output_dir, args.token, args.run_id)

        # 3. Specialized Playwright Configs (Dark mode, forced colors, masks, clips, types)
        await run_specialized_configs_audit(browser, args.base_url, args.output_dir, args.token, args.run_id)

        await browser.close()

    # Save manifest
    manifest_path = Path(args.output_dir) / "audit_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(audit_manifest, f, indent=2)

    print("\n" + "="*70)
    print(f"[SUCCESS] UI/UX Audit Complete!")
    print(f"Total screenshots captured: {len(audit_manifest)}")
    print(f"Manifest written to:        {manifest_path}")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
