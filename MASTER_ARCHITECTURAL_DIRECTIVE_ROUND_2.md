# MASTER ARCHITECTURAL DIRECTIVE: ROUND TWO CONVERGENCE

**Target System:** Citeable AEOGEO Autonomous Audit & Knowledge Platform (`areos`)  
**Authority:** Elena, CTO & Principal Systems Architect  
**Review Board:** Master Technical Verifier (Supervisor 1) & Principal Systems Architect (Supervisor 2)  
**Input Grounding:** 100% verified findings from 5 Domain Specialist Subagents across all Round 2 reports.  
**Operating Standard:** Strict Karpathy Principles — Grounded Reality, Zero Fluff, Simplicity First, Deterministic Verification Gates.

---

## 1. EXECUTIVE CONVERGENCE & VERIFIED DEFECT ARBITRATION

All findings have been forensically verified against the codebase by the 5-agent domain team and cross-examined by Supervisor 1. The ground-truth defects are categorized below:

```
╔═════════════════════════════════════════════════════════════════════════════════════════╗
║                      ROUND TWO MASTER VERIFIED DEFECT ARBITRATION                       ║
╠═════════════════════════════════════════════════════════════════════════════════════════╣
║ 🔴 P0 BLOCKERS (IMMEDIATE RELEASE BLOCKERS):                                            ║
║ 1. UI/UX: `funnelText` ReferenceError (`areos/ui/studio.js:152`)                        ║
║    → Crashes audit completion handler; no user can ever see an audit score.             ║
║ 2. SRE/INFRA: Render Starter (512MB RAM) Concurrency Saturation (`Dockerfile:41`)       ║
║    → `--limit-concurrency 100` guarantees OOM-kills on 0.5 vCPU / 512MB instances.     ║
║ 3. SRE/OPS: Missing Scheduled Backup Job in `render.yaml`                               ║
║    → `scripts/backup_db.py` exists but is not scheduled as a Render Cron service.       ║
║ 4. LLM/API: Waterfall Time Budget Overrun (`areos/llm/providers/__init__.py:120`)      ║
║    → Budget checked only between providers; synchronous hangs violate the 25s ceiling. ║
║ 5. APPSEC: Indirect Prompt Injection via JSON-LD `name` (`entity_verifier.py:183`)      ║
║    → `html.escape` only neutralizes DOM tags; natural-language injection reaches LLM.   ║
║ 6. APPSEC: SSRF TOCTOU / Hostname Rebinding in `providers/__init__.py`                  ║
║    → IP resolved for validation, but raw hostname passed to `_make_request()`.          ║
║                                                                                         ║
║ 🟠 P1 HIGH PRIORITY (CORE INTEGRITY & SECURITY):                                        ║
║ 7. UI/UX: Secrets & Bearer Tokens Leaked to DevTools Console (`areos/ui/api.js:78`)    ║
║ 8. APPSEC: Spoofable IP Rate Limiting under `--forwarded-allow-ips='*'` (`Dockerfile`) ║
║ 9. CODE SANITY: Deep JSON Nesting Recursion Crash (`audit_orchestrator.py:214`)         ║
║ 10. CODE SANITY: O(n²) Regex ReDoS Vulnerabilities in 6 auditor engines                ║
║ 11. SRE: Synchronous `/api/health` Starvation in AnyIO 40-token limiter (`main.py:194`)║
║ 12. KB/RAG: Multi-Typed Schema `@type` List Resolution Bug (`schema_validator.py:205`) ║
║ 13. KB/RAG: Dimensional Mismatch & Missing Re-Embed Fallback (`router.py:295`)          ║
║ 14. CODE SANITY: Unbounded & Unlocked Rate Limit Dict in `byok.py:24`                  ║
║ 15. UI/UX: Hardcoded "Mad Marketers" Mock Data in `studio.js:122`                       ║
║ 16. UI/UX: Missing Mobile Nav Topbar Trigger on 4 Pages (`nav.js:281`)                 ║
║                                                                                         ║
║ 🟡 P2 MEDIUM (STABILITY, RESILIENCE & A11Y):                                            ║
║ 17. APPSEC: Silent Fallback to Vulnerable ElementTree (`sitemap_auditor.py:18-21`)     ║
║ 18. APPSEC: Uncapped Fetch / Memory Bomb in `research_service.py` & `citation_sampler.py`║
║ 19. APPSEC: Raw `urlopen` SSRF Bypass in `authority_auditor.py:82`                      ║
║ 20. CODE SANITY: Connection Pool Churn in `safe_get()` (new Session per redirect hop)  ║
║ 21. DEVOPS: Stale `*.db` Files Not Excluded in `.dockerignore`                         ║
║ 22. KB/RAG: Cluster Overlap & Stale/Contested LLM Behavioral Prompts Missing            ║
║ 23. CODE SANITY: Thread-Local SQLite Connection Lifecycle vs Sync Worker Threads       ║
║ 24. CODE SANITY: Unguarded `FAQPage` Recursion in `schema_validator.py`                ║
║ 25. UI/UX: Broken Layout in `case_study.html` & Missing A11y Touch Targets / ARIA       ║
║                                                                                         ║
║ 🟢 P3 POLISH:                                                                           ║
║ 26. DEVOPS: Extraneous `curl` in Dockerfile.                                            ║
║ 27. CODE SANITY: Dead `get_thresholds_for_model()` & Unused `import re`.                ║
║ 28. KB: 4 Orphaned GUIDANCE Records (`KG-005`, `KG-006`, `KG-009`, `KG-012`).          ║
╚═════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. ARCHITECTURE DECISION RECORDS (ROUND TWO ADRs)

### [ADR-R2-01] Eliminate `funnelText` ReferenceError in `studio.js` (P0)
- **Decision:** Declare `const funnelText = funnelSelect ? (funnelSelect.options[funnelSelect.selectedIndex]?.text || funnelSelect.value) : "All Funnel Stages";` before calling `displayStudioResults()`.

### [ADR-R2-02] Scale Concurrency for Render Starter 512MB Constraints (P0)
- **Decision:** Set `--limit-concurrency 20` in `Dockerfile` to strictly prevent heap allocation over 300MB, avoiding Linux cgroup OOM-kills.

### [ADR-R2-03] Provision Production Scheduled Backup Cron Service (P0)
- **Decision:** Add a `type: cron` service definition to `render.yaml` executing `python scripts/backup_db.py` every 6 hours.

### [ADR-R2-04] Enforce Strict Waterfall Time-Budget Timeouts (P0)
- **Decision:** Calculate remaining time budget per provider attempt: `provider_timeout = min(timeout, max(1.0, time_budget_seconds - elapsed))` in `areos/llm/providers/__init__.py`.

### [ADR-R2-05] Natural-Language Isolation for Crawled Content in Synthesis (P0)
- **Decision:** Truncate untrusted JSON-LD strings (max 120 chars), sanitize whitespace, and wrap all page-extracted text inside `<untrusted_crawled_data>` XML blocks with explicit system-prompt prohibition on instruction overrides.

### [ADR-R2-06] Eliminate SSRF TOCTOU / Hostname Rebinding in BYOK Providers (P0)
- **Decision:** Pin resolved IP address into the HTTP adapter pool manager directly during pre-flight in `areos/llm/providers/__init__.py`.

### [ADR-R2-07] Strip Credential Logging in `areos/ui/api.js` (P1)
- **Decision:** Remove `console.log("OUTGOING HEADERS:", headers)` completely.

### [ADR-R2-08] Secure Forwarded IP Parsing in Dockerfile (P1)
- **Decision:** Restrict `--forwarded-allow-ips` to Render internal reverse-proxy CIDRs rather than `'*'`.

### [ADR-R2-09] Guard Deep JSON Nesting against `RecursionError` (P1)
- **Decision:** Wrap `json.loads` in `audit_orchestrator.py:214` with `except (json.JSONDecodeError, ValueError, RecursionError):`.

### [ADR-R2-10] Centralize O(N) Parser-Based HTML Extraction (P1)
- **Decision:** Implement `areos/util/html_cleaner.py` using BeautifulSoup/HTMLParser for $O(N)$ single-pass tag stripping, replacing backtracking regexes across all 6 auditor modules.

### [ADR-R2-11] Convert `/api/health` to `async def` (P1)
- **Decision:** Declare `@app.get("/api/health") async def health_check()` to execute on the event loop without threadpool queueing.

### [ADR-R2-12] Support Multi-Typed Schema `@type` List Unions (P1)
- **Decision:** Evaluate the union of schema rules across all declared `@type` array elements in `schema_validator.py`.

### [ADR-R2-13] Implement Model Dimension Check & Re-Embed Fallback (P1)
- **Decision:** On embedding dimension mismatch in `router.py::_rag_search`, invoke server-key fallback re-embedding per D-015 before falling back to `INSUFFICIENT`.

### [ADR-R2-14] Thread-Safe Bounded LRU Cache for `byok.py` Rate Limiting (P1)
- **Decision:** Port `threading.Lock()` + 10,000 entry LRU eviction from `audit.py` into `byok.py`.

### [ADR-R2-15] Remove Mock Data & Fix Mobile Navigation / Layout (P1/P2)
- **Decision:** Dynamically derive `sample_content` from crawled text in `studio.js`, inject mobile hamburger into `.main-content` if `.topbar` is absent, and wrap `case_study.html` inside `.app-container`.

---

## 3. NON-NEGOTIABLE ARCHITECTURAL INVARIANTS

1. **Zero-Trust Input Lifecycle:** All external data (crawled HTML, JSON-LD, user notes) MUST be bounded by character limits and isolated in structural XML tags before entering LLM synthesis prompts.
2. **Deterministic Time-Bounds:** Every outbound network call MUST enforce a finite, cascading timeout.
3. **Finite Recursion & Depth Caps:** All recursive JSON/XML/HTML traversals MUST contain hardcoded depth limits ($\le 5$) and trap `RecursionError`.
4. **Memory Constraint Compliance:** All concurrency parameters MUST be sized for the 512MB RAM / 0.5 vCPU Starter baseline tier.
5. **Connection Pooling Invariant:** Outbound HTTP operations MUST reuse pooled sessions and never instantiate raw sockets inside loop iterations.

---

## 4. ATOMIC TASK REGISTRY (tasks.md)

| Task ID | Severity | Subsystem | File & Lines | Description | Acceptance Criteria |
|---|---|---|---|---|---|
| `TASK-R2-01` | P0 Blocker | UI/UX | `areos/ui/studio.js:150-155` | Declare `funnelText` locally | Audit completes and mounts score dashboard without ReferenceError |
| `TASK-R2-02` | P0 Blocker | Infrastructure | `Dockerfile:41` | Set `--limit-concurrency 20` | Container memory remains < 350MB under 50 req/s load |
| `TASK-R2-03` | P0 Blocker | SRE/DevOps | `render.yaml` | Add `type: cron` backup service | Backup executes every 6h via `scripts/backup_db.py` |
| `TASK-R2-04` | P0 Blocker | LLM Engine | `areos/llm/providers/__init__.py:115-130` | Per-call dynamic timeout budget calculation | Provider hang terminates cleanly within 25s global budget |
| `TASK-R2-05` | P0 Blocker | AppSec | `areos/auditors/entity_verifier.py:183` & `synthesis_pipeline.py` | Sanitize JSON-LD name & wrap in `<untrusted_crawled_data>` | System injection payloads evaluate as literal strings |
| `TASK-R2-06` | P0 Blocker | AppSec | `areos/llm/providers/__init__.py:630-685` | Pin resolved IP in HTTP adapter for BYOK endpoints | TOCTOU / DNS rebinding attempts to private IPs fail |
| `TASK-R2-07` | P1 High | UI/UX | `areos/ui/api.js:78` | Remove `console.log("OUTGOING HEADERS")` | 0 credentials logged to browser console |
| `TASK-R2-08` | P1 High | Infrastructure | `Dockerfile:41` | Restrict `--forwarded-allow-ips` | Spoofed `X-Forwarded-For` ignored |
| `TASK-R2-09` | P1 High | Code Sanity | `areos/auditors/audit_orchestrator.py:214` | Catch `RecursionError` on deep JSON nesting | Malformed deep JSON returns clean `SCHEMA_UNVERIFIABLE` |
| `TASK-R2-10` | P1 High | Performance | `areos/util/html_cleaner.py` [NEW] | Create single-pass O(N) tag cleaner and migrate 6 auditor files | Regex backtracking eliminated; linear time on 5MB input |
| `TASK-R2-11` | P1 High | SRE | `areos/api/main.py:194` | Convert `health_check` to `async def` | `/api/health` returns 200 OK immediately under full thread load |
| `TASK-R2-12` | P1 High | KB/RAG | `areos/auditors/schema_validator.py:205-210` | Support `@type` list unions | `["Organization", "LocalBusiness"]` passes without false UNKNOWN_FIELD |
| `TASK-R2-13` | P1 High | KB/RAG | `areos/kb/router.py:295-305` | Implement server-key re-embed fallback on dimension drift | Dimensional mismatch triggers server fallback rather than dropping RAG |
| `TASK-R2-14` | P1 High | API Layer | `areos/api/routers/byok.py:24-32` | Add `threading.Lock()` + 10,000 LRU eviction | Memory leak eliminated on rotating client IPs |
| `TASK-R2-15` | P1 High | UI/UX | `areos/ui/studio.js:122` | Replace "Mad Marketers" with dynamic crawled snippet | Dynamic snippet submitted |
| `TASK-R2-16` | P1 High | UI/UX | `areos/ui/nav.js:281` | Unconditional mobile menu injection | Mobile menu button visible across all 9 pages |
| `TASK-R2-17` | P2 Medium | AppSec | `areos/auditors/sitemap_auditor.py:18-21` | Fail loud if `defusedxml` missing | Startup validation ensures defusedxml presence |
| `TASK-R2-18` | P2 Medium | AppSec | `areos/services/research_service.py` & `citation_sampler.py` | Route through size-bounded streaming fetchers | Decompression bombs rejected |
| `TASK-R2-19` | P2 Medium | AppSec | `areos/auditors/authority_auditor.py:82` | Replace raw `urlopen` with `safe_get` | SSRF protection enforced on authority lookups |
| `TASK-R2-20` | P2 Medium | Performance | `areos/util/ssrf.py:105` | Reuse connection pool across redirect hops | Socket TIME_WAIT accumulation prevented |
| `TASK-R2-21` | P2 Medium | DevOps | `.dockerignore` | Add `*.db`, `*.db-wal`, `*.db-shm` | Stale databases excluded from production image |
| `TASK-R2-22` | P2 Medium | KB/RAG | `areos/llm/synthesis_pipeline.py` | Add prompt rules for stale/contested evidence flags | LLM hedges appropriately on contested claims |
| `TASK-R2-23` | P2 Medium | Database | `areos/db/connection.py` | Global connection registry cleanup on shutdown | Threadpool worker SQLite connections closed cleanly |
| `TASK-R2-24` | P2 Medium | Code Sanity | `areos/auditors/schema_validator.py` | Add `max_depth=3` recursion limit on `FAQPage` trees | Infinite recursion prevented |
| `TASK-R2-25` | P2 Medium | UI/UX | `areos/ui/case_study.html` & `index.css` | Add `.app-container` wrapper & WCAG 44px touch targets | Layout restored; A11y standards met |
| `TASK-R2-26` | P3 Polish | DevOps | `Dockerfile` | Remove unused `curl` package | Docker image size reduced |
| `TASK-R2-27` | P3 Polish | Code Sanity | `areos/kb/router.py` & `sitemap_auditor.py` | Wire/Prune dead code and unused imports | Clean static analysis |
| `TASK-R2-28` | P3 Polish | KB | `areos/kb/corpus/knowledge.jsonl` | Prune or wire 4 orphaned GUIDANCE records | 100% active ontology reachability |
