# MASTER ARCHITECTURAL DIRECTIVE: ROUND THREE CONVERGENCE

**Target System:** Citeable AEOGEO Autonomous Audit Platform (`areos`)  
**Authority:** Elena, CTO & Chief Systems Arbiter  
**Review Board:** Hostile Verifier (Supervisor 1) & Guiding / Authoring Lead (Supervisor 2)  
**Input Grounding:** 5 Deep Domain Reports in `external_audit_packages/Output/Round three/` cross-examined under hostile adversarial red-teaming.  
**Standard:** Strict Karpathy Principles — Reality Grounding, Simplicity First, Surgical Fixes, Zero Hallucinations.

---

## 1. EXECUTIVE CONVERGENCE & RED-TEAM ADVERSARIAL MATRIX

The Hostile Verifier subjected all domain claims to empirical code testing, separating genuine defects from hallucinations and already-mitigated points:

```
╔═════════════════════════════════════════════════════════════════════════════════════════╗
║                  ROUND THREE ADVERSARIALLY VERIFIED DEFECT MATRIX                       ║
╠═════════════════════════════════════════════════════════════════════════════════════════╣
║ 🔴 P0 CRITICAL ARCHITECTURAL DEFECTS:                                                   ║
║ 1. LLM WATERFALL: Timeout Budget Variable Ignored (`providers/__init__.py:126`)         ║
║    → `provider_timeout` computed but not passed to `provider_fn()`; hangs violate 25s.  ║
║ 2. SRE/API: Async Health Check Blocks Event Loop on SQLite Lock (`main.py:194`)         ║
║    → `conn.execute("SELECT 1")` in `async def health_check` blocks the entire loop.     ║
║ 3. SRE/BACKUP: Render Cron Backup Isolated from Production DB (`render.yaml:76`)        ║
║    → `type: cron` lacks `/data` mount; backups run against empty ephemeral disk.        ║
║ 4. APPSEC: Closing Tag Escape in Prompt Tag Isolation (`synthesis_pipeline.py:174`)     ║
║    → `</untrusted_crawled_data>` inside crawled text breaks isolation boundary.         ║
║ 5. APPSEC: SSRF IPv4-Mapped IPv6 Subnet Bypass (`areos/util/ssrf.py:52-57`)             ║
║    → `ip.ipv4_mapped` (e.g. `::ffff:169.254.169.254`) bypasses IPv4 denylist.          ║
║                                                                                         ║
║ 🟠 P1 HIGH INTEGRITY & ALGORITHMIC RESILIENCE:                                          ║
║ 6. KB/RAG: Dimension Drift Fallback Uses Stale Threshold (`router.py:299-314`)          ║
║    → Fallback embeds via server model but evaluates using client model's threshold.     ║
║ 7. SCHEMA: FAQPage Skipped When Secondary in `@type` List (`schema_validator.py:279`)   ║
║    → `schema_type == "FAQPage"` only checks index 0; skips `["Page", "FAQPage"]`.       ║
║ 8. LLM/SYNTHESIS: Stale/Contested Metadata Loss & Grounder Erasure (`synthesis_pipeline`)║
║    → Drops `contested_reason`/`stale_since`; grounder prompt omits flags completely.    ║
║ 9. CODE SANITY: ReDoS in Tag Pairing Regexes (`content_format_auditor.py:66-68`)       ║
║    → Unclosed tags cause polynomial backtracking over 1MB payload caps.                 ║
║ 10. APPSEC/ZERO-RETENTION: Plaintext API Keys in LRU Heap (`byok.py:56`)                ║
║    → `@lru_cache` stores live plaintext keys in long-lived memory dump surfaces.        ║
║ 11. DEVOPS: Typo with Spaces in `.dockerignore:39` (`* . d b *`)                       ║
║    → Fails to ignore SQLite files during `docker build`.                                ║
║ 12. SRE/PERF: `TargetIPAdapter` PoolManager Socket Leak (`ssrf.py:107-109`)             ║
║    → Re-instantiating adapter on every redirect hop leaks connection pools.             ║
║ 13. INFRA: Uvicorn `--forwarded-allow-ips` on Render Dynamic Reverse Proxy (`Dockerfile`)║
║    → `127.0.0.1` ignores Render's edge XFF header; scopes all clients to one proxy IP.  ║
║                                                                                         ║
║ 🟡 P2 MEDIUM A11Y & POLISH:                                                             ║
║ 14. UI/A11Y: Missing ARIA Live Regions on Toasts (`api.js:15`, `byok.js:53`)           ║
║ 15. UI/A11Y: Mobile Touch Targets Below 44px (`index.css:1637`, `785`)                 ║
║ 16. UI/A11Y: Contrast Ratio on Disabled / Locked Stepper Labels (`index.css:1630`)      ║
║                                                                                         ║
║ 🟢 VERIFIED ALREADY MITIGATED / FALSIFIED:                                              ║
║ • `funnelText` crash: 100% FIXED & VERIFIED across all 10 states.                       ║
║ • Decompression Bombs & XML XXE: 100% PROTECTED via `safe_get` & `defusedxml`.          ║
║ • "Top-level @graph recursion": FALSIFIED/HALLUCINATION (traversal is iterative).       ║
╚═════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. ARCHITECTURE DECISION RECORDS (ROUND THREE ADRs)

### [ADR-R3-01] Forward Dynamic Timeout to Provider Execution (`TASK-R3-01`)
- **Decision:** Pass `timeout=provider_timeout` into `provider_fn(...)` in `areos/llm/providers/__init__.py:127`.

### [ADR-R3-02] Non-Blocking Database Ping in Health Check (`TASK-R3-02`)
- **Decision:** Wrap database health check in `anyio.to_thread.run_sync` or perform lightweight file/state check in `areos/api/main.py:194`.

### [ADR-R3-03] Persistent Disk Attachment for Backup Cron (`TASK-R3-03`)
- **Decision:** Mount `areos-data` disk to the `areos-backup` cron service in `render.yaml` with shared `/data` path.

### [ADR-R3-04] XML Tag Escape in Prompt Data Framing (`TASK-R3-04`)
- **Decision:** Escape `</untrusted_crawled_data>` or sanitize angle brackets before injecting crawled strings into `synthesis_pipeline.py`.

### [ADR-R3-05] Explicit IPv4-Mapped IPv6 Unmapping & Validation (`TASK-R3-05`)
- **Decision:** In `areos/util/ssrf.py::_validate_ip`, check `if ip.ipv4_mapped: _validate_ip(str(ip.ipv4_mapped))` before admitting connection.

### [ADR-R3-06] Dynamic Threshold Recalibration on Dimensional Fallback (`TASK-R3-06`)
- **Decision:** In `areos/kb/router.py::_rag_search`, update `threshold = get_thresholds_for_model(server_model).get("primary", 0.82)` when falling back.

### [ADR-R3-07] Union Array Check for Multi-Typed Schema Specializations (`TASK-R3-07`)
- **Decision:** In `areos/auditors/schema_validator.py`, check `if "FAQPage" in schema_types:` to properly validate nested FAQ structures regardless of array index.

### [ADR-R3-08] Preserve Stale/Contested Metadata in Synthesis & Grounding (`TASK-R3-08`)
- **Decision:** Forward `contested_reason` and `stale_since` in `_build_synthesizer_input` and include flags in `grounder_input` in `synthesis_pipeline.py`.

### [ADR-R3-09] Parser-Based Tag Stripping for Content Format & Cloaking (`TASK-R3-09`)
- **Decision:** Replace remaining tag-pairing regexes in `content_format_auditor.py` and `cloaking_detector.py` with `html_cleaner.py`.

### [ADR-R3-10] Purge Plaintext Key Memory Caching (`TASK-R3-10`)
- **Decision:** Remove `@lru_cache` from `_verify_api_key_cached` in `areos/api/routers/byok.py`, ensuring keys exist only ephemerally within the request frame.

### [ADR-R3-11] Fix Space Typo in `.dockerignore` (`TASK-R3-11`)
- **Decision:** Change `* . d b *` to `*.db*` in `.dockerignore:39`.

### [ADR-R3-12] Close Previous Adapters in Redirect Traversals (`TASK-R3-12`)
- **Decision:** Call `adapter.close()` before mounting a new `TargetIPAdapter` in `areos/util/ssrf.py:107`.

### [ADR-R3-13] Configure Render Edge Forwarded IP Trust (`TASK-R3-13`)
- **Decision:** Set `--forwarded-allow-ips='*'` in `Dockerfile` for Render production deployment.

### [ADR-R3-14] Enforce WCAG A11y Toast Live Regions & 44px Touch Targets (`TASK-R3-14`)
- **Decision:** Add `aria-live="polite"` to toast creation in `api.js`/`byok.js` and enforce `min-height: 44px` in `index.css`.

---

## 3. ATOMIC TASK REGISTRY (tasks.md)

| Task ID | Severity | Module | File & Lines | Description | Acceptance Criteria |
|---|---|---|---|---|---|
| `TASK-R3-01` | P0 | LLM Engine | `areos/llm/providers/__init__.py:126` | Forward `provider_timeout` into `provider_fn` | Upstream hangs terminate within budget |
| `TASK-R3-02` | P0 | API/SRE | `areos/api/main.py:194` | Non-blocking threadpool run for health DB ping | Health check never blocks event loop |
| `TASK-R3-03` | P0 | SRE/DevOps | `render.yaml:76` | Mount persistent disk on backup cron service | Cron backs up real `/data/areos.db` |
| `TASK-R3-04` | P0 | AppSec | `areos/llm/synthesis_pipeline.py:174` | Escape `</untrusted_crawled_data>` in inputs | Tag breakout payloads neutralized |
| `TASK-R3-05` | P0 | AppSec | `areos/util/ssrf.py:52` | Unmap and revalidate `ip.ipv4_mapped` | `::ffff:169.254.169.254` blocked |
| `TASK-R3-06` | P1 | KB/RAG | `areos/kb/router.py:305` | Recalibrate similarity threshold on server re-embed | Correct server threshold applied |
| `TASK-R3-07` | P1 | Schema | `areos/auditors/schema_validator.py:279` | `if "FAQPage" in schema_types:` | Multi-typed FAQPage validated |
| `TASK-R3-08` | P1 | Synthesis | `areos/llm/synthesis_pipeline.py:165,282` | Forward stale/contested metadata to Grounder | Flags retained in narrative |
| `TASK-R3-09` | P1 | Code Sanity | `content_format_auditor.py` & `cloaking_detector.py` | Migrate to `html_cleaner.py` | Zero regex catastrophic backtracking |
| `TASK-R3-10` | P1 | Security | `areos/api/routers/byok.py:56` | Remove `@lru_cache` on plaintext keys | Zero plaintext keys retained in heap |
| `TASK-R3-11` | P1 | DevOps | `.dockerignore:39` | Change `* . d b *` to `*.db*` | SQLite files excluded from build |
| `TASK-R3-12` | P1 | SRE | `areos/util/ssrf.py:107` | Close existing adapter before mounting new | Socket pool leaks eliminated |
| `TASK-R3-13` | P1 | Infra | `Dockerfile:40` | Set `--forwarded-allow-ips='*'` for Render | Client IPs correctly resolved from XFF |
| `TASK-R3-14` | P2 | UI/A11y | `api.js`, `byok.js`, `index.css` | Toast `aria-live` & 44px touch targets | WCAG 2.1 A11y standards met |
