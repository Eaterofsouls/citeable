# Changelog — UX Audit Remediation Pass

Implements the full audit at `citeable_ux_audit_and_recalibration_plan.md` (§3, §4, §5). Every entry below is
cross-referenced to that document so you can verify against the original reasoning rather than trusting this
summary blind. All changes tested locally in-sandbox (see "How this was verified" at the bottom) — I could not
test against a live LLM provider (no API keys) or on Render itself.

---

## Frontend (§3 + §4)

**Landing page (§3.1)**
- `areos/ui/studio.html` → `areos/ui/index.html` (new landing page)
- `areos/ui/index.html` (old Claims Browser) → `areos/ui/claims_browser.html`
- Updated every internal link/nav entry/breadcrumb/deep-link across `nav.js`, `studio.js`, and both renamed files
- `identity.js`: the "Welcome to Citeable" identity gate no longer blocks `claims_browser.html` — read-only claim
  browsing doesn't log an attributed action, so it shouldn't require an identity, unlike the Studio flow

**Stepper navigation (§4)**
- Replaced the 4-button flat tab bar in `index.html` with a numbered stepper (`.studio-stepper` / `.step-btn`)
- **Bug found and fixed while doing this:** the original tab-click handler used `e.target`, which would have
  broken on clicks landing on the new `.step-dot`/`.step-label` child spans (`e.target.dataset.tab` would be
  `undefined`, causing `document.getElementById(undefined)` to throw). Switched to `e.currentTarget`. Fixed in
  three places: the module-level tab-click listener, and two auto-switch call sites in `studio.js`.
- Added `syncStepper()`, called from `updateShieldProgress()` and after synthesis completes, to reflect real
  completion/lock state on each step (`.step-complete`, `.step-locked`)

**Results Dashboard "Action Required" banner (§3.4)**
- New `#results-action-banner` in `index.html`, driven by `syncResultsActionBanner()` in `studio.js`
- Shows amber "N check(s) still need a human look" while the wizard is incomplete, flips to green "Human review
  complete" once it isn't, with a button that jumps to the correct next step either way

**Dead button fix (§3.5)**
- `studio.js`: `renderSynthesisTab()`'s "Start Guided Wizard" button used `document.querySelector('[data-tab=wizard]')`,
  which matches nothing (`data-tab="tab-wizard"` is the real attribute) — `null && null.click()` silently did
  nothing. Fixed the selector.

**Shield banner + progress meter CSS (§3.6)**
- `.shield-banner`, `.shield-locked`, `.shield-unlocked`, `.progress-meter`, `.progress-meter-fill` were toggled
  by JS and referenced in HTML but never defined in `index.css` — the "audit unverified" warning rendered with
  zero visual weight. Added full CSS (amber=locked, green=unlocked).

**Lock-out state (§3.7)**
- `.step-locked` styling (dimmed + lock icon) added to the stepper for steps 3/4 when not yet reachable; steps
  stay clickable (not `disabled`) so the in-panel "why" message (§3.5's fixed CTA) can still explain and redirect

**Nav consolidation (§3.8)**
- Removed "Manual Review", "Remediation", "Outcome Logger" from the sidebar (`nav.js` `workflowItems`) — all
  three duplicated content already rendered inside Studio's own tabs, via a different data path each
  (`manual_review.html` called `GET .../report`, a deterministic markdown compiler entirely separate from
  Studio's `POST .../synthesize` LLM pipeline — see §3.6/§5 below for why that mattered)
- `manual_review.html`, `remediation.html`, `outcome.html` are now thin redirect stubs pointing to
  `index.html?tab=<step>&run_id=<id>` (preserves bookmarks/links), landing on the equivalent Studio step
- `studio.js`: added query-param routing on load (`?tab=`, `?run_id=`) so these redirects — and any bookmarked
  `?run_id=` link — land somewhere real instead of resetting to a blank Audit Input screen (see `loadRunById()`
  under Backend, below)

**Copywriting pass (§3.2)**
- Hero subtext, shield banner title/subtitle, wizard "Note:" label, AI Synthesis header/status-bar copy (now
  "Your Final Report" instead of "AI Synthesis Narrative", with the three-step pipeline explanation moved to a
  collapsible "how this works" instead of leading the page)

**Guided Review redesign (§5.5, implemented as a frontend template change)**
- `guided_review.js`: every check family's guidance rewritten as a direct question ("Can AI search engines
  actually reach your pages?") with a "why this matters" line and a numbered "how to check it" procedure —
  previously a dense, bureaucratic-voice paragraph per card, and the PASS/WARN/FAIL definitions were duplicated
  in prose *and* on the buttons
- `renderInlineWizard()` rebuilt around the question-first template (`.gr-card` / `.gr-card-question` /
  `.gr-card-why` / `.gr-card-how`), with progress dots ("Question 3 of 8"), a "View the site we're asking
  about" deep link, and the check code/card ID demoted to a small footnote instead of leading the card
- Post-answer confirmation copy softened ("✓ Answered: Pass" instead of "[DONE] Submitted to Registry")

**Premature export fix (§3.11)**
- `exportExecutiveReport()`: the export is now titled "(Automated Findings)" normally, or explicitly flagged
  "— PRELIMINARY, Human Review Not Yet Complete" with an inline warning when the wizard isn't done, instead of
  silently calling itself "Executive Report" regardless of completeness
- Button relabeled "Export Automated Findings (.md)" and visually demoted (`opacity:0.75`)
- New "Download Final Report →" button (`downloadFinalReport()`) appears only once a real synthesis narrative
  exists — it's the one primary action once there's something to be primary about

**Mobile responsiveness (§3.9)**
- `.studio-tabs`/`.tab-btn` had zero CSS rules beyond a generic color reset — the stepper now has a
  `max-width: 640px` rule enabling horizontal scroll instead of silent overflow/clipping

**Outcome Logger disable state (§3.10)**
- `syncOutcomeFormAvailability()` disables `.outcome-input`/`.btn-log-outcome` when there's no active run,
  instead of letting the user fill the form and only then failing with a toast

---

## Backend (§5)

**One derivable state machine, not three inconsistent writers (§5.2)**
- Confirmed the exact problem described in the audit: `audit_runs.status` was being written independently by
  `audit_orchestrator.py` (`automated_complete`), `verdicts.py` (`in_review`, on *every* verdict, not just the
  first), and `reports.py` (`report_generated`, mutated inside a `GET` handler)
- Rather than trying to make three separate writers agree (fragile), added `areos/services/run_state.py`, which
  **derives** status live from ground truth already in the DB:
  - `get_wizard_cards_for_run()` recomputes the expected wizard-card set from the run's stored
    `automated_findings` via the same `select_triggered_cards()` function the orchestrator used originally —
    this works because it's a pure function of persisted data, so no new "expected card count" column was needed
  - `get_run_completeness()` compares that expected set against `COUNT(DISTINCT card_id)` in `manual_verdicts`,
    and checks for a row in the new `audit_synthesis` table, to derive one of three states:
    `awaiting_review` → `ready_for_synthesis` → `complete`
  - The legacy `status` column and its three writers were **not** modified or removed — this derivation lives
    alongside them rather than risking a change to code paths I couldn't fully integration-test blind. The new
    endpoints use the derived value; nothing currently reads the legacy column as authoritative anymore, but
    removing the old writes outright is a good candidate for a follow-up pass once this is verified in staging.

**One report object your synthesis result can't outlive a page reload (§5.3)**
- **New table** `audit_synthesis` (`db/schema/artifacts.py` + `db/schema.sql`) — added because I found, while
  tracing the code, that the three-step LLM synthesis result (`POST .../synthesize`) was **never persisted
  anywhere** — it only ever existed in that one HTTP response. A page reload after synthesis silently lost the
  "final report" the entire hybrid flow builds toward. This wasn't in the original audit; found during
  implementation.
- `POST /api/v1/audit/runs/{run_id}/synthesize` (`api/routers/audit.py`) now persists a successful result via
  `run_state.persist_synthesis()` (upsert on `run_id`, wrapped in `write_as()` for correct changelog
  attribution). Persistence failure is caught and logged, not raised — a DB hiccup shouldn't cost the user their
  already-generated report this session.
- **New endpoint** `GET /api/v1/audit/runs/{run_id}/full` — the single rehydration point for a stored run:
  returns `remediation_plan` (rebuilt from stored findings via the same claim-lookup logic already proven in
  `/synthesize`), `manual_review_wizard`, `llm_synthesis` (persisted result if one exists), `raw_findings`, and
  `completeness`. This is what the retired standalone pages' redirects resolve through, and what
  `loadRunById()` in `studio.js` calls to rehydrate the Results/Wizard/Synthesis tabs for a bookmarked
  `?run_id=` link.
  - **Documented scope limit, not fixed in this pass:** `executive_scorecard`'s crawler-status / llms.txt-status
    / citation-rate / authority-metrics fields were computed from live network calls at scan time and aren't
    reconstructable from stored findings without re-crawling. `/full` returns `overall_score` (persisted at scan
    time) but the frontend intentionally shows placeholders for those specific sub-fields on a reload rather
    than guessing. This only affects revisiting an old run later — a run's first, live view is unaffected.

**No claims/DB-registry changes** — `claims`, `check_code_mappings`, and every other claims-governance table are
untouched. The one schema addition (`audit_synthesis`) lives entirely in the audit-run subsystem, consistent
with the scope boundary agreed before starting this work.

---

## Documentation updates

- `areos/ui/docs/internal.md` §6.5: added a row documenting `GET .../full`, and a note on `POST .../synthesize`
  now persisting its result
- `areos/ui/docs/internal.md` §2.2: noted the new `audit_synthesis` table alongside the existing
  `audit_runs`/`manual_verdicts` description
- This file (`CHANGELOG.md`)

**Not touched, on purpose:** `README.md`'s env var name / test-suite references were already inconsistent with
this codebase export before I started (e.g. `Citeable_API_TOKEN` in prose vs. `AREOS_API_TOKEN` which is what
actually works, and a `tests/` directory the README describes that isn't present in this export) — pre-existing
drift, unrelated to this pass, left alone rather than risking an unrequested fix based on a guess about which is
correct.

---

## Follow-up pass: guided review content + synthesis prompt editor relocation

Two issues found after deployment, from real screenshots of the running app.

**Guided Review was showing identical text for different checks (found via user report + PDF screenshots)**

Root cause: `getSimpleGuidance()` in `guided_review.js` bucketed all 14 real instruction cards
(`areos/instruction_cards/*.md`) into 5 generic keyword-matched families and served one canned paragraph per
family — so two genuinely different cards in the same family (e.g. C073 "Causal Attribution of Citations" vs
C082 "Digital-PR / Third-Party Citation Gap") showed byte-identical questions, reasoning, and steps. This wasn't
a rendering bug — the 14 cards already have detailed, well-differentiated, professionally-written content sitting
unused in the repo; the family-bucketing discarded it in favor of my own generic invention.

Fix: replaced the 5-family generator with a `CARD_GUIDANCE` table keyed by the actual `card_id` (all 14 present),
each entry adapted from that specific card's real `.md` content into the layman interview format (question / why
it matters / how to check), instead of inventing generic per-family text. Added an `example` field on cards where
a literal worked example makes sense (mainly the citation-related cards — C056, C073, C074, C077, C078, C082),
rendered as a new "Try it yourself" block with the real domain and literal platform query text
("Type into ChatGPT: 'What does {{domain}} do?'") substituted at render time. `escapeHtml()` is applied after
domain substitution, not before, since domain is user-entered input.

Also fixed in the same file: `checkRef`'s "strip the redundant prefix" regex had accumulated quadruple-escaped
backslashes from an earlier edit pass and never actually matched — confirmed via the user's own screenshot,
which showed "Check C073 · Check code(s) fired: CITATION_NOT_OBSERVED" instead of the intended
"Check C073 · CITATION_NOT_OBSERVED". Fixed the regex.

Not touched: `getHumanReviewGuidance()` / `getCheckFamily()` / `FAMILY_BY_CARD_ID` still exist and are used only
by the modal-dialog review flow (`mode` other than `"inline"`), which nothing in the live app currently invokes
(`studio.js` always calls `GuidedReview.start()` with `mode: "inline"`). Left the family-bucketing structure
alone there since it's unreachable in practice, but did soften `getHumanReviewGuidance`'s copy (dropped phrases
like "Tailored AI Extractability Protocol") so it isn't left in a worse state than everything else in the file,
since it remains exported on the public `GuidedReview` API.

**Synthesis Prompt Editor was rendering blank textareas and throwing 401s for every non-admin visitor**

Root cause: `GET/PUT /api/v1/synthesis/prompts*` require `verify_admin` on the backend (correct, by design), but
the editor panel was unconditionally rendered inside Studio's "AI Synthesis" tab — a screen every visitor sees —
and `studio.js` fired the fetch for everyone. Any visitor without an admin token got silent 401s and permanently
empty textareas with Save/Reset buttons that would also 401 if clicked.

This wasn't just a missing auth-check — the panel was in the wrong place architecturally even for an admin: it
edits global state (the actual system prompts driving the Synthesizer/Red-Teamer/Grounder pipeline), so a save
changes AI behavior for every future audit run, for every user, not just the person editing it. Putting that on
the same screen a client might be viewing their finished report on made it easy to fat-finger.

Fix, two parts:
1. Removed the panel entirely from `index.html`'s `#tab-synthesis` and the corresponding
   `loadSynthesisPrompts()`/`savePrompt()`/`resetPrompt()` functions from `studio.js`.
2. Added a new admin-only page, `synthesis_prompts.html` + `synthesis_prompts.js`, gated in `nav.js`'s
   `adminIds` list exactly like the existing "Prompt Design" page (hidden from the sidebar unless
   `sessionStorage.areos_api_token` is set). The new page:
   - Shows a permanent, unmissable warning that changes here affect every future audit run for every user.
   - Distinguishes "no admin token at all" (shows an "Admin access required" panel with a button that opens the
     existing Ctrl/Cmd+Shift+A admin-auth modal) from "token present but rejected" (401/403 — shows a distinct
     "your token was rejected, re-authenticate" message), instead of both cases silently producing blank boxes.
   - Reuses the exact same three prompt cards (Synthesizer/Red Teamer/Grounder), moved verbatim from the old
     location, with no backend/API changes — this was a frontend relocation + gating fix only.

Verified via the real running server: `GET /synthesis/prompts` confirmed to return 401 with no token, 401 with a
wrong token, and 200 with the correct one; `synthesis_prompts.html`/`.js` confirmed served; the full audit
lifecycle (orchestrate → verdicts → `/full` completeness) re-run end-to-end afterward to confirm nothing in the
existing flow regressed.

---

## How this was verified

No test suite was included in this codebase export (no `tests/` dir despite `migrate_audit_tables.py`'s
comments referencing one), so verification here was manual:

- `node --check` on every modified `.js` file (syntax only, not behavior)
- Python `ast.parse()` on every modified/new `.py` file
- Booted the FastAPI app locally (`uvicorn`, fresh SQLite DB) and confirmed `migrate()` creates
  `audit_synthesis` cleanly on top of the existing schema
- Ran a full lifecycle against the real, running backend: orchestrate → partial verdicts → remaining verdicts →
  confirmed `status` transitions `awaiting_review` → `ready_for_synthesis` at exactly 100% completion →
  `synthesize` with no LLM key configured (confirmed graceful `llm_synthesis_used: false`, no crash) →
  confirmed `/full` still correctly reports `ready_for_synthesis` (not silently "complete")
- Directly exercised `persist_synthesis()`/`get_persisted_synthesis()` against the live DB with a synthetic
  result: round-trip correctness, and confirmed a second write **updates** (upsert) rather than duplicating a row
- Cross-checked every DOM ID the new/modified JS reads or writes against the actual HTML — no stale references
- Grepped for any remaining reference to the old `studio.html`/`index.html` filenames or the broken
  `[data-tab=wizard]` selector — none found

**Not verified (couldn't be, in this environment):** a real LLM provider call through `/synthesize` (no API
keys available here), actual rendering in a browser (no headless browser tool available — HTML was checked for
well-formedness and DOM-id consistency, not visually), and anything Render-specific (env var wiring in the Render
dashboard, persistent disk behavior). Dockerfile/render.yaml/requirements.txt are unchanged from the original,
so deploy mechanics should behave exactly as they did before this pass.

---

## Documentation pass: internal/external doc upgrade

Upgraded existing documentation (`areos/ui/docs/external.md`, `internal.md`) rather than rewriting from scratch.
No capabilities invented — every new claim below was verified against the running code or the live database
before being written.

**New: "The Complete AEO/GEO Audit Lifecycle" section (both docs).** This was the explicit top priority. Per the
brief, searched the repository for existing lifecycle material before writing anything new — found it not as
prose, but as governed data: `claims.stage_id` values `AP-01`..`AP-09` encode a real, researched nine-phase audit
taxonomy (213 of 217 live claims), each carrying an `automatability_rating` claim describing whether that phase's
work is human-only, partial, or automatable. Wrote up that taxonomy as a first-class section in both docs — a
9-phase table, a new Mermaid diagram showing exactly which phases Citeable automates vs. leaves to a human, and
an explicit answer to "where does Citeable fit in a real audit." The internal version goes deeper: it documents
the exact SQL query behind the phase counts, and a verified finding that the Manual Review Wizard's 14
instruction cards are literally keyed to 14 specific `AP-0X` claims (same ID, confirmed by checking every one
against `INSTRUCTION_CARDS`) — meaning only 14 of the 213 phase-taxonomy claims currently have an actionable
wizard card; the rest are governed knowledge with no UI surface yet.

**Found and flagged: a real naming collision.** `scoring.py`'s five scoring layers are independently labeled
`AP-01`..`AP-05` in the code — a completely different, unrelated namespace from the `claims.stage_id` taxonomy
above, which also uses `AP-01`..`AP-09`. Both are real, live code. Added an explicit callout in both docs (§2.4
external, §2.4 internal) so a reader doesn't conflate "AP-03 the scoring layer" (Content Format) with "AP-03 the
audit phase" (Technical Crawlability) — they are not the same thing despite sharing a prefix.

**Fixed real factual errors, found by cross-checking against code:**
- `internal.md` stated the score range as "15 to 98" in two places; `scoring.py` defines `SCORE_FLOOR = 5`. Fixed
  both instances to 5–98.
- Claims count was stated as 213 in two places; live `SELECT COUNT(*) FROM claims` returns 217. Updated with
  "live count as of this revision" framing rather than a claim that will silently go stale again.
- Claim-type count stated as 16; live distinct count is 17. Fixed.
- A claim in a draft of the new section asserted "M001–M005 are all `status='deprecated'`" — checked directly;
  `M003` is actually `status='active'`. Corrected before it reached the doc.

**Restructured, not just edited.** Both docs had their own numbering scheme, which the new section required
renumbering rather than awkwardly wedging in as e.g. "§2.5": `external.md`'s 15 other `##`/`###` headings shifted
+1 (verified every one of 59 heading replacements matched exactly once before applying), and every one of the
doc's cross-reference links (`[§N](#anchor)`) was updated to match — verified programmatically afterward by
re-deriving every heading's real slug (replicating `docs.js`'s exact `slugifyHeadingText()` logic) and confirming
all 29 anchor links resolve, with zero broken links. `internal.md` had a pre-existing, unrelated structural bug
fixed in the same pass: sections 04–10 were `###` while 01–03 were `##`, so they nested incorrectly in the
viewer's auto-generated TOC (`docs.js` walks `h2, h3` — the mismatched level meant those seven sections were
rendered one level deeper than they should have been). Normalized to `##` throughout.

**Verified against the real admin-view rendering path, not just each file in isolation.** Found that `docs.js`
concatenates `external.md` + `internal.md` into a single combined document for any session with an admin token,
with no visible separator between them (`loadDocumentationSource()`). Re-ran the anchor/slug verification against
that actual concatenated output (105 combined headings) to confirm no ID collisions between the two files' heading
schemes — none found; the two docs' differing number formats (`N.` vs `0N —`) already prevent collision, and the
new sections follow the same pattern.

**Mermaid diagrams.** No headless browser available in this sandbox to visually render, so validated all three
diagrams (2 pre-existing + 1 new) through the real `mermaid.parse()`/`mermaid.render()` API via a jsdom-based
harness — all three confirmed syntactically valid. Caught and fixed two real bugs in my own new diagram before
finalizing: `\n` does not produce a line break in a Mermaid flowchart node label (needs `<br/>`), and dotted-edge
labels are safer with padding spaces (`-. label .->` vs `-.label.->`). Confirmed the two pre-existing diagrams
are byte-identical to the original file — untouched by the renumbering pass.

**Spot-verified existing content rather than rewriting indiscriminately.** Cross-checked the deterministic
scoring section's full 26-entry deduction table against `scoring.py`'s live `LAYER_DEDUCTIONS` dict — exact
match, left unchanged. Cross-checked the citation-sampling section's provider claims against
`citation_sampler.py` — confirmed Perplexity Sonar + Gemini grounded search are the actual two providers used
(the doc was previously vague on this; named them explicitly, since specificity here doesn't expose anything
internal-only). Cross-checked the "11-provider waterfall" claim against `llm/providers/__init__.py`'s
`_build_waterfall()` — the code's own inline comments number providers 1–11; confirmed accurate, left unchanged.

**Internal/external boundary.** Checked the new external-facing lifecycle section for leaked internal-only
terms (`claims.stage_id`, `automatability_rating`, table/column names, file paths, raw SQL) — none found. The
external version describes the same nine phases and the same automation boundary in plain terms; the internal
version is the one with schema references, SQL, and file-path citations.

**Added:** a scannable "30-second" summary table at the very top of `external.md` (what it is / problem / input
/ process / output / why the architecture is interesting), per the brief's #1.

**Not done in this pass** (scope was very large; prioritized the explicitly-flagged "most important" item and
verified accuracy over exhaustive rewriting): a section-by-section rewrite of `external.md` §3 (System
Architecture) and §8 (Evidence Model) — both were read and appear substantively sound, but weren't individually
cross-checked against code line-by-line the way scoring/citation-sampling/providers were. `docs.js`/`docs.html`
(the viewer) were reviewed and found to already be well-built — vendored `marked.js`/`mermaid.js` (avoiding a CSP
issue with CDN scripts), auto-generated scroll-spied TOC, stable heading IDs — so left alone per "don't redesign
things for no reason"; no functional viewer changes were needed to support the new content, since it uses the
same heading/table/Mermaid patterns the viewer already renders correctly.

---

## Docs viewer: collapsible sections + motion pass

Implements the accordion/motion redesign discussed and approved for the documentation page specifically
(`docs.html`/`docs.js`/`index.css`) — no other pages touched.

**Correction to my own earlier brief:** while implementing, found that `setupSmoothAnchorScroll()` already existed
and already used `window.scrollTo({behavior:'smooth'})` for TOC/cross-reference clicks — I'd incorrectly told the
user this didn't exist, having only checked CSS (`scroll-behavior`) and missed the JS implementation. Left it as
is; the actual gaps were the lack of collapsible sections and the lack of any reveal motion on load, both fixed
below.

**Structure — `buildAccordionSections()` (new, `docs.js`).** Each top-level (`##`/H2) section becomes a native
`<details class="docs-section">`, collapsed by default: title always visible, click to read. Built via real DOM
node moves (`appendChild`), never by re-serializing `innerHTML`, specifically so it's safe to run after
`renderMermaidDiagrams()` even though `mermaid.run()` is async — relocating a node doesn't invalidate a pending
promise that's still writing into it. Content before the first H2 (intro + the "30-second summary" table) is left
untouched outside any accordion, so orientation content costs zero clicks. Uses genuine `<details>`/`<summary>`
(matching the existing `docs-toc-details` pattern already in this codebase) rather than a custom show/hide, so
keyboard operation and the browser's native find-in-page auto-expand keep working for free.

**Motion — `setSectionOpen()` (new, `docs.js`).** Expand/collapse animates height + opacity via the Web Animations
API using this app's *existing* design tokens (400ms / `cubic-bezier(0.2, 0.8, 0.2, 1)`, i.e. `--duration-slow` /
`--ease-standard` from `index.css`) — no new timing values invented. Initial page load reveals section headers
with a 60ms stagger (CSS `animation-delay`, capped at 8 steps so a 27-section combined admin view doesn't drag).
Explicitly checks `prefers-reduced-motion` in JS before running any WAAPI animation, since — confirmed by reading
the existing sitewide override — that CSS rule only zeroes `animation-duration`/`transition-duration` for CSS-
driven motion, not JS-driven `element.animate()` calls; without this check, reduced-motion users would still get
the JS animation. The CSS reveal-on-load animation, being plain CSS, is separately covered by the existing rule
and confirmed accordingly.

**Preserved on purpose:**
- Deep links and cross-reference clicks (`[§N.M](#anchor)`) now call a new `openAncestorSection()` before
  scrolling, so clicking a link into a collapsed section opens it first rather than scrolling toward a
  zero-height hidden target.
- Added a `toggle` event listener per section (fires regardless of *how* `open` changed) to keep `aria-expanded`
  and inline animation styles in sync even when a section is opened by a path this file doesn't control directly
  — e.g. the browser's own find-in-page mechanism force-opening a closed section to reveal a match.
- Added one small "Expand all sections" / "Collapse all sections" control in the page header (`docs.html`) for
  the read-straight-through use case, toggling all sections instantly (no stagger — animating 16+ sections at
  once would be noise, not polish) — this wasn't explicitly requested in the brief but follows directly from it
  and costs one small button.

**Verification (no real browser available in this sandbox, so verified as rigorously as tooling allowed):**
- Ran the *actual* `buildAccordionSections` logic against the real, current `external.md` through real `marked.js`
  (not synthetic test markup): 16 sections produced from 16 real `##` headings, byte-identical `textContent`
  before/after restructuring, all 3 real Mermaid blocks preserved intact, zero empty section bodies.
- Re-ran against the real *combined* external+internal admin view (27 sections) — internal's SQL code block and
  phase table inside the new §2 lifecycle section confirmed to survive the restructuring intact.
- Ran a full end-to-end interaction test: loaded the real `docs.html` + real `docs.js` + real `external.md` into
  a jsdom window, fired `DOMContentLoaded`, and simulated real user actions — clicking "Expand all" (confirmed
  all 16 open, button label updates), clicking a single section summary (confirmed only that one toggles,
  siblings unaffected), and clicking a real H3-level TOC link (confirmed its parent section opens from closed
  before the scroll is attempted).
- Verified Mermaid's CDN-blocked fallback path (this sandbox's actual network reality) still works correctly
  with the new structure — all 3 diagram blocks end up inside their correct accordion section with source intact,
  even without `mermaid.js` available to render them.
- Cross-checked every CSS class name string used in `docs.js` against `index.css` selectors and vice versa —
  exact match, no typos.
- Parsed the full `index.css` with a real CSS parser (not brace-counting) — 372 rules, zero syntax errors.

**Bug caught and fixed during this pass, unrelated to the feature itself:** the CSS append introduced `\r\r\n`
(doubled carriage returns) across the entire file — a double-conversion bug from combining a manual
`\n`→`\r\n` string replace with an *additional* `newline='\r\n'` file-write mode, each independently converting
`\n` to `\r\n` and compounding on top of each other. Caught by an explicit byte-level line-ending check (a
verification step added to this session specifically because of line-ending bugs caught in earlier sessions),
fixed by normalizing the whole file to a clean single `\n` baseline before a single, explicit CRLF conversion.
Re-verified clean (0 doubled-CR, 0 bare LF) and re-ran the CSS parser + full integration test afterward to
confirm the fix didn't regress anything.

**Scope:** confined entirely to `docs.html`/`docs.js`/`index.css`'s new `.docs-section*`/`.docs-toggle-all-btn`
rules. No other page's markup, scripts, or existing CSS rules were modified.
