# Testing & Verification

This document details the reliability engineering framework for Citeable. Testing goes beyond code path execution to enforce mathematical invariants, semantic synchronization, and database integrity across all subsystems.

## 1. Testing Philosophy

- **Invariants over Coverage:** Tests verify system invariants rather than just execution paths.
- **Mathematical Guarantees:** The scoring system's core mathematical properties are continuously asserted.
- **Semantic Synchronization:** Tests enforce consistency across independent registries to prevent disjoint configurations.
- **Zero External Dependencies:** All LLM calls and live network requests are mocked out during CI to ensure fast, deterministic, and hermetic test runs.

## 2. Scoring Invariants

The scoring test suite (`test_phase3_kb_scoring.py`) asserts that the multi-layered evaluation engine adheres to the following mathematical properties:

- **Global Bounds:** `∀ findings: 5 ≤ overall_score ≤ 98` (The score floor and ceiling are strictly enforced, even under extreme deduction scenarios).
- **Non-Negative Layers:** `∀ layer L: 0 ≤ L.score ≤ L.max_points` (Layers cannot go negative or overflow their maximum point allocation).
- **Point Conservation:** `Σ L.max_points = 100` (The total possible score always equals 100).
- **Access Gate Enforcement:** `If access gate triggered: overall_score ≤ min(triggered_gate_caps)` (Critical blockers like `CLOAKING_DETECTED` instantly cap the maximum achievable score).
- **Determinism:** Scoring operations on identical input arrays consistently yield identical deductions and final scores.

## 3. Semantic Parity Gate

The `test_ci_semantic_parity.py` CI test ensures strict semantic synchronization for 77 distinct check codes across three independent registries:

| Registry | Purpose |
|----------|---------|
| `check_code_to_knowledge_map.json` | Maps check codes to canonical knowledge IDs. |
| `LAYER_DEDUCTIONS` | Assigns each check code a deduction value and target scoring layer. |
| `ACTION_SNIPPETS` | Provides actionable remediation code examples for the UI. |

If a check code is introduced into one registry but omitted from the others, the CI gate fails. This prevents orphaned findings, missing remediations, or un-scored deductions from reaching production.

## 4. QA Gate Verification

The QA regression suite (`test_qa_regression_suite.py`) enforces strict validation logic for UI inputs and systemic behaviors:

- **Claim Validation:** Recommendations with valid, active claims `PASS`.
- **Missing Claims:** Recommendations with missing claim IDs are `REJECTED`.
- **Deprecated/Archived Claims:** Recommendations citing deprecated or archived claims are `REJECTED`.
- **Manual Verdicts:** Findings sourced via manual entry (`source == 'manual'`) bypass automated re-validation and always `PASS`.
- **Database Resilience:** Database failures or lock timeouts result in explicit `REJECTION` rather than a silent failure or default pass.

## 5. Knowledge Base Integrity

The Knowledge Base (KB) build pipeline (`areos/kb/build_kb.py`) maintains structural and referential integrity using an atomic staging process:

- **Schema Validation:** All ingested JSONL records conform to strict Pydantic models (enforcing types, schema, and required fields).
- **Referential Integrity:** Evidence links must reference valid, existing `kid` (knowledge) and `sid` (source) records. Check code mappings must also reference valid knowledge IDs.
- **Atomic Rollouts:** KB construction operates on a staging database. If any ingestion step or integrity check fails, the transaction is rolled back, preventing corrupted or incomplete builds from reaching production.
- **Consistency Checks:** `verify_kb_semantic_parity.py` asserts cross-table parity between check codes and their knowledge backing.

## 6. Deterministic Auditor Tests

The auditor pipeline is tested under strict isolation to verify the deterministic extraction of findings. Key test coverage includes:

### Scoring & Evaluation
- `test_phase3_kb_scoring.py`
- `test_qa_regression_suite.py`
- `test_qa_phase_q1.py` through `test_qa_phase_q5.py`
- `test_qa2_phase_r1.py` through `test_qa2_phase_r5.py`
- `test_qa3_phase_r1.py` through `test_qa3_phase_r5.py`

### Auditor Modules
- `test_cloaking_detector.py`
- `test_competitor_analyzer.py`
- `test_entity_verifier.py`
- `test_freshness_auditor.py`
- `test_media_blindness.py`
- `test_multipage_auditor.py`
- `test_rendering_auditor.py`

### Integration & Pipeline
- `test_phase1_fetch.py`
- `test_phase2_auditors.py`
- `test_phase4_enhancements.py`
- `test_synthesis_enrichment.py`
- `test_rag.py`

### Security & Fuzzing
- `test_security_dom_sweeps.py`
- `test_ssrf_byok_llm_endpoints.py`
- `test_adversarial_stream_fuzzing.py`

## 7. Concurrency & Database Tests

SQLite concurrency is aggressively verified:
- **Thread-Local Connection Isolation:** Enforces strict boundaries to prevent context crosstalk between concurrent operations.
- **WAL Mode Verification:** Validates that Write-Ahead Logging allows readers to never block writers, achieving 0 WAL busy exceptions under high multi-threaded stress.
- **UPSERT Atomicity:** Verifies atomic updates for manual observation overrides.
- **File Locking:** Guarantees serialized file access for parallel changelog approvals.

## 8. What Is NOT Tested

Intellectual honesty regarding system boundaries:

- **LLM Output Quality:** Synthesis content generation is non-deterministic by nature and cannot be reliably asserted in CI.
- **Live API Provider Availability:** Third-party APIs (LLMs, search engines) are mocked in tests to guarantee hermetic execution.
- **Real-World Citation Correlation:** Verification of how findings strictly influence a live model's retrieval ranking requires controlled A/B experiments, not unit tests.
- **Browser Rendering:** Headless browser metrics (Playwright) are omitted from standard CI runs because they require an opt-in heavy environment footprint.
