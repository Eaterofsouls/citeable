Engineering maturity is demonstrated not by claiming everything works perfectly, but by precisely identifying what doesn't. This page documents Citeable's known limitations, architectural tradeoffs, and measurement boundaries.

## Architectural Tradeoffs

### SQLite as the Database Engine
- **Chosen**: Embedded SQLite in WAL mode with thread-local connections
- **Given up**: Horizontal scaling, multi-node deployment, concurrent write throughput
- **Why**: The audit data model is relational (claims → evidence → sources, with referential integrity). Single-node deployment eliminates distributed system complexity. WAL mode provides concurrent readers alongside a single writer, which matches the access pattern (many reads, infrequent writes).

### Zero-SDK LLM Integration
- **Chosen**: Raw HTTP requests to all 11 providers
- **Given up**: Streaming responses, SDK-managed retries, automatic API versioning
- **Why**: Eliminates SDK dependency conflicts, reduces container size, minimizes supply chain attack surface, and enables vendor-agnostic provider switching.

### Client-Side Documentation Rendering
- **Chosen**: Browser-side markdown parsing via marked.js + mermaid.js
- **Given up**: Server-side rendering, SEO for docs, static site generation
- **Why**: Zero build step, no additional dependencies, docs deploy seamlessly with the application itself.

### Synchronous Audit Execution
- **Chosen**: Audit runs execute synchronously within the HTTP request
- **Given up**: Background job processing, progress streaming, long-running audit support
- **Why**: Simpler reasoning about state, no job queue infrastructure, and all audit state is returned in the response. **Tradeoff**: Long audits (with citation sampling + Playwright) can approach HTTP timeout limits.

### Deterministic Scoring (No ML)
- **Chosen**: Pure mathematical deduction model with hardcoded weights
- **Given up**: Adaptive scoring, personalized weights, ML-based quality prediction
- **Why**: Reproducibility, auditability, and explainability. Given identical inputs, the score is identical every time. Clients can independently verify the calculation.

## Measurement Limitations

### Citation Sampling Is Probabilistic
- Results represent observed frequency only (cited in N/M sampled runs).
- AI engine outputs are non-deterministic — the same query may produce different results.
- Share-of-voice is relative to the sampled query set, not the entire query space.
- Limited to Perplexity and Gemini APIs (other engines lack citation extraction APIs).

### Authority Metrics Are Approximate
- Open PageRank is the only live API currently integrated.
- Moz and Ahrefs API integrations are scaffolded but not functional.
- For domains not in Open PageRank's index, the system falls back to deterministic heuristic profiles.
- Brand mention growth rates are currently derived from heuristic estimates, not live monitoring.

### Extractability Judgment Has an LLM Dependency
- The heuristic fast-path handles clear cases deterministically.
- Ambiguous cases require an LLM call, introducing non-determinism.
- If no LLM API key is available, the system defaults to "medium" (safe but uninformative).

## Coverage Gaps

### No Continuous Monitoring
- Audits are point-in-time snapshots.
- A site's AI readiness can change between audits as content, schema, or AI engine behavior changes.
- No webhook or polling-based change detection.

### No Multi-Tenant Isolation
- Single SQLite database for all audit runs.
- No per-user or per-organization data isolation.
- Acceptable for single-operator deployment; would require migration for SaaS deployment.

### Optional JS Rendering
- Playwright-based JS rendering diff is opt-in (requires Playwright installation + environment flag).
- Without it, the system cannot detect JS-gated content (SPAs, client-rendered frameworks).
- The system reports `skipped: true` rather than false negatives.

### Limited Competitor Analysis
- Competitor analysis covers schema presence and content structure only.
- Does not analyze competitor content quality, publication frequency, or authority metrics.
- Limited to 3 competitors per audit (to bound execution time).

## Epistemic Boundaries

### Absence of Evidence Is Not Treated as Negative Evidence
- If a diagnostic check cannot be completed (network error, timeout, blocked), the finding is marked as `info` severity (unverifiable), not `error`.
- This prevents penalizing sites for transient infrastructure issues.
- **Example**: `ROBOTS_UNVERIFIABLE` (info) vs `CRAWLER_FULLY_BLOCKED` (warning).

### Scores Are Directional, Not Absolute
- A score of 72 is better than 45, but the difference is not precisely quantifiable in terms of real-world AI citation probability.
- Scores measure AI readiness (what the site makes possible), not AI ranking (what AI engines actually do).
- AI engines do not disclose their citation ranking algorithms, so any claim of predicting citation probability would be unsupported.

### Knowledge Base Scope
- The knowledge base covers AI search engine crawling, citation, and optimization practices as of its last verified date.
- AI engine behavior is evolving rapidly; claims may become stale between verification cycles.
- The system tracks `review_due` dates and flags stale claims, but does not automatically re-verify them.

## Failure Modes (How Things Break)

| Failure | Impact | Mitigation |
|---|---|---|
| All LLM providers fail | No synthesis narrative generated | Deterministic results (scores, findings, recommendations) are fully available |
| Target site blocks all requests | Most checks produce UNVERIFIABLE findings | Access gate caps score; explicit findings explain what couldn't be checked |
| Citation sampling circuit breaker trips | Citation layer receives no data | Findings are omitted (not scored as zero) |
| SQLite busy timeout exceeded | HTTP 500 on write operations | 30-second timeout with WAL mode; unlikely under normal load |
| Malformed JSON-LD on target | Schema validation produces JSON_PARSE_FAILURE | Counted as a finding, not a system error |
| KB build with corrupt JSONL | Build fails during Pydantic validation | Atomic staging swap means production DB is never corrupted |

## What Could Be Better

- **Async audit execution** would eliminate HTTP timeout concerns for comprehensive audits.
- **Background job processing** would enable audit queuing and webhook notification.
- **A second database (PostgreSQL)** would enable multi-tenant deployment.
- **Streaming LLM responses** would improve perceived latency during synthesis.
- **Continuous monitoring** would enable trend analysis over time.
