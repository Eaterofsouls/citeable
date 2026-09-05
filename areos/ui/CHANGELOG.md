# Citeable UI Changelog — LinkedIn × Instagram Light Hybrid Edition

## [v2.5.0] - 2026-09-02

### 1. Design System & Token Architecture (`index.css`)
- **Canvas & Surface Layering**:
  - Replaced legacy dark espresso tones with crisp off-white canvas (`--surface-canvas: #F8F9FB`), pure white elevated panels (`--surface-panel: #FFFFFF`), and inset sunken wells (`--surface-sunken: #F1F5F9`).
  - Standardized hairline borders (`--border-default: #E2E8F0`, `--border-strong: #CBD5E1`).
  - Added subtle modern shadows (`--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-focus`).
- **Brand Palette & Gradients**:
  - Primary Brand Token: LinkedIn Sapphire Blue (`--brand-500: #0A66C2`).
  - Primary Action CTAs & Score Progress Rings: Signature Hybrid Sunset Iris Gradient (`linear-gradient(135deg, #0A66C2 0%, #4F46E5 50%, #E11D48 100%)`).
  - Semantic Status Tokens: Verified Emerald (`#059669`), Contested Amber (`#D97706`), Critical Sunset Rose (`#E11D48`).
- **Typography Standards**:
  - UI Copy: `Plus Jakarta Sans` (weights: 400, 500, 600, 700, 800, 900).
  - Code, Data Keys, Metrics, and JSON: `JetBrains Mono` (weights: 400, 500, 600, 700, 800).

### 2. 100% Emoji Removal & Vector SVG Migration
- **Navigation (`nav.js`)**:
  - Replaced all 7 route emojis with clean 1.5px/2px stroke Lucide vector SVGs:
    - Audit Studio: `polygon` bolt vector
    - Knowledge Explorer: `book-open` vector
    - Approvals: `shield-check` vector
    - Documentation: `book` vector
    - Prompt Design: `message-square` vector
    - Synthesis Prompts: `refresh-cw` vector
    - Case Study: `file-text` vector
    - BYOK AI Vault: `key` vector
- **Scorecard Sub-Score Layers (`studio.js`)**:
  - Citation: Search radar SVG
  - Content: Document page SVG
  - Access: Robot access gate SVG
  - Authority: Classical column pillar SVG
  - Schema: Microdata tag SVG
- **Status Banners & Steppers (`index.html`, `studio.js`, `synthesis_prompts.html`)**:
  - Pipeline Monitor: Animated spinning SVG loader and emerald completion checkmark.
  - Score Delta Box: Upward trending vector polyline chart.
  - Access Gate & Security Warnings: Geometric alert triangle SVG.
  - Stale Data Badges: Clock time-decay SVG.

### 3. Client Domain Modules & Modals
- **BYOK Vault (`byok.js`)**:
  - Updated modal styling to clean white card with subtle slate borders and backdrop blur.
  - Replaced unicode indicators with SVG shield assurance badge and live status pills.
- **Documentation Viewer (`docs.js`)**:
  - Updated Mermaid diagram theme engine (`themeVariables`) to render crisp light theme architecture diagrams.
  - Replaced unicode fullscreen symbol with clean text.
- **Approvals & Human Review (`approvals.js`, `guided_review.js`)**:
  - Updated walkthrough completion modal and all-clear states with emerald circular checkmark SVGs.
  - Replaced raw inline styling with unified CSS custom properties.
- **Toast Notifications (`api.js`)**:
  - Restyled `AreosAPI.notify()` with white card background, subtle shadow, and color-coded status indicator borders.

### 4. HTML Template Standardization
- Standardized Google Font links (`Plus Jakarta Sans` + `JetBrains Mono`) across all 12 templates:
  `index.html`, `approvals.html`, `byok.html`, `case_study.html`, `claims_browser.html`, `docs.html`, `knowledge_explorer.html`, `manual_review.html`, `outcome.html`, `prompts.html`, `remediation.html`, `synthesis_prompts.html`.

### 5. UI Polish & Component Restorations
- **Knowledge Explorer Card Contrast & Structure (`index.css`, `knowledge_explorer.html`)**:
  - Structured every claim into a distinct rectangular card with white background, slate border (`#E2E8F0`), subtle elevation, and hover lift.
  - Replaced washed-out badges with high-contrast accessible color tokens:
    - `FACT`: Emerald Green (`#ECFDF5` bg, `#065F46` text, `#A7F3D0` border)
    - `GUIDANCE`: Sapphire Blue (`#EFF6FF` bg, `#1E40AF` text, `#BFDBFE` border)
    - `STANDARD`: Slate Neutral (`#F1F5F9` bg, `#334155` text, `#CBD5E1` border)
    - `FINDING`: Amber Gold (`#FFFBEB` bg, `#92400E` text, `#FDE68A` border)
    - `UNCERTAINTY`: Rose Crimson (`#FFF1F2` bg, `#9F1239` text, `#FECDD3` border)
- **Studio Workflow Stepper Bar (`index.css`)**:
  - Restored complete `.studio-stepper`, `.step-btn`, `.step-dot`, and `.step-connector` styling.
  - Active step now displays high-contrast LinkedIn Sapphire badge with subtle shadow, and connecting bars smoothly bridge each phase.
- **Documentation Page Availability (`main.py`, `docs.js`)**:
  - Fixed `/docs` mount point in `main.py` to point directly to `areos/ui/docs` directory.
  - Enhanced `fetchMarkdown` in `docs.js` with multi-path fallback discovery (`docs/external.md`, `/docs/external.md`, `areos/ui/docs/external.md`).

### 6. Additional Refinements & Brand Identity
- **Brand Logo — The Citation Prism (`favicon.svg`, `index.css`)**:
  - Replaced the generic magnifying glass icon with **The Citation Prism**: precision vector geometric double quotation marks `“”` on the signature Sunset Iris Gradient (`#0A66C2` ➔ `#4F46E5` ➔ `#E11D48`) with a high-contrast diamond spark accent.
  - Updated `.logo-icon` across all pages for crisp, unclipped scaling from 16px tab favicons to 32px sidebar headers.
- **Hero & Primary Action CTA Polish (`index.css`, `index.html`)**:
  - Restored bold emerald count (`#059669`) and continuous pulsing live dot animation (`.live-pulse-dot`) on the 216 research checks counter.
  - Updated **RUN FULL SPECTRUM AUDIT →** and input wells to smooth 10px rounded pill radius (`--radius-md`) with high-energy primary CTA gradient and hover elevation.
  - Fixed **Export Automated Findings (.md)** affordance: removed fading `opacity: 0.75;`, added crisp `1.5px solid var(--border-strong)` border, and embedded a vector download SVG icon.
- **Results Dashboard Analytics Panels (`index.css`, `index.html`, `studio.js`)**:
  - Replaced raw programmer `//` comment syntax with clean editorial titles (*Historical AEO Delta & Timeline*, *Citation Domain Distribution*, *Prioritized Action & Remediation Plan*).
  - Wrapped analytics in an elevated 2-column responsive card grid (`.analytics-grid`, `.analytics-panel`) with inline SVG icons and right-aligned category badges.
  - Upgraded citation distribution bar charts to the vibrant Light Hybrid palette (`#0A66C2`, `#4F46E5`, `#059669`, `#D97706`, `#8B5CF6`).
- **Context-Aware Manual Review Empty State (`index.html`, `studio.js`)**:
  - Prevented premature rendering of *"One more step..."* banners and unpopulated disclosure caveats before an audit session is initiated.
  - Ensured pre-audit visits to the Manual Review tab display only the clean centered *"No active audit session"* card with `[GO TO AUDIT INPUT →]`.
- **Floating Help Trigger FAB (`help.js`)**:
  - Replaced the dark black-on-black circle with the signature Sunset Iris Gradient button, white centered question mark SVG icon, and soft glow hover elevation.

### 7. Verification & Quality Assurance
- Backend Test Suite: 339 / 339 unit & integration tests passing (**100% pass rate, 0 regressions**).
- Node Syntax Check: 19 / 19 JavaScript client modules validated clean.
- Emoji Count: Exactly 0 unicode emojis across the UI layer.
