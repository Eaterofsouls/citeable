# Citeable Architecture & Version History

This page serves as the authoritative record of Citeable's architectural evolution. It documents the versioning schema, the foundational Architecture Decision Records (ADRs) that govern the codebase, and the major structural changes made to support the AI readiness auditing platform.

## Section 1: Version System

Citeable's Knowledge Base adheres to Calendar Versioning (CalVer) in the format `YYYY.MM.DD.N`.
- For same-day updates, the incremental counter `N` increments.
- When a new day begins, the counter resets to `1`.

To retrieve the current Knowledge Base version, operators and external systems can query the endpoint: `GET /api/v1/knowledge/stats`.

## Section 2: Architecture Decision Record

The current architecture is governed by specific decisions explicitly designed to manage LLM non-determinism, secure execution, and enforce knowledge reproducibility. The following key ADRs are implemented across the codebase:

### Knowledge Architecture
- **DEC-03**: The deterministic KB router (`router.py`) walks `kb_check_code_map` candidate rows ordered by priority, automatically skipping deprecated or archived records to find an active record if one exists.
- **DEC-15**: Enables atomic staging database swaps via an in-memory SQLite backup, achieving zero-downtime KB rebuilds.
- **TR-202**: Backing factual records are registered at priority − 5 to ensure primary guidance always takes precedence during deterministic resolution.
- **D5 / Bible §6.4**: Source tiers (T1–T5/T7) are deterministic by source type (e.g., official documentation vs. vendor blogs) and not subject to subjective editorial judgment.

### LLM & Provider Architecture
- **D-008 / D-013**: Zero heavy ML dependencies. RAG and embedding use the BYOK (Bring Your Own Key) waterfall mirroring LLM providers, avoiding `ChromaDB`, `PyTorch`, or `numpy` in the deployment artifact.
- **D-011 / DEC-16**: Calibrated RAG cosine similarity thresholds per embedding model to favor precision. Primary queries require 0.82/0.80, while Enrichment queries require 0.70/0.68.
- **D-014**: Graceful degradation. If no BYOK key is available for embeddings, the system silently skips RAG enrichment and falls back to deterministic-only routing.
- **D-015**: Dimension mismatch protection. If the client's query embedding model does not match the corpus model, it falls back to a server-side key or skips RAG entirely.

### Security Architecture
- **DEC-05 / QA-GAP-2**: A strict 5MB request body size limit is enforced globally as an ASGI middleware.
- **Critical-2**: TargetIPAdapter provides DNS rebinding prevention for outbound crawler or BYOK API requests.
- **SEC-7**: A global exception handler intercepts and strips stack traces from all client HTTP responses to prevent information disclosure.

### Database Architecture
- **D3 / Bible §6.3**: Uses a two-tier context pattern (`write_as()` + SQLite triggers) for robust semantic audit logging of all modifications.
- **INVARIANT-08**: Hard deletes are expressly forbidden via `BEFORE DELETE` triggers in `schema.sql`. Records must transition to `deprecated` or `superseded` statuses.
- **MF-6 / SEC-11**: Implements database-backed idempotency for write endpoints.
- **MF-10**: Live health check endpoint verifies actual database reachability via a thread pool, rather than merely checking if the process is alive.
- **MF-11**: Centralized SQLite connection registry handles predictable lifespan teardown.
- **MF-13**: Thread-local connection caching is utilized per database path.

## Section 3: Major Architectural Evolutions

### Evolution 1: Flat Scoring → Layered Scorecard
- **Before**: The system utilized a single flat formula: `100 - errors×18 - warnings×7`.
- **After**: Implemented a 5-layer weighted model (Access, Schema, Content, Citation, Authority) with per-layer isolation and access gate caps.
- **Why**: The flat formula couldn't express that access issues (like a blocked crawler) should dominate and cap scoring regardless of on-page optimization. The access gate correctly reflects AI ingestion realities.

### Evolution 2: Flat Claims Table → Governed Knowledge Records
- **Before**: A simple `claims` table storing a statement and a status.
- **After**: A rich `knowledge` table featuring evidence chains, source tiers, atomicity rules, temporal tracking, and provenance.
- **Why**: Recommendations must carry their full evidence chain for auditability. Governance requires detailed lifecycle states and temporal staleness tracking.
- **Backward compatibility**: The legacy `claims` table continues to exist as a SQL `VIEW` over the new `knowledge` table, ensuring existing `/api/v1/claims` queries work unchanged.

### Evolution 3: Direct LLM Calls → Three-Step Adversarial Pipeline
- **Before**: A single LLM call to generate the audit synthesis.
- **After**: Synthesizer → Red Teamer → Grounder with forward and reverse waterfalls to maximize cognitive diversity.
- **Why**: Single-model synthesis produced hallucinated statistics and unsupported recommendations. The adversarial pipeline systematically catches and corrects these errors before user presentation.

### Evolution 4: Legacy Manual Verdicts → Structured Observation Wizard
- **Before**: Simple pass/warn/fail verdicts per instruction card.
- **After**: An 11-question structured wizard with conditional visibility, data pre-population, and diagnosis text.
- **Why**: Binary verdicts failed to capture the qualitative reasoning required for the synthesis pipeline. The structured format enables richer human-AI collaboration.
- **Backward compatibility**: Both systems coexist; the synthesis pipeline gracefully falls back from structured observations to verdicts if the observations are empty.

## Section 4: Deprecated Check Codes

Certain check codes have been deliberately deprecated from runtime logic as empirical evidence disproved their value for AI citation readiness. 

- `LLMS_TXT_MISSING`: Deprecated because no major AI search platform officially reads `llms.txt` for search/citation crawling, and empirical studies show no citation correlation.
- `LLMS_TXT_MISSING_H1`, `LLMS_TXT_MISSING_SECTION`, `LLMS_TXT_NO_LINKS`, `LLMS_TXT_EMPTY_CONTENT`: Sub-codes of the above, deprecated for identical reasons.
- `GOOGLE_EXTENDED_MISSING`: Deprecated because `Google-Extended` is a training-data opt-out token, not a crawler used for Google AI Overviews or Search, having zero effect on AI-citation eligibility.
- `GPTBOT_MISSING`: Deprecated because `GPTBot` is OpenAI's training crawler, not the ChatGPT-citation crawler (which is `OAI-SearchBot`).
- `AUTHORITY_DR_LOW`: Deprecated because proprietary metrics like Moz Domain Rating (DR) are not used by AI engines as a citation signal; using it as a pass/fail threshold rests on unverified relevance.

> *Crawler and robots.txt analysis is provided for technical diagnostic purposes only and does not constitute legal advice regarding copyright opt-outs, text-and-data-mining (TDM) directives, or compliance with any jurisdiction's intellectual property laws. See [Legal](legal.md) for details.*

## Section 5: Documentation Version

- **Documentation version**: 2026.09.02.1
- **Last updated**: 2026-09-02
- **Note**: Generated directly from active codebase analysis, not inherited from legacy or superseded documentation.
