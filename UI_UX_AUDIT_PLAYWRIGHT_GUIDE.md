# AREOS / CITEABLE UI/UX AUDIT & PLAYWRIGHT CONFIGURATION MASTER GUIDE

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
| 03 | `03_mobile_hamburger_drawer_open.png` | Mobile Nav Drawer (390×844) | Programmatic menu toggle, `has_touch=True` | **Touch Target Ergonomics:** Verifies navigation links meet WCAG 2.5.5 minimum touch target height ($\ge 48	ext{px}$), checks backdrop tap-to-dismiss behavior. |
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
python scripts/external_ui_ux_audit_playwright.py   --base-url "https://my-staging-site.com"   --output-dir "./custom_screenshots"   --token "secret-admin-token"   --run-id "RUN-CUSTOM-001"
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