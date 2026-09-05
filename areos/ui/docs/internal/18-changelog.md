---
last_verified: 2026-09-02
verified_against: HEAD
owner: system
status: current
---

# Internal Documentation Changelog

## Version 2026.09.02.1 — Initial Release

**Date**: 2026-09-02
**Scope**: Complete rewrite of Citeable internal engineering documentation.

### Created (18 documents)

| Document | Size | Purpose |
|---|---|---|
| `00-orientation.md` | 6KB | System overview, terminology, local dev quick-start |
| `01-architecture.md` | 8KB | Component boundaries, data flow, trust boundaries, invariants |
| `02-repository-map.md` | 31KB | Complete annotated file tree with responsibilities |
| `03-audit-engine.md` | 9KB | Implementation-level audit lifecycle (12 stages) |
| `04-data-model.md` | 11KB | Database schema, ER diagram, schema drift analysis |
| `05-evidence-findings.md` | 10KB | Evidence chain, claims, findings, QA gate, governance |
| `06-scoring.md` | 8KB | Complete LAYER_DEDUCTIONS (59 codes), ACCESS_GATE, invariants |
| `07-ai-llm.md` | 9KB | 11-provider waterfall, BYOK lifecycle, trust boundaries |
| `08-frontend.md` | 11KB | 19 JS modules, 12 HTML pages, state management, design system |
| `09-api-reference.md` | 8KB | Complete endpoint inventory with auth and schemas |
| `10-security.md` | 8KB | Threat model, SSRF deep dive, credential exposure analysis |
| `11-governance.md` | 7KB | Auth, approval workflow, mutation audit trail, auto_apply gate |
| `12-testing-qa.md` | 8KB | 41 test files, invariant mappings, CI pipeline, known gaps |
| `13-operations.md` | 11KB | Deployment, env vars, startup, troubleshooting guide |
| `14-adrs.md` | 16KB | 15 Architecture Decision Records verified against source |
| `15-known-issues.md` | 10KB | 13 issues (DRIFT/DEBT/GAP), each verified against source |
| `16-historical.md` | 9KB | 36 session artifacts classified with provenance links |
| `17-how-to-change.md` | 10KB | Maintainer guide for 7 common modification scenarios |

**Total**: ~190KB across 18 focused documents.

### Superseded

| Document | Status |
|---|---|
| `docs/internal.md` (61KB monolith) | Renamed to `docs/internal_legacy.md`, preserved for reference |

### Methodology

All content was reconstructed from source code via 14 parallel codebase investigations covering:
- Every Python module under `areos/`
- Every JavaScript file under `areos/ui/`
- Complete database schema (`schema.sql` + runtime code)
- All 41 test files
- All 36 session artifacts
- All environment variables, deployment config, and CLI tools

No content was copied from the legacy `internal.md`. Every claim was verified against the authoritative source file.
