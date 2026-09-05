---
last_verified: 2026-09-02
verified_against: HEAD
owner: system
status: current
---

# Technical Debt & Discrepancies

## Schema Drift Issues

### DRIFT-001: KB tables not in schema.sql
| Field | Value |
|---|---|
| ID | DRIFT-001 |
| Severity | High |
| Component | `areos/db/` |
| Description | KB tables (`kb_*`, `knowledge`) are not defined in the canonical `schema.sql`. They are dynamically created during the KB build process. |
| Evidence | `areos/db/schema.sql` lacks KB tables. `areos/kb/build_kb.py` defines them via `SCHEMA_SQL` on execution. |
| Status | Open |
| Workaround | Run `build_kb.py` to correctly initialize the KB schema. |
| Recommended Resolution | Consolidate the KB schema definition into `schema.sql` or establish a unified schema generation mechanism. |

### DRIFT-002: jobs table created by artifacts.py but not in schema.sql
| Field | Value |
|---|---|
| ID | DRIFT-002 |
| Severity | Low |
| Component | `areos/db/schema/` |
| Description | The initial claim is partially incorrect: the `jobs` table *is* present in the generated `schema.sql`. |
| Evidence | `areos/db/schema/artifacts.py` defines the `jobs` table schema, and `areos/db/schema.sql` successfully includes `CREATE TABLE IF NOT EXISTS jobs`. |
| Status | Tracked |
| Workaround | None needed. |
| Recommended Resolution | Close the issue, as the table is correctly synchronized with `schema.sql`. |

### DRIFT-003: migrate_audit_tables.py adds columns not in schema.sql
| Field | Value |
|---|---|
| ID | DRIFT-003 |
| Severity | Medium |
| Component | `areos/db/` |
| Description | `migrate_audit_tables.py` dynamically applies raw DDL patches that are not present in the canonical `schema.sql` definitions (e.g., dynamically creating the `kb_meta` table). |
| Evidence | `areos/db/migrate_audit_tables.py` uses `CREATE TABLE IF NOT EXISTS kb_meta`, which is completely absent from `schema.sql`. |
| Status | Open |
| Workaround | Ensure `migrate_audit_tables.py` is always run after initializing the database. |
| Recommended Resolution | Move the `kb_meta` table definition into `areos/db/schema/artifacts.py` and regenerate `schema.sql`. |

## Technical Debt

### DEBT-001: Synchronous audit execution
| Field | Value |
|---|---|
| ID | DEBT-001 |
| Severity | High |
| Component | `areos/jobs/` |
| Description | Audit execution runs synchronously, making long audits approach or hit HTTP timeout limits. |
| Evidence | `areos/jobs/__init__.py` is empty. The `audit_orchestrator` runs synchronously within the HTTP request cycle. |
| Status | Open |
| Workaround | Increase server and reverse-proxy HTTP timeouts. |
| Recommended Resolution | Implement an asynchronous job queue (e.g., using standard background tasks or a basic worker process). |

### DEBT-002: No background job queue despite scaffolded jobs/ directory
| Field | Value |
|---|---|
| ID | DEBT-002 |
| Severity | Medium |
| Component | `areos/jobs/` |
| Description | The `jobs/` directory exists as a structural scaffold, but no background worker or queue polling mechanism is implemented. |
| Evidence | The `areos/jobs/` directory contains only an empty `__init__.py`. |
| Status | Open |
| Workaround | None. |
| Recommended Resolution | Build a lightweight polling worker that processes tasks queued in the existing `jobs` database table. |

### DEBT-003: Admin token is static
| Field | Value |
|---|---|
| ID | DEBT-003 |
| Severity | Medium |
| Component | `areos/api/dependencies.py` |
| Description | Administrative API authentication relies on a single, static environment variable token with no built-in rotation mechanism. |
| Evidence | `areos/api/dependencies.py` retrieves `_API_TOKEN = os.environ.get("AREOS_API_TOKEN")` and validates it purely using `hmac.compare_digest`. |
| Status | Open |
| Workaround | Rotate the token by changing the environment variable and restarting the application. |
| Recommended Resolution | Implement dynamic token management, multi-token support, or external SSO integration. |

### DEBT-004: Moz/Ahrefs authority integrations scaffolded but non-functional
| Field | Value |
|---|---|
| ID | DEBT-004 |
| Severity | Low |
| Component | `areos/auditors/authority_auditor.py` |
| Description | Integration endpoints for Moz and Ahrefs metrics exist but contain no actual logic. |
| Evidence | `fetch_moz_metrics()` and `fetch_ahrefs_metrics()` in `areos/auditors/authority_auditor.py` simply return `None`. |
| Status | Accepted |
| Workaround | Fall back to the Open PageRank implementation or deterministic heuristics. |
| Recommended Resolution | Complete the implementations for these third-party integrations or remove the dead code stubs. |

### DEBT-005: No headless UI tests
| Field | Value |
|---|---|
| ID | DEBT-005 |
| Severity | Medium |
| Component | `tests/` |
| Description | The testing suite completely lacks headless browser or UI integration tests. |
| Evidence | Listing the `tests/` directory reveals 41 test files (e.g., `test_qa_regression_suite.py`), all of which are backend or API unit/integration tests. |
| Status | Open |
| Workaround | Perform manual regression testing for the UI layer. |
| Recommended Resolution | Integrate Playwright or Selenium to cover core user journeys in the frontend. |

## Coverage Gaps

### GAP-001: No multi-tenant isolation
| Field | Value |
|---|---|
| ID | GAP-001 |
| Severity | Critical |
| Component | `areos/db/schema.sql` |
| Description | The system uses a single-tenant design. The database schema has no structural boundaries for multi-tenant data. |
| Evidence | An inspection of `areos/db/schema.sql` reveals that no tables contain a `tenant_id` or similar isolation mechanism. |
| Status | Open |
| Workaround | Deploy distinct API and DB instances per tenant. |
| Recommended Resolution | Add `tenant_id` columns to all domain models and enforce tenant boundaries at the data access layer. |

### GAP-002: No request signing
| Field | Value |
|---|---|
| ID | GAP-002 |
| Severity | Medium |
| Component | `areos/api/dependencies.py` |
| Description | Client requests are not cryptographically signed to prevent tampering or replay attacks. |
| Evidence | `verify_admin` relies solely on a static Bearer token in the `Authorization` header without verifying request payload signatures. |
| Status | Open |
| Workaround | Mandate strict HTTPS/TLS to protect the transport layer. |
| Recommended Resolution | Implement HMAC-based request signing for all sensitive API endpoints. |

### GAP-003: No automated schema migration tool
| Field | Value |
|---|---|
| ID | GAP-003 |
| Severity | High |
| Component | `areos/db/migrate_audit_tables.py` |
| Description | Migrations are applied via a custom Python script executing `CREATE TABLE IF NOT EXISTS` and `try/except` `ALTER TABLE` operations, lacking robust versioning. |
| Evidence | `areos/db/migrate_audit_tables.py` implements manual SQL statement execution rather than utilizing standard tools like Alembic. |
| Status | Tracked |
| Workaround | Carefully test manual migration scripts against production-like data before deployment. |
| Recommended Resolution | Adopt Alembic for proper schema versioning, rollbacks, and history tracking. |

### GAP-004: No rate limiting on admin endpoints
| Field | Value |
|---|---|
| ID | GAP-004 |
| Severity | Medium |
| Component | `areos/api/main.py` |
| Description | The API does not enforce rate limiting on administrative or high-cost endpoints, exposing the system to resource exhaustion. |
| Evidence | `areos/api/main.py` defines payload size limits (`BodySizeLimitMiddleware`) but includes no rate-limiting middleware (like `slowapi`). |
| Status | Open |
| Workaround | Enforce rate limiting externally via an API Gateway or WAF (e.g., Cloudflare, Nginx). |
| Recommended Resolution | Implement `slowapi` or an equivalent rate limiter directly within the FastAPI application. |

### GAP-005: CORS allows localhost in development
| Field | Value |
|---|---|
| ID | GAP-005 |
| Severity | Low |
| Component | `areos/api/main.py` |
| Description | The CORS configuration explicitly permits `localhost:8000` and `localhost:3000` to accommodate development flows. |
| Evidence | `CORSMiddleware` in `main.py` hardcodes `allow_origins` to localhost URLs. The code comments acknowledge this is primarily for local dev servers. |
| Status | Accepted |
| Workaround | The shipped UI is served same-origin, so these rules do not actively compromise standard usage. |
| Recommended Resolution | Shift CORS configuration to environment variables so it can be strictly disabled in production environments. |

## Documentation/Code Divergence

An inspection of `docs/internal_legacy.md` highlights several claims that diverge from the current reality of the codebase:

1. **Schema Divergence:** `internal_legacy.md` notes that there are 17 claim types in the DB despite the specification mandating only 5 (`empirical`, `operational`, `policy`, `heuristic`, `outcome`).
2. **Hardcoded Knowledge:** The legacy document states that AP-03 (Schema/JSON-LD Extraction) is explicitly omitted from the `audited_stages` array logged in the database, meaning the schema extraction phase is missing from the audit trail.
3. **Synthesis Engine Status Check:** The documentation correctly identifies that `areos/auditors/synthesis_engine.py` hardcodes the query `claim_status="active"`, entirely bypassing contested or nuanced claims before the QA gate processes them.
4. **LLM Waterfall Fallbacks:** `internal_legacy.md` indicates that if live LLM APIs fail during `citation_sampler.py`, there is no offline fallback routine. The system does not emit a `CITATION_UNAVAILABLE` code, representing an unresolved architecture gap.
