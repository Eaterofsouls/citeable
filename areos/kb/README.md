# areos/kb — Citeable Knowledge Architecture

> **Time to understand: < 1 minute**

## What This Is

The `areos/kb/` module is Citeable's knowledge layer. It replaces the old system where 5 hardcoded claims powered the entire product with a **202-record governed corpus** backed by evidence chains, source citations, and semantic search.

## Key Files

| File | What it does |
|---|---|
| `corpus/knowledge.jsonl` | 202 knowledge records (FACT, GUIDANCE, FINDING, etc.) |
| `corpus/evidence.jsonl` | 200 evidence links connecting knowledge → sources |
| `corpus/sources.jsonl` | 115 cited sources with URLs and authority tiers |
| `check_code_to_knowledge_map.json` | 50 check codes → knowledge record mappings |
| `build_kb.py` | Transforms JSONL → SQLite tables. Run on every deploy. |
| `models.py` | Pydantic models for all record types + Resolution |
| `embeddings.py` | BYOK embedding waterfall (Google/OpenAI/Mistral) |
| `router.py` | Knowledge Router: deterministic + 3-tier RAG |
| `DECISIONS.md` | 30 architectural decisions with rationale |
| `GOVERNANCE.md` | How to create/modify/deprecate knowledge records |
| `CHECK_CODES.md` | Complete registry of all 50 check codes |

## How Knowledge Flows

```
Auditor emits check_code (e.g., "CRAWLER_FULLY_BLOCKED")
    │
    ▼
Knowledge Router (router.py)
    │
    ├── KNOWN (in kb_check_code_map table)
    │   └── Deterministic: GUIDANCE record + backing FACT + evidence chain
    │
    └── UNKNOWN (not in map)
        └── RAG: embed query with client's BYOK key → cosine search
            └── ≥ 0.82 → use as primary
            └── < 0.82 → INSUFFICIENT (flag for human review)
    │
    ▼
Resolution object → LLM Synthesis Pipeline → Remediation Report
```

## How to Add New Knowledge

1. Edit `corpus/knowledge.jsonl` — add a new line with a `KT-xxx` kid
2. If it has sources, add entries to `corpus/sources.jsonl` and `corpus/evidence.jsonl`
3. If it maps to a check code, update `check_code_to_knowledge_map.json`
4. Run `python -m areos.kb.build_kb` to rebuild SQLite
5. Commit the JSONL changes to git

**Never edit SQLite directly.** The JSONL files are the source of truth.

## How to Rebuild

```bash
# Local development
python -m areos.kb.build_kb

# On deploy (added to startup command)
python -m areos.kb.build_kb && uvicorn areos.api.main:app --host 0.0.0.0 --port $PORT
```

## Record Types

| Type | Purpose | Example |
|---|---|---|
| **FACT** | Verified factual statement | "GPTBot is OpenAI's web crawler for training data" |
| **STANDARD** | Industry standard or specification | "RFC 9309 defines the Robots Exclusion Protocol" |
| **FINDING** | Empirical observation | "Pages with JSON-LD are 40% more likely to be cited" |
| **UNCERTAINTY** | Known unknown or evolving area | "Google's AI Overview selection criteria are opaque" |
| **GUIDANCE** | Actionable remediation advice | "Unblock AI crawlers in robots.txt" |

## Evidence Chain

Every knowledge record can have evidence links:

```
KT-124 (GUIDANCE: "Unblock AI Crawler")
    │
    ├── EV-101 (supports, primary) → SRC-042 (OpenAI Crawlers Docs, T1)
    ├── EV-102 (supports, secondary) → SRC-015 (RFC 9309, T1)
    └── rationale: KT-033 (FACT: "Search crawlers operate independently")
            └── EV-045 (supports) → SRC-042 (OpenAI Crawlers Docs, T1)
```
