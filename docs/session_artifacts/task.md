# Citeable V2 — Implementation Tasks

## Phase 1 — Foundation (`areos/kb/` module + corpus load)
- [x] Create `areos/kb/` directory structure
- [x] Copy validated corpus from `Final_Audit_Extract` into `areos/kb/corpus/`
- [x] Write `areos/kb/__init__.py`
- [x] Write `areos/kb/models.py` (Pydantic models)
- [x] Write `areos/kb/build_kb.py` (JSONL → SQLite + embeddings)
- [x] Write `areos/kb/embeddings.py` (BYOK embedding waterfall)
- [x] Write `areos/kb/router.py` (Knowledge Router — full implementation)
- [x] Create `claims` SQL VIEW for backwards compatibility
- [x] Write `areos/kb/README.md`
- [x] Copy `DECISIONS.md` into `areos/kb/`
- [x] Run `build_kb.py` — 202 records, 199 evidence, 114 sources, 50 check codes ✓
- [x] Run existing tests — zero regressions

## Phase 2 — Wire Deterministic Path
- [x] Replace `PRIORITY_SCORES` dict → DB query via `_load_priority_scores()`
- [x] Replace `REMEDIATION_TEXT` dict → GUIDANCE records via `_load_remediation_text()`
- [x] Enrich `Recommendation` dataclass with 7 evidence fields
- [x] Wire Knowledge Router into `_build_automated_recommendations()`
- [x] Pass `client_keys` through `synthesise()` → `_build_automated_recommendations()`
- [x] Update `findings_to_claims.py` → query `kb_check_code_map` with legacy fallback
- [x] Fix `conn.close()` MF-11 violation in `synthesise()`
- [x] Write `tests/test_kb_parity.py` — 11 tests, ALL PASSED

## Phase 3 — RAG (Three Tiers, BYOK-Native)
- [x] Implement BYOK embedding waterfall in `embeddings.py` (Phase 1)
- [x] Pre-compute corpus embeddings in `build_kb.py` (embed_corpus + --embed flag)
- [x] Implement 3-tier RAG in `router.py` (Phase 1)
- [x] Wire RAG fallback into `findings_to_claims.py` (UNMAPPED → semantic search)
- [x] Write `tests/test_rag.py` — 16 tests, ALL PASSED
- [x] Combined regression: 27/27 tests passed

## Phase 4 — Knowledge API + Knowledge Explorer (UI)
- [x] Write `areos/api/routers/knowledge.py` (6 endpoints)
- [x] Register in `areos/api/main.py`
- [x] Knowledge Explorer (UI) evolution from Claims Browser (`knowledge_explorer.html` & `knowledge_explorer.js`)
- [x] Update Cmd+K palette and sidebar in `nav.js` to point to V2 UIwer with evidence chains
- [x] Update Cmd+K palette to search knowledge
- [x] Write `tests/test_knowledge_api.py`

## Phase 5 — Enriched LLM Pipeline + Report
- [x] Enrich `_build_synthesizer_input()` with evidence chains
- [x] Update LLM system prompts
- [x] Upgrade remediation card rendering in `studio.js`
- [x] Upgrade `exportExecutiveReport()` with source citations
- [x] Write `tests/test_synthesis_enrichment.py`

## Phase 6 — Temporal Governance + Contested Knowledge
- [x] Implement stale record detection
- [x] Surface contested status in router degradation
- [x] Update UI to visually flag contested/stale recordswledge Explorer
- [ ] Write `tests/test_temporal.py`, `tests/test_contested.py`

## Phase 7 — Cleanup + Dead Code Removal
- [x] Remove old dicts from `synthesis_engine.py`
- [x] Remove `_CHECK_CODE_MAPPINGS` from `ingest_claims.py`
- [x] Add 14 MANUAL_REMEDIATION_TEXT entries as GUIDANCE records
- [x] Full regression test

## Phase 8 — Documentation
- [x] Update `internal.md` (11 sections)
- [x] Update `external.md` (9 sections)
- [x] Create `areos/kb/GOVERNANCE.md`, `CHECK_CODES.md`, `ARCHITECTURE.md`
- [x] UI text updates (7 string changes)
- [x] Update `CHANGELOG.md`
