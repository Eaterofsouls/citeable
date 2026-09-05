# RAG × BYOK Integration — Architecture Decision

## How BYOK Works Today

The BYOK (Bring Your Own Key) system is a core Citeable design principle:

```
User's browser (BYOK Vault in localStorage)
    │  Keys stored client-side only, never on server
    │
    ▼  HTTP headers: x-api-key-google, x-api-key-openai, etc.
dependencies.py::get_client_keys()
    │  Extracts headers → dict {"google": "sk-...", "openai": "sk-..."}
    │
    ▼  Passed through every function in the call chain
audit_orchestrator.py → synthesis_engine.py → synthesis_pipeline.py
    │
    ▼  Used in the waterfall
llm/providers/__init__.py::complete(prompt, client_keys=client_keys)
    │  Tries: Gemini → Groq → OpenAI → Anthropic → ... (11 providers)
    │
    ▼  Response
LLM output
```

**Key design facts:**
- Keys are **never stored on the server** — stateless pass-through per-request
- Client-provided keys **take priority** over server env vars
- The waterfall tries every configured provider until one succeeds
- **No key = no LLM synthesis** (the app shows "Add a free key in the BYOK AI Vault")

---

## The Problem With My Previous Plan

My previous plan used `sentence-transformers/all-MiniLM-L6-v2` (local model) for embeddings. This has serious problems:

| Issue | Impact |
|---|---|
| `sentence-transformers` requires `torch` | **+750MB** to the deploy image |
| Model download on first boot | 80MB download, 30s+ cold start on Render |
| RAM usage | ~200MB for the model in memory |
| Inconsistent with BYOK | Every other AI call uses client keys. Why should embeddings be different? |
| No provider choice | Forces one model. Client might prefer OpenAI or Gemini embeddings |

**This breaks the zero-dependency, BYOK-first design that makes Citeable lightweight and deployable.**

---

## The Right Architecture: BYOK Embeddings + Pre-Computed Fallback

### Two-Layer Embedding Strategy

```
┌──────────────────────────────────────────────────────────────┐
│                EMBEDDING LAYER (areos/kb/embeddings.py)       │
│                                                               │
│  CORPUS SIDE (build-time):                                    │
│  ┌──────────────────────────────────────┐                    │
│  │ build_kb.py runs at deploy/rebuild   │                    │
│  │ → Embeds all 202 knowledge.statement │                    │
│  │ → Uses server-side key OR pre-built  │                    │
│  │ → Stores vectors in kb_embeddings    │                    │
│  │   table (kid → float[] as JSON)      │                    │
│  └──────────────────────────────────────┘                    │
│                                                               │
│  QUERY SIDE (runtime, per-request):                           │
│  ┌──────────────────────────────────────┐                    │
│  │ User's finding needs RAG search      │                    │
│  │ → Embed the query using client's     │                    │
│  │   BYOK key (same waterfall)          │                    │
│  │ → Cosine similarity against stored   │                    │
│  │   corpus vectors                     │                    │
│  │ → Confidence gate → return results   │                    │
│  └──────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

### Why This Is Correct

1. **Corpus embeddings are pre-computed at build time** — the 202 records don't change per-request. Embed them once, store the vectors in SQLite. This can use a server-side API key (set via env var) or ship pre-computed embeddings with the corpus.

2. **Query embeddings use the client's BYOK key** — when a novel finding needs semantic search, embed the query string using the same BYOK waterfall. The user's own key pays for the API call, consistent with every other LLM operation.

3. **No new dependencies** — no `torch`, no `sentence-transformers`, no ChromaDB. Just an HTTP POST to an embedding API endpoint (same pattern as `llm/providers/__init__.py`) and cosine similarity in Python (5 lines of math, or `numpy` which is already tiny).

4. **Provider flexibility** — the embedding waterfall supports the same providers as the LLM waterfall:

| Provider | Embedding Model | Dims | Cost |
|---|---|---|---|
| Google | `text-embedding-004` | 768 | Free tier: 1500 req/min |
| OpenAI | `text-embedding-3-small` | 1536 | \$0.02 / 1M tokens |
| Mistral | `mistral-embed` | 1024 | \$0.1 / 1M tokens |
| Custom/Ollama | `nomic-embed-text` | 768 | Free (local) |

### What Happens Without a Key?

If no BYOK key is configured, RAG enrichment is **gracefully disabled** — the system still works via deterministic lookup only. The remediation report uses the GUIDANCE record's own text without RAG enrichment. This is the correct degradation:

```
With BYOK key:    Deterministic + RAG enrichment + Cross-phase intelligence
Without BYOK key: Deterministic only (still better than the current 5-claim system)
```

The UI shows a subtle indicator: "🔑 Add an AI key in BYOK Vault to enable knowledge enrichment" — same pattern as the existing "Add a free key" prompt for synthesis.

---

## Implementation: `areos/kb/embeddings.py`

```python
"""
Embedding provider abstraction — mirrors llm/providers/__init__.py pattern.
Uses the same BYOK client_keys dict for provider selection.
"""

import json
import math
from typing import Optional

import requests

ClientKeys = Optional[dict[str, str]]


def embed(text: str, *, client_keys: ClientKeys = None) -> list[float]:
    """
    Embed a single text string using the BYOK waterfall.
    Returns a float vector, or raises if no provider is configured.
    """
    for embed_fn, label in _build_embed_waterfall(client_keys):
        try:
            return embed_fn(text)
        except Exception:
            continue
    raise RuntimeError("No embedding provider configured. Add a key in the BYOK Vault.")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity. No numpy needed."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _build_embed_waterfall(client_keys: ClientKeys) -> list[tuple]:
    ck = client_keys or {}
    waterfall = []

    # Google text-embedding-004 (free tier: 1500 req/min)
    google_key = ck.get("google") or os.environ.get("AREOS_GEMINI_KEY_1", "")
    if google_key := google_key.strip():
        waterfall.append((lambda t, k=google_key: _google_embed(k, t), "Google"))

    # OpenAI text-embedding-3-small
    openai_key = ck.get("openai") or os.environ.get("OPENAI_API_KEY", "")
    if openai_key := openai_key.strip():
        waterfall.append((lambda t, k=openai_key: _openai_embed(k, t), "OpenAI"))

    # Mistral mistral-embed
    mistral_key = ck.get("mistral") or os.environ.get("MISTRAL_API_KEY", "")
    if mistral_key := mistral_key.strip():
        waterfall.append((lambda t, k=mistral_key: _mistral_embed(k, t), "Mistral"))

    return waterfall


def _google_embed(api_key: str, text: str) -> list[float]:
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"text-embedding-004:embedContent?key={api_key}",
        json={"content": {"parts": [{"text": text}]}},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["embedding"]["values"]


def _openai_embed(api_key: str, text: str) -> list[float]:
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "text-embedding-3-small", "input": text},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]
```

### Corpus-Side: Pre-Computed Embeddings

```python
# In build_kb.py — runs at deploy time or manually
def embed_corpus(db_path: Path, api_key: str):
    """Pre-compute embeddings for all knowledge records."""
    conn = get_connection(db_path)
    records = conn.execute(
        "SELECT kid, statement FROM knowledge WHERE status != 'archived'"
    ).fetchall()

    for kid, statement in records:
        vector = embed(statement, client_keys={"google": api_key})
        conn.execute(
            "INSERT OR REPLACE INTO kb_embeddings (kid, vector_json, model, embedded_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (kid, json.dumps(vector), "text-embedding-004")
        )
    conn.commit()
```

### Query-Side: RAG Search (uses client's BYOK key)

```python
# In router.py — runs per audit request
def semantic_search(query: str, client_keys: dict, db_path: Path,
                    threshold: float = 0.82, top_k: int = 5) -> list[dict]:
    """
    Embed query with client's BYOK key, compare against pre-computed corpus vectors.
    """
    query_vector = embed(query, client_keys=client_keys)

    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT e.kid, e.vector_json, k.statement, k.type, k.status, k.confidence "
        "FROM kb_embeddings e JOIN knowledge k ON e.kid = k.kid "
        "WHERE k.status NOT IN ('archived', 'deprecated')"
    ).fetchall()

    candidates = []
    for row in rows:
        corpus_vector = json.loads(row["vector_json"])
        sim = cosine_similarity(query_vector, corpus_vector)
        if sim >= 0.70:
            candidates.append({
                "kid": row["kid"], "similarity": sim,
                "statement": row["statement"], "type": row["type"],
                "confidence": row["confidence"],
                "tier": "high" if sim >= threshold else "loosely_relevant"
            })

    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates[:top_k]
```

---

## What This Changes in the Implementation Plan

| Phase | Previous Plan | Updated |
|---|---|---|
| **Dependencies** | `chromadb` + `sentence-transformers` (+800MB) | **Nothing new.** Uses `requests` (already present) + pure Python cosine. |
| **Phase 1** | Create ChromaDB collection | Create `kb_embeddings` SQLite table + pre-compute vectors at build time |
| **Phase 3 (RAG)** | `SemanticIndex` class wrapping ChromaDB | `embeddings.py` — BYOK waterfall for embeddings, cosine in SQLite |
| **Embed model** | `all-MiniLM-L6-v2` (local, fixed) | Client's choice via BYOK: Gemini, OpenAI, Mistral, or local |
| **Deploy size** | +800MB (torch + model) | **+0 bytes** (no new deps) |
| **Runtime RAM** | +200MB (model in memory) | **+0 bytes** |
| **Cold start** | +30s (model download) | **+0s** |

---

## Embedding Dimension Mismatch Handling

Different providers produce different vector dimensions. The pre-computed corpus embeddings use one model (e.g., Gemini 768-dim), but the query might use a different model (e.g., OpenAI 1536-dim).

**Solution:** The `kb_embeddings` table stores the `model` column. At query time:

1. If the query provider matches the corpus provider → direct cosine similarity
2. If they mismatch → re-embed the query using the **same** provider that built the corpus (using server-side key as fallback)
3. If neither works → skip RAG enrichment gracefully

This is a rare edge case (most users will have one key), and the graceful degradation keeps it invisible.

---

## Summary

> **RAG does NOT need its own separate keys.** It uses the exact same BYOK keys the user already provided for LLM synthesis. The embedding API call is just another provider in the waterfall — same pattern as `complete()`, same `client_keys` dict, same zero-server-storage contract.
>
> The corpus vectors are pre-computed once at build/deploy time. Only the per-request query embedding costs a BYOK API call (one call per audit, ~0.001¢ with Google's free tier).
