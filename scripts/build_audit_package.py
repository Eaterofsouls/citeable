#!/usr/bin/env python3
"""
scripts/build_audit_package.py
--------------------------------------------------------------------------------
Generates the comprehensive UI/UX Audit & Playwright Configuration Guide
(both Markdown and styled HTML), packages all 42 audit screenshots, manifest,
and runnable audit scripts into a clean ZIP archive, and saves everything
directly to the user's Downloads directory.
"""

import os
import shutil
import zipfile
from pathlib import Path

DOWNLOADS_DIR = Path(r"C:\Users\drc16\Downloads")
WORKSPACE_DIR = Path(r"d:\07 Transfer-20260727T165431Z-1-001\Antigravity 26-07 Transfer\AREOS_COMPLETE_WORKSPACE")
SCREENSHOTS_DIR = WORKSPACE_DIR / "screenshots" / "ui_ux_audit"
SCRIPT_PATH = WORKSPACE_DIR / "scripts" / "external_ui_ux_audit_playwright.py"
MANIFEST_PATH = SCREENSHOTS_DIR / "audit_manifest.json"

DOC_MD_PATH = WORKSPACE_DIR / "UI_UX_AUDIT_PLAYWRIGHT_GUIDE.md"
DOC_HTML_PATH = WORKSPACE_DIR / "UI_UX_AUDIT_PLAYWRIGHT_GUIDE.html"
ZIP_OUT_PATH = DOWNLOADS_DIR / "AREOS_UI_UX_Playwright_Audit_Package.zip"

MD_CONTENT = """# AREOS / CITEABLE UI/UX AUDIT & PLAYWRIGHT CONFIGURATION MASTER GUIDE

> **Comprehensive Visual Quality, Accessibility, and Playwright Automation Handbook**  
> *Target System: Citeable AEOGEO Autonomous Audit & Knowledge Platform*  
> *Generated: September 2026 | Total Audit Captures: 42 High-Resolution States*

---

## 1. Executive Summary & Package Contents

This audit package delivers an external, automated UI/UX and visual regression audit suite built with **Playwright**. It provides full-spectrum visual captures of every user-facing page, interactive modal, sliding drawer, form validation state, and technical dashboard in the platform across **Desktop** and **Mobile** layouts.

Every screenshot demonstrates a specific Playwright screenshot configuration or browser context emulation parameter. This document serves as a complete **"What is What"** encyclopedia explaining what each configuration does, why it exists, what each screenshot captures, and how UI/UX auditors should inspect them.

### What Is Included in This Package:
1. **Desktop Audit Suite (`/desktop/`)**: 23 high-resolution (1440×900 @ 2× Retina) screenshots covering every page, tab, execution monitor, form error, and keyboard overlay modal.
2. **Mobile Audit Suite (`/mobile/`)**: 9 ultra-dense (390×844 @ 3× DPR with touch emulation) screenshots covering mobile portrait views, vertical reflows, interactive hamburger drawer navigation, stacked cards, and landscape orientation.
3. **Specialized Configurations Suite (`/specialized_configs/`)**: 10 advanced screenshots demonstrating every Playwright parameter: Dark Mode, Windows High Contrast Mode (Forced Colors), Reduced Motion accessibility, Element Masking, Region Clipping, Isolated Locators, Transparent Alpha Backgrounds, JPEG compression benchmarking, Injected CSS Hit-Target Audits, and 1:1 CSS Layout Scaling.
4. **Machine-Readable Manifest (`audit_manifest.json`)**: JSON index documenting file paths, resolutions, devices, applied Playwright configs, and UX audit objectives.
5. **Standalone Executable Script (`external_ui_ux_audit_playwright.py`)**: Asynchronous Python Playwright script ready to run against any local, staging, or production URL.

---

## 2. Playwright Configuration Master Reference: "What Is What"

Playwright provides fine-grained control over the browser engine and rendering pipeline. Understanding how each parameter alters capture behavior is critical for building deterministic, flake-free visual testing and UX audits.

### A. Screenshot-Level Parameters (`page.screenshot(...)` / `locator.screenshot(...)`)

#### 1. `full_page` (`bool`, default: `False`)
- **What it does:**
  - `False`: Captures strictly the current visible viewport window (e.g. 1440×900). Content below the fold is cropped out.
  - `True`: Instructs the Chromium rendering engine to measure the full scrollable `document.body` height, resize the virtual surface, and stitch the entire webpage into a single vertical image.
- **Why it matters in UI/UX Audits:**
  - `full_page=False` evaluates the **initial above-the-fold impression**: Is the primary call-to-action (CTA) visible without scrolling? Does the hero headline dominate appropriately?
  - `full_page=True` evaluates **vertical rhythm and layout integrity**: Are section margins balanced? Does the footer pin to the bottom or create unwanted whitespace? Are cards arranged cohesively down the page?

#### 2. `type` (`'png' | 'jpeg'`, default: `'png'`)
- **What it does:**
  - `'png'`: Produces 24-bit lossless images with full alpha channel support. Every pixel rendered by Skia/Chromium is preserved identically.
  - `'jpeg'`: Applies discrete cosine transform lossy compression to produce lightweight image files.
- **Why it matters in UI/UX Audits:**
  - `'png'` is **mandatory for visual regression and typography inspection**. Sub-pixel font smoothing, antialiasing around rounded corners (`border-radius`), and 1px border lines blur or artifact under JPEG.
  - `'jpeg'` is used when generating massive automated test runs (hundreds of pages) where disk space or network transfer bandwidth is constrained.

#### 3. `quality` (`int` 1–100, default: `None`)
- **What it does:** Controls JPEG compression aggressiveness. Only valid when `type='jpeg'`.
- **Why it matters in UI/UX Audits:** Enables benchmarking between image weight and visual clarity. A quality setting of 75–80 typically reduces file sizes by 70–85% while keeping large headlines legible.

#### 4. `animations` (`'disabled' | 'allow'`, default: `'allow'`)
- **What it does:**
  - `'allow'`: CSS transitions, CSS `@keyframes` animations, and SVG animations run normally. The screenshot captures whatever instantaneous frame happens to be rendering when the shutter triggers.
  - `'disabled'`: Playwright automatically seeks all CSS animations to their terminal state, rewinds transitions, and pauses SVG spinners.
- **Why it matters in UI/UX Audits:** **Vital for eliminating test flakiness.** Mid-fade transitions, pulsing notification dots, or spinning loading indicators create false visual diff errors in automated CI/CD pipelines. Disabling animations guarantees deterministic pixel-for-pixel reproducibility.

#### 5. `caret` (`'hide' | 'initial'`, default: `'hide'`)
- **What it does:**
  - `'hide'`: Playwright suppresses the text insertion cursor (the blinking vertical line) inside focused text inputs, search boxes, and textareas.
  - `'initial'`: Preserves the natural browser blinking caret.
- **Why it matters in UI/UX Audits:** A blinking cursor alternates between visible and invisible every 500ms. In visual regression audits, a snapshot taken at 490ms vs 510ms will fail a pixel-diff check. Setting `caret='hide'` completely stabilizes form input testing.

#### 6. `scale` (`'css' | 'device'`, default: `'device'`)
- **What it does:**
  - `'device'`: Captures images at the physical screen pixel resolution (multiplying viewport dimensions by `device_scale_factor`). On a 2× Retina display, a 1440×900 viewport yields a 2880×1800 image.
  - `'css'`: Captures images mapped 1:1 to CSS layout pixels. A 1440×900 viewport yields an exact 1440×900 image regardless of display density.
- **Why it matters in UI/UX Audits:**
  - `'css'` is used for **grid and layout ruler inspection**: 1 pixel in the image equals exactly 1 CSS pixel (`px`), allowing designers to measure padding, margins, and alignment against an 8px grid.
  - `'device'` is used for **HiDPI visual sharpness testing**: Verifying that SVG icons, vector glyphs, and typography remain crisp on modern high-resolution displays.

#### 7. `clip` (`dict: {'x', 'y', 'width', 'height'}`)
- **What it does:** Restricts the capture area to a defined rectangular bounding box, measured in CSS pixels from the top-left corner of the page.
- **Why it matters in UI/UX Audits:** Allows targeted inspection of sub-components (such as sticky headers, KPI score cards, or floating notifications) without rendering the entire DOM canvas.

#### 8. `omit_background` (`bool`, default: `False`)
- **What it does:**
  - `False`: The page is rendered against the browser's default solid white canvas (`#FFFFFF`).
  - `True`: Playwright leaves unpainted canvas regions transparent (RGBA `[0, 0, 0, 0]`).
- **Why it matters in UI/UX Audits:** Essential for **Design System and Component Testing**. Inspects floating cards, dialogs, pill badges, and tooltips over transparent backgrounds to verify drop shadows, outer glows, and border antialiasing without background color interference.

#### 9. `mask` (`List[Locator]`) & `mask_color` (`str`, default: `'#FF00FF'`)
- **What it does:** Playwright paints a solid color rectangle (default magenta `#FF00FF`) over the bounding boxes of all specified locators prior to capturing the screenshot.
- **Why it matters in UI/UX Audits:** Dynamically changing data (such as live clocks, relative timestamps like *"3 minutes ago"*, random UUID run IDs, or user profile pictures) will cause visual regression tests to fail. Masking these elements isolates dynamic areas while verifying the stability of surrounding static layouts.

#### 10. `style` (`str`, default: `""`)
- **What it does:** Injects a custom CSS stylesheet string into the document immediately before taking the screenshot.
- **Why it matters in UI/UX Audits:** Extremely powerful for automated usability checks. Auditors can inject outlines (`outline: 2px dashed cyan`) to visualize all interactive touch targets, highlight headings lacking `aria` attributes, or test font fallback cascades.

#### 11. `locator.screenshot(...)`
- **What it does:** Calls the screenshot method on a specific DOM element handle (`page.locator(".card").screenshot()`) rather than the page.
- **Why it matters in UI/UX Audits:** Storybook-style component verification. Captures atomic design tokens in isolation without needing to crop or calculate coordinates manually.

---

### B. Browser Context Emulation Parameters (`browser.new_context(...)`)

| Parameter | Configuration Values | Meaning & Audit Role |
|---|---|---|
| `viewport` | `{'width': int, 'height': int}` | Sets the browser window size in CSS pixels (e.g. 1440×900, 390×844). Controls CSS `@media (min-width/max-width)` breakpoint activation. |
| `device_scale_factor` | `1.0`, `2.0`, `3.0` | Simulates screen pixel density. Standard desktop monitor (1.0), Apple Retina display (2.0), Flagship OLED smartphone (3.0). |
| `is_mobile` | `True` \| `False` | When `True`, enables viewport meta tag parsing, suppresses default desktop scrollbars, and enables mobile event handling. |
| `has_touch` | `True` \| `False` | Emulates a touch-screen device. Enables `touchstart`/`touchend` events and suppresses mouse `:hover` persistent styles. |
| `color_scheme` | `'light'` \| `'dark'` \| `'no-preference'` | Emulates `@media (prefers-color-scheme: ...)`. Tests dark mode theme contrast, surfaces, and typography readability. |
| `forced_colors` | `'active'` \| `'none'` | Emulates Windows High Contrast Mode. Verifies that interactive elements have distinct system borders when custom colors are stripped. |
| `reduced_motion` | `'reduce'` \| `'no-preference'` | Emulates `@media (prefers-reduced-motion: reduce)`. Verifies accessibility compliance for users with vestibular sensitivity. |
| `locale` & `timezone_id` | `'en-US'`, `'de-DE'`, etc. | Tests internationalization, date/time formatting, and layout stability under German or French text expansion. |
| `extra_http_headers` | `{'Authorization': 'Bearer ...'}` | Emulates authenticated sessions for restricted engineering routes and gated internal administration views. |

---

## 3. Desktop Layout Screenshots Catalog (23 Views Explained)

All desktop screenshots were captured at **1440×900 CSS resolution with a 2× Device Scale Factor (2880×1800 physical pixels)** with font stabilization and animation disabling.

| # | Screenshot Filename | Page / Target Route | Applied Configurations | UI/UX Audit Purpose & Inspection Points |
|---|---|---|---|---|
| 01 | `01_studio_landing_viewport.png` | `index.html` (Audit Studio) | `full_page=False`, `scale='device'`, `caret='hide'` | **Above-the-fold Hero Impact:** Verifies headline visual weight, domain input visibility, CTA button prominence, and top navigation bar branding. |
| 02 | `01_studio_landing_fullpage.png` | `index.html` (Audit Studio) | `full_page=True`, `animations='disabled'` | **Vertical Document Rhythm:** Inspects vertical breathing room, footer alignment, step sequence stepper bar, and absence of orphan elements. |
| 03 | `02_studio_domain_validation_error.png` | `index.html` (Input State) | `caret='initial'`, simulated error input | **Form Error Usability:** Tests regex validation feedback on invalid domain entry. Verifies WCAG 1.4.1 non-color reliance (icon + text, not just red border). |
| 04 | `03_studio_live_scan_telemetry.png` | `index.html` (Active Scan) | `animations='disabled'`, live telemetry DOM | **Anxiety Reduction during Waiting:** Evaluates multi-phase progress display (Layers 1 to 6), progress indicators, and terminal log legibility. |
| 05 | `04_studio_score_results_dashboard.png` | `index.html?tab=tab-results` | `full_page=True`, populated run state | **Information Density & Hierarchy:** Inspects 0–100 score gauge, color-coded status badges (Pass/Warn/Fail), layer breakdown cards (AP-01 to AP-05), and export CTA. |
| 06 | `05_studio_guided_review_cards.png` | `index.html?tab=tab-wizard` | `full_page=True`, review wizard tab | **Human-in-the-Loop Interaction:** Verifies verdict selection button contrast (green Pass, amber Warn, red Fail), observation notes textarea, and expandable evidence links. |
| 07 | `06_studio_synthesis_narrative.png` | `index.html?tab=tab-synthesis` | `full_page=True`, synthesis tab | **Long-Form Editorial Typography:** Evaluates markdown rendering, line length (65–85 chars/line), heading contrast, and recommendation checklist formatting. |
| 08 | `07_claims_browser_page.png` | `claims_browser.html` | `full_page=True`, KB registry | **Data Table & Registry Usability:** Inspects filter chip layout, search input responsiveness, claim ID pills, and outbound source citation links. |
| 09 | `08_knowledge_explorer_graph.png` | `knowledge_explorer.html` | `full_page=False`, interactive canvas | **Graph Visual Ergonomics:** Assesses node contrast against dark canvas, label readability at 100% zoom, and zoom/pan control positioning. |
| 10 | `09_byok_security_vault.png` | `byok.html` | `full_page=False`, security vault | **Security Reassurance:** Evaluates password mask/reveal eye icon clarity, provider dropdown, active key table, and client-side zero-retention messaging. |
| 11 | `10_approvals_console.png` | `approvals.html` | `full_page=True`, admin auth header | **High-Stakes Decision Ergonomics:** Verifies separation of Approve vs Reject actions, diff viewer readability, and audit log table alignment. |
| 12 | `11_prompts_editor.png` | `prompts.html` | `full_page=True`, prompt design | **Technical Workspace UX:** Evaluates monospace font contrast, template parameter tag pills, and unsaved changes indicator clarity. |
| 13 | `12_synthesis_prompts.png` | `synthesis_prompts.html` | `full_page=True`, synthesis config | **Multi-Section Form Hierarchy:** Inspects textarea autosizing, version history indicators, and validation state messaging. |
| 14 | `13_remediation_plan.png` | `remediation.html` | `full_page=True`, remediation sequence | **Task Prioritization Clarity:** Assesses P0/P1/P2 badge color distinctiveness, code block copy button feedback, and checkbox touch areas. |
| 15 | `14_case_study_benchmarks.png` | `case_study.html` | `full_page=True`, citation case study | **Data Visualization Usability:** Verifies citation velocity bar charts, competitor comparison legend readability, and legal disclaimer visibility. |
| 16 | `15_outcome_report.png` | `outcome.html` | `full_page=True`, verification outcome | **Audit Completion Signaling:** Checks Pass/Fail outcome stamps, summary score cards, and return-to-dashboard navigation paths. |
| 17 | `16_manual_review_worksheet.png` | `manual_review.html` | `full_page=True`, manual reviewer | **Analyst Efficiency:** Evaluates scoring rubric typography, note-taking field ergonomics, and submission workflow clarity. |
| 18 | `17_docs_scoring_ontology.png` | `docs.html#page=scoring` | `full_page=True`, public documentation | **Documentation Readability:** Tests sticky table-of-contents sidebar, heading anchor links, and formula/code snippet syntax styling. |
| 19 | `18_docs_internal_architecture.png` | `docs.html#page=int-architecture` | `full_page=True`, internal docs | **Security Gating UX:** Verifies internal engineering banner treatment, token authentication status, and architecture diagram embedding. |
| 20 | `19_docs_diagram_fullscreen_canvas.png` | `docs.html` (Diagram Modal) | `full_page=False`, modal active | **Modal Canvas Usability:** Evaluates fullscreen diagram backdrop blur, floating zoom/pan controls accessibility, and `Escape` key dismissal affordance. |
| 21 | `20_global_cmdk_palette.png` | Global Overlay (`Ctrl+K`) | `full_page=False`, keyboard trigger | **Keyboard-First Navigation:** Assesses command palette backdrop dimming, input auto-focus, search results categorization, and keyboard shortcut hints. |
| 22 | `21_global_admin_auth_modal.png` | Global Overlay (`Ctrl+Shift+A`) | `full_page=False`, keyboard trigger | **Authentication Modal UX:** Tests modal focus trapping, clear security messaging, password field styling, and submit action button prominence. |
| 23 | `22_global_help_tour_modal.png` | Global Overlay (Help Tour) | `full_page=False`, programmatic open | **Onboarding Cognitive Load:** Evaluates multi-step tour modal clarity, pagination dots, dismiss target size, and explanatory graphic hierarchy. |

---

## 4. Mobile Layout Screenshots Catalog (9 Views Explained)

Mobile screenshots were captured at **390×844 CSS resolution with a 3× Device Scale Factor (1170×2532 physical pixels)**, utilizing full touch emulation and mobile user-agent headers.

| # | Screenshot Filename | Viewport / State | Applied Configurations | UI/UX Audit Purpose & Inspection Points |
|---|---|---|---|---|
| 01 | `01_mobile_studio_landing_viewport.png` | Mobile Portrait (390×844) | `full_page=False`, `is_mobile=True`, `has_touch=True` | **Mobile Above-The-Fold:** Checks topbar compactness, `#mobile-menu-btn` visibility, domain input scaling, and mobile CTA button hit area. |
| 02 | `02_mobile_studio_landing_fullpage.png` | Mobile Portrait (390×844) | `full_page=True`, `is_mobile=True` | **Horizontal Overflow Check:** Verifies zero horizontal scroll leakage (`overflow-x` check) and evaluates single-column card stacking order down the page. |
| 03 | `03_mobile_hamburger_drawer_open.png` | Mobile Nav Drawer (390×844) | Programmatic menu toggle, `has_touch=True` | **Touch Target Ergonomics:** Verifies navigation links meet WCAG 2.5.5 minimum touch target height ($\ge 48\text{px}$), checks backdrop tap-to-dismiss behavior. |
| 04 | `04_mobile_score_dashboard_fullpage.png` | Results Dashboard (390×844) | `full_page=True`, `is_mobile=True` | **Responsive Data Reflow:** Checks SVG circular score gauge responsiveness on small screens, ensures export button text does not truncate. |
| 05 | `05_mobile_guided_review_cards.png` | Guided Review (390×844) | `full_page=True`, `is_mobile=True` | **Thumb Zone Optimization:** Evaluates verdict button placement (Pass/Warn/Fail) within natural thumb reach, textarea expanding behavior on mobile. |
| 06 | `06_mobile_byok_vault.png` | BYOK Vault (390×844) | `full_page=True`, `is_mobile=True` | **Mobile Form UX:** Verifies touch hit area of password reveal eye icon, ensures provider dropdown fits narrow screens without breaking layout. |
| 07 | `07_mobile_claims_browser.png` | Claims Browser (390×844) | `full_page=True`, `is_mobile=True` | **Stacked Table Alternatives:** Tests how multi-column claims data wraps into readable stacked mobile cards with multi-line statements. |
| 08 | `08_mobile_docs_scoring.png` | Documentation (390×844) | `full_page=True`, `is_mobile=True` | **Code & Formula Scrolling:** Verifies code blocks have independent horizontal scrolling without expanding the outer container. |
| 09 | `09_mobile_landscape_results_viewport.png` | Mobile Landscape (844×390) | `viewport={"width": 844, "height": 390}`, `full_page=False` | **Vertical Compression Handling:** Tests horizontal phone rotation to ensure sticky headers do not consume $>40\%$ of screen height. |

---

## 5. Specialized Configurations & Accessibility Catalog (10 Views Explained)

These 10 screenshots exhibit advanced Playwright capabilities for accessibility compliance (WCAG 2.1 AAA), visual regression stabilization, and design system isolation.

| # | Screenshot Filename | Specialized Configuration | Implementation Code | UI/UX & Quality Engineering Role |
|---|---|---|---|---|
| 01 | `config_01_light_scheme_contrast.png` | Light Hybrid Baseline | `color_scheme="light"` | **Design System Light Baseline:** Tests `color_scheme="light"`. Validates that the calibrated Light Hybrid theme satisfies WCAG AA 4.5:1 text-on-surface contrast (per Task 6 Option B, dark mode is out of scope for this release). |
| 02 | `config_02_forced_colors_high_contrast.png` | Windows High Contrast Mode | `forced_colors="active"` | **Assistive Technology Bordering:** Emulates OS high-contrast accessibility mode to verify buttons, inputs, and cards retain solid system borders. |
| 03 | `config_03_reduced_motion_emulation.png` | Reduced Motion Sensitivity | `reduced_motion="reduce"` | **Vestibular Motion Safety:** Tests `@media (prefers-reduced-motion: reduce)`. Verifies that transitions, spinners, and animations are disabled. |
| 04 | `config_04_element_masking_pink.png` | Dynamic Element Masking | `mask=[locators], mask_color="#FF00FF"` | **Visual Regression Stabilization:** Masks dynamic timestamps and variable run IDs with magenta boxes to prevent false-positive diff failures. |
| 05 | `config_05_region_clipped_header_kpis.png` | Bounding Box Region Clipping | `clip={"x": 260, "y": 20, "w": 1140, "h": 380}` | **Sub-Layout Isolation:** Crops capture strictly to the results header and KPI score card coordinates without full DOM overhead. |
| 06 | `config_06_component_isolated_locator.png` | Component Locator Screenshot | `page.locator("#studio-results").screenshot()` | **Design System Token Cataloging:** Directly captures an individual DOM component in pure isolation (Storybook-style). |
| 07 | `config_07_transparent_background_button.png` | Transparent Alpha Rendering | `locator.screenshot(omit_background=True)` | **Alpha Channel Antialiasing:** Renders an isolated button with a transparent background to inspect corner radius antialiasing and drop shadows. |
| 08 | `config_08_lossy_jpeg_quality75.jpeg` | Lossy JPEG Compression | `type="jpeg", quality=75` | **Fidelity vs Weight Benchmarking:** Evaluates artifacting around text when generating lightweight audit reports or thumbnails for fast delivery. |
| 09 | `config_09_injected_style_focus_audit.png` | Injected Custom CSS Style | `style="button, a, input { outline: 2px dashed cyan; }"` | **Interactive Hit-Target Visualization:** Injects outlines around all interactive elements to immediately reveal tap targets and boundary spacing. |
| 10 | `config_10_scale_css_grid.png` | 1:1 CSS Layout Scaling | `scale="css"` | **Pixel-Accurate Grid Ruler:** Forces snapshot dimensions to map 1:1 to CSS pixels, allowing designers to measure exact 8px grid alignments. |

---

## 6. How to Run and Extend the Playwright Audit Suite

### Command-Line Arguments

The included audit script [`scripts/external_ui_ux_audit_playwright.py`](file:///d:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/scripts/external_ui_ux_audit_playwright.py) accepts standard CLI arguments:

```bash
# Basic execution
python scripts/external_ui_ux_audit_playwright.py

# Custom target and output location
python scripts/external_ui_ux_audit_playwright.py \
  --base-url "https://my-staging-site.com" \
  --output-dir "./custom_screenshots" \
  --token "secret-admin-token" \
  --run-id "RUN-CUSTOM-001"
```

### CI/CD Integration (GitHub Actions)

Add this step to your `.github/workflows/ui_audit.yml` to automatically capture and upload screenshots on every pull request:

```yaml
name: UI/UX Playwright Audit
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install playwright
          playwright install --with-deps chromium
      - name: Start Application Server
        run: |
          python -m uvicorn areos.api.main:app --port 8000 &
          sleep 3
        env:
          AREOS_API_TOKEN: "ci-token"
      - name: Run Playwright Audit
        run: python scripts/external_ui_ux_audit_playwright.py --token "ci-token"
      - name: Upload Screenshots Artifact
        uses: actions/upload-artifact@v4
        with:
          name: playwright-ui-ux-screenshots
          path: screenshots/ui_ux_audit/
```

---

*End of Guide. All assets, screenshots, and manifests are packaged inside `AREOS_UI_UX_Playwright_Audit_Package.zip` in your Downloads folder.*
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AREOS / Citeable UI/UX Audit & Playwright Configuration Guide</title>
  <style>
    :root {
      --bg: #0b0f19;
      --surface: #111827;
      --surface-elevated: #1f2937;
      --border: #374151;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --brand: #06b6d4;
      --brand-hover: #0891b2;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.6;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 40px 24px;
    }
    header {
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
      margin-bottom: 36px;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: rgba(6, 182, 212, 0.15);
      color: var(--brand);
      border: 1px solid rgba(6, 182, 212, 0.3);
      margin-bottom: 12px;
    }
    h1 {
      font-size: 2.2rem;
      font-weight: 800;
      margin: 0 0 12px 0;
      color: #fff;
    }
    h2 {
      font-size: 1.5rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
      margin-top: 48px;
      color: var(--brand);
    }
    h3 {
      font-size: 1.15rem;
      margin-top: 28px;
      color: #e5e7eb;
    }
    p, li {
      color: var(--text-muted);
      font-size: 0.95rem;
    }
    strong {
      color: var(--text-main);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      background: var(--surface);
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border);
    }
    th, td {
      padding: 12px 14px;
      text-align: left;
      font-size: 0.85rem;
      border-bottom: 1px solid var(--border);
    }
    th {
      background: var(--surface-elevated);
      color: #fff;
      font-weight: 600;
    }
    tr:last-child td {
      border-bottom: none;
    }
    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }
    code {
      font-family: var(--font-mono);
      background: rgba(255, 255, 255, 0.08);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.85em;
      color: #38bdf8;
    }
    pre {
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      color: #e2e8f0;
    }
    .card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 20px;
      margin: 24px 0;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 18px;
      transition: transform 0.2s, border-color 0.2s;
    }
    .card:hover {
      border-color: var(--brand);
    }
    .card-title {
      font-weight: 700;
      font-size: 0.95rem;
      color: #fff;
      margin-bottom: 6px;
    }
    .card-desc {
      font-size: 0.82rem;
      color: var(--text-muted);
      margin-bottom: 12px;
    }
    .tag {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 600;
      background: var(--surface-elevated);
      color: #cbd5e1;
      margin-right: 6px;
      margin-top: 4px;
    }
    .pill-pass { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .pill-warn { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
    .pill-info { background: rgba(6, 182, 212, 0.2); color: #38bdf8; }
    .footer {
      margin-top: 60px;
      padding-top: 24px;
      border-top: 1px solid var(--border);
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge">Enterprise Quality Assurance</div>
      <h1>AREOS / Citeable UI/UX Audit & Playwright Guide</h1>
      <p>Automated visual quality, accessibility (WCAG 2.1 AAA), and Playwright screenshot configuration handbook. Documents all 42 captured states across Desktop and Mobile devices.</p>
    </header>

    <h2>1. Executive Summary & Package Structure</h2>
    <p>This package contains full-resolution captures of every user-facing page, workflow state, and interactive overlay in the platform. Each screenshot exercises specific Playwright rendering and context emulation options to ensure cross-platform visual consistency.</p>
    
    <div class="card-grid">
      <div class="card">
        <div class="card-title">🖥️ Desktop Suite (23 Captures)</div>
        <div class="card-desc">1440×900 resolution at 2× Retina scale factor. Covers hero layouts, telemetry streams, score dashboards, governance approvals, documentation hubs, and keyboard modals.</div>
        <span class="tag pill-info">Retina 2x</span>
        <span class="tag">Full Page & Viewport</span>
      </div>
      <div class="card">
        <div class="card-title">📱 Mobile Suite (9 Captures)</div>
        <div class="card-desc">390×844 resolution at 3× OLED density with touch emulation. Tests hamburger menu drawer, responsive card reflow, tap target ergonomics, and landscape mode.</div>
        <span class="tag pill-pass">3x Touch Emulation</span>
        <span class="tag">Zero Overflow-X</span>
      </div>
      <div class="card">
        <div class="card-title">⚙️ Specialized Configs (10 Captures)</div>
        <div class="card-desc">Advanced Playwright capabilities: Dark Mode, High Contrast (Forced Colors), Reduced Motion, Dynamic Masking, Clipping, Alpha Transparency, and Injected CSS Styles.</div>
        <span class="tag pill-warn">WCAG AAA</span>
        <span class="tag">Regression Stability</span>
      </div>
    </div>

    <h2>2. Playwright Configuration Master Reference ("What Is What")</h2>
    <table>
      <thead>
        <tr>
          <th>Configuration Parameter</th>
          <th>Type & Default</th>
          <th>Behavioral Explanation</th>
          <th>UI/UX Audit Role</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>full_page</code></td>
          <td><code>bool = False</code></td>
          <td>When True, scrolls the full document height and stitches the entire webpage into a single image.</td>
          <td>Auditing vertical rhythm, page length, and footer placement vs. testing initial above-the-fold CTA prominence.</td>
        </tr>
        <tr>
          <td><code>type</code> & <code>quality</code></td>
          <td><code>'png' | 'jpeg'</code></td>
          <td>PNG provides lossless 24-bit output with alpha; JPEG applies lossy compression (1–100 quality).</td>
          <td>PNG is mandatory for typography and sub-pixel alignment inspection; JPEG benchmarks lightweight reporting.</td>
        </tr>
        <tr>
          <td><code>animations</code></td>
          <td><code>'disabled' | 'allow'</code></td>
          <td>When disabled, freezes CSS transitions, keyframes, and SVG animations at terminal states.</td>
          <td>Eliminates test flakiness from moving spinners, half-faded overlays, or pulsating status dots in CI.</td>
        </tr>
        <tr>
          <td><code>caret</code></td>
          <td><code>'hide' | 'initial'</code></td>
          <td>Suppresses the blinking text insertion cursor inside input fields.</td>
          <td>Prevents 500ms blinking cursor timing differences from triggering false visual regression alerts.</td>
        </tr>
        <tr>
          <td><code>scale</code></td>
          <td><code>'css' | 'device'</code></td>
          <td>'css' maps 1:1 to CSS layout pixels; 'device' captures at physical hardware pixel density.</td>
          <td>'css' enables pixel ruler measurement against 8px grids; 'device' audits Retina SVG sharpness.</td>
        </tr>
        <tr>
          <td><code>clip</code></td>
          <td><code>dict {x, y, w, h}</code></td>
          <td>Crops capture strictly to a rectangular coordinate boundary.</td>
          <td>Targeted sub-layout inspection (e.g. score card or sticky header) without full DOM overhead.</td>
        </tr>
        <tr>
          <td><code>omit_background</code></td>
          <td><code>bool = False</code></td>
          <td>Renders with a transparent alpha channel rather than the browser's default white canvas.</td>
          <td>Design system component isolation; audits border antialiasing and drop shadows on arbitrary backgrounds.</td>
        </tr>
        <tr>
          <td><code>mask</code> & <code>mask_color</code></td>
          <td><code>List[Locator], str</code></td>
          <td>Paints solid color boxes over specified dynamic elements (e.g. timestamps or session IDs).</td>
          <td>Stabilizes visual regression testing by masking non-deterministic or volatile UI elements.</td>
        </tr>
        <tr>
          <td><code>style</code></td>
          <td><code>str</code></td>
          <td>Injects custom CSS stylesheets into the document immediately prior to capturing the screenshot.</td>
          <td>Visual accessibility audits: draws outlines around all interactive tap targets or tests fallback fonts.</td>
        </tr>
        <tr>
          <td><code>color_scheme</code></td>
          <td><code>'dark' | 'light'</code></td>
          <td>Emulates <code>@media (prefers-color-scheme: dark)</code>.</td>
          <td>Dark mode contrast compliance (WCAG AA 4.5:1), ensuring no un-themed white surfaces persist.</td>
        </tr>
        <tr>
          <td><code>forced_colors</code></td>
          <td><code>'active' | 'none'</code></td>
          <td>Emulates Windows High Contrast Mode.</td>
          <td>Verifies interactive buttons and cards maintain visible system outlines when custom colors are stripped.</td>
        </tr>
        <tr>
          <td><code>reduced_motion</code></td>
          <td><code>'reduce' | 'none'</code></td>
          <td>Emulates <code>@media (prefers-reduced-motion: reduce)</code>.</td>
          <td>Ensures vestibular accessibility compliance by disabling non-essential motion and animated transitions.</td>
        </tr>
      </tbody>
    </table>

    <h2>3. Complete Screenshot Manifest (42 Captured States)</h2>
    <p>All screenshots are stored in the accompanying directory structure and indexed in <code>audit_manifest.json</code>.</p>
    
    <h3>🖥️ Desktop Suite (1440×900 @ 2× DPR)</h3>
    <ul>
      <li><code>desktop/01_studio_landing_viewport.png</code> — Landing hero above-the-fold CTA prominence and input field affordance.</li>
      <li><code>desktop/01_studio_landing_fullpage.png</code> — Full vertical document scroll of landing studio and baseline footer.</li>
      <li><code>desktop/02_studio_domain_validation_error.png</code> — Inline regex domain validation error feedback and active input border highlight.</li>
      <li><code>desktop/03_studio_live_scan_telemetry.png</code> — Multi-phase diagnostic scan monitor with active progress states.</li>
      <li><code>desktop/04_studio_score_results_dashboard.png</code> — Overall 0-100 score gauge, 5-layer diagnostic cards, and historical score delta.</li>
      <li><code>desktop/05_studio_guided_review_cards.png</code> — Guided review wizard with Pass/Warn/Fail tri-state verdict buttons.</li>
      <li><code>desktop/06_studio_synthesis_narrative.png</code> — Generative synthesis executive report with formatted markdown typography.</li>
      <li><code>desktop/07_claims_browser_page.png</code> — Empirical claims knowledge base registry with filter pills and citation links.</li>
      <li><code>desktop/08_knowledge_explorer_graph.png</code> — Interactive ontological graph canvas and node relationship matrix.</li>
      <li><code>desktop/09_byok_security_vault.png</code> — BYOK encryption vault, provider key entry form, and password mask toggle.</li>
      <li><code>desktop/10_approvals_console.png</code> — Governance queue, pending sign-off diff viewer, and decision bars.</li>
      <li><code>desktop/11_prompts_editor.png</code> — Monospace prompt engineering interface and template parameter tokens.</li>
      <li><code>desktop/12_synthesis_prompts.png</code> — Synthesis pipeline model instructions and reasoning templates.</li>
      <li><code>desktop/13_remediation_plan.png</code> — Prioritized technical remediation sequence and code export triggers.</li>
      <li><code>desktop/14_case_study_benchmarks.png</code> — Citation velocity graphs, competitor comparison bars, and methodology disclaimers.</li>
      <li><code>desktop/15_outcome_report.png</code> — Post-audit verification summary and pass/fail status stamps.</li>
      <li><code>desktop/16_manual_review_worksheet.png</code> — Analyst manual scoring rubric and observational note inputs.</li>
      <li><code>desktop/17_docs_scoring_ontology.png</code> — Technical documentation hub covering 5-layer scoring formulas and deductions.</li>
      <li><code>desktop/18_docs_internal_architecture.png</code> — Token-authenticated internal engineering architecture and async task topology.</li>
      <li><code>desktop/19_docs_diagram_fullscreen_canvas.png</code> — Fullscreen interactive SVG diagram canvas with zoom and pan controls.</li>
      <li><code>desktop/20_global_cmdk_palette.png</code> — Keyboard-triggered (Ctrl+K) command palette search modal.</li>
      <li><code>desktop/21_global_admin_auth_modal.png</code> — Keyboard-triggered (Ctrl+Shift+A) administrative token modal.</li>
      <li><code>desktop/22_global_help_tour_modal.png</code> — First-time user onboarding modal explaining platform navigation.</li>
    </ul>

    <h3>📱 Mobile Suite (390×844 @ 3× DPR & Touch Emulation)</h3>
    <ul>
      <li><code>mobile/01_mobile_studio_landing_viewport.png</code> — Mobile portrait initial viewport: compact branding, hamburger toggle, and hero CTA.</li>
      <li><code>mobile/02_mobile_studio_landing_fullpage.png</code> — Complete vertical reflow on mobile, testing for zero horizontal scroll leakage.</li>
      <li><code>mobile/03_mobile_hamburger_drawer_open.png</code> — Slide-out navigation drawer with touch targets meeting the ≥ 48px guideline.</li>
      <li><code>mobile/04_mobile_score_dashboard_fullpage.png</code> — Stacked results dashboard with responsive circular SVG gauge.</li>
      <li><code>mobile/05_mobile_guided_review_cards.png</code> — Vertically stacked review cards with thumb-zone verdict button rows.</li>
      <li><code>mobile/06_mobile_byok_vault.png</code> — Compact mobile credential management screen and password reveal hit target.</li>
      <li><code>mobile/07_mobile_claims_browser.png</code> — Claims registry reflowed into readable stacked mobile cards.</li>
      <li><code>mobile/08_mobile_docs_scoring.png</code> — Documentation layout with independent horizontally scrollable code blocks.</li>
      <li><code>mobile/09_mobile_landscape_results_viewport.png</code> — Mobile phone rotated horizontally (844×390), testing vertical compression.</li>
    </ul>

    <h3>⚙️ Specialized Configurations Suite</h3>
    <ul>
      <li><code>specialized_configs/config_01_light_scheme_contrast.png</code> — Light Hybrid theme contrast validation (Task 6 Option B).</li>
      <li><code>specialized_configs/config_02_forced_colors_high_contrast.png</code> — Windows High Contrast Mode simulation via forced_colors='active'.</li>
      <li><code>specialized_configs/config_03_reduced_motion_emulation.png</code> — Vestibular motion sensitivity simulation via prefers-reduced-motion: reduce.</li>
      <li><code>specialized_configs/config_04_element_masking_pink.png</code> — Dynamic timestamp and run ID masking via mask=[locators] and mask_color.</li>
      <li><code>specialized_configs/config_05_region_clipped_header_kpis.png</code> — Isolated rectangular bounding-box clip of the score header banner.</li>
      <li><code>specialized_configs/config_06_component_isolated_locator.png</code> — Direct locator-level component capture (page.locator().screenshot()).</li>
      <li><code>specialized_configs/config_07_transparent_background_button.png</code> — Button component rendered with transparent alpha channel (omit_background=True).</li>
      <li><code>specialized_configs/config_08_lossy_jpeg_quality75.jpeg</code> — Lightweight JPEG compression at quality=75 for bandwidth-sensitive audits.</li>
      <li><code>specialized_configs/config_09_injected_style_focus_audit.png</code> — Custom CSS injected to highlight all interactive button and link hit areas.</li>
      <li><code>specialized_configs/config_10_scale_css_grid.png</code> — 1:1 CSS layout pixel scaling for exact 8px grid ruler measurements.</li>
    </ul>

    <div class="footer">
      Generated automatically by the AREOS Quality Assurance Engine &middot; Antigravity 2.0
    </div>
  </div>
</body>
</html>
"""

def generate_docs():
    print("[*] Generating Markdown guide...")
    with open(DOC_MD_PATH, "w", encoding="utf-8") as f:
        f.write(MD_CONTENT.strip())

    print("[*] Generating Styled HTML guide...")
    with open(DOC_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE.strip())

    # Copy docs directly to Downloads
    shutil.copy2(DOC_MD_PATH, DOWNLOADS_DIR / "UI_UX_AUDIT_PLAYWRIGHT_GUIDE.md")
    shutil.copy2(DOC_HTML_PATH, DOWNLOADS_DIR / "UI_UX_AUDIT_PLAYWRIGHT_GUIDE.html")
    print(f"[+] Saved standalone documentation directly to {DOWNLOADS_DIR}")


def build_zip_archive():
    print(f"[*] Creating ZIP archive at: {ZIP_OUT_PATH}")
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(ZIP_OUT_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # 1. Add documentation files at root of zip
        zf.write(DOC_MD_PATH, arcname="UI_UX_AUDIT_PLAYWRIGHT_GUIDE.md")
        zf.write(DOC_HTML_PATH, arcname="UI_UX_AUDIT_PLAYWRIGHT_GUIDE.html")

        # 2. Add manifest
        if MANIFEST_PATH.exists():
            zf.write(MANIFEST_PATH, arcname="audit_manifest.json")

        # 3. Add runnable script
        if SCRIPT_PATH.exists():
            zf.write(SCRIPT_PATH, arcname="scripts/external_ui_ux_audit_playwright.py")

        # 4. Add all screenshots
        for root, _, files in os.walk(SCREENSHOTS_DIR):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(SCREENSHOTS_DIR.parent)
                zf.write(full_path, arcname=str(rel_path).replace("\\", "/"))

    size_mb = ZIP_OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Zip package built! Size: {size_mb:.2f} MB")
    print(f"[+] Saved to: {ZIP_OUT_PATH}")

if __name__ == "__main__":
    generate_docs()
    build_zip_archive()
