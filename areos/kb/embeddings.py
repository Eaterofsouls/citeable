# areos/kb/embeddings.py
#
# BYOK-native embedding layer — mirrors llm/providers/__init__.py pattern.
# Uses the same client_keys dict for provider selection.
#
# D-008: No ChromaDB, no sentence-transformers, no torch.
# D-013: Same BYOK keys for embeddings and text generation.
# D-014: Graceful degradation — if no key, RAG is silently disabled.
# D-015: Dimension mismatch handled via model column in kb_embeddings.

from __future__ import annotations

import json
import logging
import math
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ClientKeys = Optional[dict[str, str]]


class EmbeddingUnavailable(Exception):
    """No embedding provider is configured or reachable."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed(text: str, *, client_keys: ClientKeys = None) -> list[float]:
    """
    Embed a single text string using the BYOK embedding waterfall.

    Returns a float vector. Raises EmbeddingUnavailable if no provider works.

    The waterfall mirrors llm/providers — client keys first, env vars fallback.
    """
    errors: list[str] = []

    for embed_fn, label, model_name in _build_embed_waterfall(client_keys):
        try:
            vector = embed_fn(text)
            if vector and len(vector) > 0:
                return vector
        except Exception as e:
            errors.append(f"[{label}] {e}")
            continue

    raise EmbeddingUnavailable(
        "No embedding provider configured or reachable. "
        "Add a key in the BYOK Vault to enable RAG enrichment.\n"
        f"Per-provider errors: {errors}"
    )


def get_active_model(client_keys: ClientKeys = None) -> str | None:
    """Return the model name of the first available embedding provider, or None."""
    waterfall = _build_embed_waterfall(client_keys)
    if waterfall:
        return waterfall[0][2]  # model_name
    return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Pure-Python cosine similarity. No numpy needed.

    Returns 0.0 if either vector has zero magnitude or contains NaN.
    Vectors must have the same dimensionality.
    """
    if len(a) != len(b):
        return 0.0
    for val in a:
        if math.isnan(val):
            return 0.0
    for val in b:
        if math.isnan(val):
            return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0 or math.isnan(norm_a) or math.isnan(norm_b):
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Waterfall builder
# ---------------------------------------------------------------------------

def _build_embed_waterfall(
    client_keys: ClientKeys,
) -> list[tuple]:
    """
    Build ordered list of (callable, label, model_name) embedding providers.

    Same key resolution as llm/providers: client_keys → env var fallback.
    """
    ck = client_keys or {}
    waterfall: list[tuple] = []

    # 1. Google text-embedding-004 (free tier: 1500 req/min)
    google_key = (ck.get("google") or os.environ.get("AREOS_GEMINI_KEY_1", "")).strip()
    if google_key:
        k = google_key
        waterfall.append((
            lambda t, _k=k: _google_embed(_k, t),
            "Google",
            "text-embedding-004",
        ))

    # 2. OpenAI text-embedding-3-small
    openai_key = (ck.get("openai") or os.environ.get("OPENAI_API_KEY", "")).strip()
    if openai_key:
        k = openai_key
        waterfall.append((
            lambda t, _k=k: _openai_embed(_k, t),
            "OpenAI",
            "text-embedding-3-small",
        ))

    # 3. Mistral mistral-embed
    mistral_key = (ck.get("mistral") or os.environ.get("MISTRAL_API_KEY", "")).strip()
    if mistral_key:
        k = mistral_key
        waterfall.append((
            lambda t, _k=k: _mistral_embed(_k, t),
            "Mistral",
            "mistral-embed",
        ))

    return waterfall


import time

# ---------------------------------------------------------------------------
# Provider implementations with retry logic (QA-H10)
# ---------------------------------------------------------------------------

def _retry_post(url: str, max_retries: int = 2, **kwargs) -> requests.Response:
    """Helper to execute requests.post with exponential backoff on transient errors."""
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, timeout=15, **kwargs)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(1.0 * (2 ** attempt))
                continue
            r.raise_for_status()
            return r
        except (requests.RequestException, requests.Timeout) as e:
            if attempt < max_retries:
                time.sleep(1.0 * (2 ** attempt))
                continue
            raise


def _google_embed(api_key: str, text: str) -> list[float]:
    """Google text-embedding-004 via Generative Language API."""
    r = _retry_post(
        "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent",
        headers={"x-goog-api-key": api_key},
        json={"content": {"parts": [{"text": text}]}},
    )
    return r.json()["embedding"]["values"]


def _openai_embed(api_key: str, text: str) -> list[float]:
    """OpenAI text-embedding-3-small."""
    r = _retry_post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "text-embedding-3-small", "input": text},
    )
    return r.json()["data"][0]["embedding"]


def _mistral_embed(api_key: str, text: str) -> list[float]:
    """Mistral mistral-embed."""
    r = _retry_post(
        "https://api.mistral.ai/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "mistral-embed", "input": [text]},
    )
    return r.json()["data"][0]["embedding"]
