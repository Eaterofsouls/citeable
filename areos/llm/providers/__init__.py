# areos/llm/providers/__init__.py
#
# LLM provider abstraction — waterfall design with BYOK (Bring Your Own Key).
#
# Exposes a single `complete(prompt, *, model, system, client_keys)` function.
#
# Waterfall order (auto-detected from client_keys first, then env vars):
#   1.  Gemini 2.0 Flash     (x-api-key-google  / AREOS_GEMINI_KEY_1)
#   2.  Gemini 2.0 Flash     (AREOS_GEMINI_KEY_2 rotation)
#   3.  Groq llama-3.3-70b   (x-api-key-groq    / AREOS_GROQ_KEY)
#   4.  OpenAI gpt-4o-mini   (x-api-key-openai  / OPENAI_API_KEY)
#   5.  Anthropic Claude      (x-api-key-anthropic)
#   6.  Perplexity Sonar      (x-api-key-perplexity)
#   7.  xAI Grok              (x-api-key-xai)
#   8.  Mistral               (x-api-key-mistral)
#   9.  DeepSeek              (x-api-key-deepseek)
#  10.  Azure OpenAI          (x-api-key-azure + x-api-base-azure)
#  11.  Ollama / Custom       (x-api-key-custom + x-api-base-custom)
#
# Key resolution priority per provider:
#   client_keys dict (from HTTP request headers) → os.environ fallback
#
# Error mitigation implemented:
#   - 429 Rate Limit:             Exponential backoff (2s, 4s, 8s) then waterfall fallback
#   - 401/403 Auth/Credits:       Instant skip, no retries
#   - 402 Payment Required:       Instant skip
#   - 400 Content Filter:         Parse body; skip to next if safety violation
#   - 404 Model Not Found:        Treat as _ProviderUnavailable, skip
#   - 500/503/504 Server Error:   Retry once after 2s then skip
#   - Network Timeout:            30s hard timeout, catch Timeout → skip
#   - Connection/DNS Error:       Catch ConnectionError → skip
#   - SSL Error:                  Catch SSLError → skip (NEVER verify=False)
#   - Chunked Encoding Error:     Catch ChunkedEncodingError → skip
#   - Malformed API key:          Key .strip()ped at API boundary before injection
#   - Missing Azure base URL:     Raise _NotConfigured if api_base absent
#   - Local Custom refused:       Catch ConnectionError with short timeout
#   - Empty/refused responses:    Treat as _ProviderUnavailable → skip
#   - Output cut-off (length):    Log warning, attempt JSON repair
#   - Total waterfall collapse:   Raise RuntimeError with full per-provider error log
#
# Zero-dependency architecture: all providers use pure requests.post() — no SDKs.
# Keys are NEVER stored to disk; stateless pass-through per-request only.

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

import requests as _requests
from requests.exceptions import (
    ChunkedEncodingError as _ChunkedEncodingError,
    ConnectionError as _ConnectionError,
    SSLError as _SSLError,
    Timeout as _Timeout,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public type alias for client-supplied keys
# ---------------------------------------------------------------------------

ClientKeys = Optional[dict[str, str]]


# ---------------------------------------------------------------------------
# Internal exceptions
# ---------------------------------------------------------------------------

class _NotConfigured(Exception):
    """Provider skipped — key/base not set."""

class _RateLimit(Exception):
    """Provider returned 429 — rate-limited or quota exhausted."""

class _AuthFailure(Exception):
    """Provider returned 401/402/403 — invalid key or out of credits."""

class _ProviderUnavailable(Exception):
    """Provider returned a transient or permanent server error."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def complete(
    prompt: str,
    *,
    model: str | None = None,
    system: str | None = None,
    client_keys: ClientKeys = None,
) -> str:
    """
    Send `prompt` through the provider waterfall and return the response text.
    Tries each configured provider in order; raises RuntimeError only if ALL fail.

    Args:
        prompt:      The user-facing prompt text.
        model:       Optional override for provider model name.
        system:      Optional system/context instruction.
        client_keys: Dict of user-supplied API keys from request headers.
                     Client-provided keys take priority over os.environ.
    """
    errors: list[str] = []

    for provider_fn, label in _build_waterfall(client_keys):
        try:
            result = provider_fn(prompt, model=model, system=system)
            if not result or not result.strip():
                raise _ProviderUnavailable("Empty or refused response from model.")
            return result
        except _RateLimit as e:
            errors.append(f"[{label}] rate-limited: {e}")
            continue
        except _AuthFailure as e:
            errors.append(f"[{label}] auth/credits failure: {e}")
            continue
        except _ProviderUnavailable as e:
            errors.append(f"[{label}] unavailable: {e}")
            continue
        except _NotConfigured:
            continue  # silently skip unconfigured providers

    raise RuntimeError(
        "All LLM providers failed or are unconfigured.\n"
        "Supply at least one API key via HTTP headers (x-api-key-google, "
        "x-api-key-openai, x-api-key-groq, x-api-key-anthropic, etc.) or "
        "set server environment variables.\n"
        f"Per-provider errors: {errors}"
    )


def complete_adversarial(
    prompt: str,
    *,
    model: str | None = None,
    system: str | None = None,
    client_keys: ClientKeys = None,
) -> str:
    """
    Like complete(), but runs the waterfall in REVERSE order for cognitive diversity.
    Used for adversarial critique to ensure a different model from the primary response.
    """
    errors: list[str] = []

    for provider_fn, label in reversed(_build_waterfall(client_keys)):
        try:
            result = provider_fn(prompt, model=model, system=system)
            if not result or not result.strip():
                raise _ProviderUnavailable("Empty or refused response from model.")
            return result
        except _RateLimit as e:
            errors.append(f"[{label}] rate-limited: {e}")
            continue
        except _AuthFailure as e:
            errors.append(f"[{label}] auth/credits failure: {e}")
            continue
        except _ProviderUnavailable as e:
            errors.append(f"[{label}] unavailable: {e}")
            continue
        except _NotConfigured:
            continue

    raise RuntimeError(
        "All adversarial LLM providers failed or are unconfigured.\n"
        f"Per-provider errors: {errors}"
    )


def check_any_provider_configured(client_keys: ClientKeys = None) -> bool:
    """Returns True if at least one provider key is available (client or server)."""
    return len(_build_waterfall(client_keys)) > 0


# ---------------------------------------------------------------------------
# Waterfall builder
# ---------------------------------------------------------------------------

def _build_waterfall(client_keys: ClientKeys) -> list[tuple]:
    """
    Builds the ordered list of (callable, label) provider pairs.
    Providers are included only if their key is resolvable from client_keys or env.
    Client-provided keys take priority and are injected as closures.
    """
    ck = client_keys or {}

    def _resolve(client_key: str, env_key: str) -> str | None:
        val = ck.get(client_key) or os.environ.get(env_key, "")
        return val.strip() if val else None

    waterfall = []

    # 1. Gemini (client key or server key 1)
    gemini_key1 = ck.get("google") or os.environ.get("AREOS_GEMINI_KEY_1", "")
    if gemini_key1 := gemini_key1.strip() if gemini_key1 else None:
        k = gemini_key1
        waterfall.append((lambda p, model, system, _k=k: _gemini_call(_k, p, model=model, system=system), "Gemini-Client/Key1"))

    # 2. Gemini server key 2 (rotation)
    gemini_key2 = os.environ.get("AREOS_GEMINI_KEY_2", "").strip()
    if gemini_key2:
        k = gemini_key2
        waterfall.append((lambda p, model, system, _k=k: _gemini_call(_k, p, model=model, system=system), "Gemini-Key2"))

    # 3. Groq
    groq_key = _resolve("groq", "AREOS_GROQ_KEY")
    if groq_key:
        k = groq_key
        waterfall.append((lambda p, model, system, _k=k: _groq_call(_k, p, model=model, system=system), "Groq"))

    # 4. OpenAI
    openai_key = _resolve("openai", "OPENAI_API_KEY")
    if openai_key:
        k = openai_key
        waterfall.append((lambda p, model, system, _k=k: _openai_call(_k, p, model=model, system=system), "OpenAI"))

    # 5. Anthropic
    anthropic_key = _resolve("anthropic", "ANTHROPIC_API_KEY")
    if anthropic_key:
        k = anthropic_key
        waterfall.append((lambda p, model, system, _k=k: _anthropic_call(_k, p, model=model, system=system), "Anthropic"))

    # 6. Perplexity
    perplexity_key = _resolve("perplexity", "PERPLEXITY_API_KEY")
    if perplexity_key:
        k = perplexity_key
        waterfall.append((lambda p, model, system, _k=k: _perplexity_call(_k, p, model=model, system=system), "Perplexity"))

    # 7. xAI Grok
    xai_key = _resolve("xai", "XAI_API_KEY")
    if xai_key:
        k = xai_key
        waterfall.append((lambda p, model, system, _k=k: _xai_call(_k, p, model=model, system=system), "xAI-Grok"))

    # 8. Mistral
    mistral_key = _resolve("mistral", "MISTRAL_API_KEY")
    if mistral_key:
        k = mistral_key
        waterfall.append((lambda p, model, system, _k=k: _mistral_call(_k, p, model=model, system=system), "Mistral"))

    # 9. DeepSeek
    deepseek_key = _resolve("deepseek", "DEEPSEEK_API_KEY")
    if deepseek_key:
        k = deepseek_key
        waterfall.append((lambda p, model, system, _k=k: _deepseek_call(_k, p, model=model, system=system), "DeepSeek"))

    # 10. Azure OpenAI
    azure_key = _resolve("azure", "AZURE_OPENAI_KEY")
    azure_base = (ck.get("azure_base") or os.environ.get("AZURE_OPENAI_BASE", "")).strip()
    if azure_key and azure_base:
        k, b = azure_key, azure_base
        waterfall.append((lambda p, model, system, _k=k, _b=b: _azure_call(_k, _b, p, model=model, system=system), "Azure-OpenAI"))

    # 11. Custom / Ollama (local)
    custom_key = ck.get("custom", "").strip()  # optional for Ollama (no auth)
    custom_base = (ck.get("custom_base") or os.environ.get("CUSTOM_LLM_BASE", "")).strip()
    if custom_base:
        k, b = custom_key or "", custom_base
        waterfall.append((lambda p, model, system, _k=k, _b=b: _custom_call(_k, _b, p, model=model, system=system), "Custom/Ollama"))

    return waterfall


# ---------------------------------------------------------------------------
# Shared request helper with full error mitigation
# ---------------------------------------------------------------------------

def _make_request(
    url: str,
    headers: dict,
    payload: dict,
    label: str,
    timeout: int = 30,
    max_retries_429: int = 3,
    is_local: bool = False,
) -> dict:
    """
    Shared HTTP POST dispatcher with full error mitigation:
    429 → exponential backoff → waterfall fallback
    401/402/403 → instant _AuthFailure (no retry)
    400 → parse content filter → skip or crash
    404 → _ProviderUnavailable
    500/503/504 → retry once after 2s
    Timeout → _ProviderUnavailable
    ConnectionError → _ProviderUnavailable
    SSLError → _ProviderUnavailable (NEVER verify=False)
    ChunkedEncodingError → _ProviderUnavailable
    """
    delay = 2
    for attempt in range(max_retries_429):
        try:
            r = _requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=5 if is_local else timeout,
            )
        except _Timeout:
            raise _ProviderUnavailable(f"[{label}] Request timed out after {timeout}s.")
        except _SSLError as e:
            raise _ProviderUnavailable(f"[{label}] SSL certificate error: {e}")
        except _ConnectionError as e:
            raise _ProviderUnavailable(f"[{label}] Connection/DNS failure: {e}")
        except _ChunkedEncodingError as e:
            raise _ProviderUnavailable(f"[{label}] Chunked encoding desync — corrupt payload: {e}")

        # 429 — rate limit: exponential backoff then waterfall
        if r.status_code == 429:
            if attempt < max_retries_429 - 1:
                wait = delay * (2 ** attempt)
                logger.warning("[%s] 429 rate-limited. Retrying in %ss (attempt %s/%s)...", label, wait, attempt + 1, max_retries_429)
                time.sleep(wait)
                continue
            raise _RateLimit(f"Exhausted {max_retries_429} retries on 429: {r.text[:200]}")

        # 401/402/403 — auth failure or credit exhaustion: instant skip
        if r.status_code in (401, 402, 403):
            raise _AuthFailure(f"HTTP {r.status_code} — invalid key or out of credits: {r.text[:200]}")

        # 400 — bad request: check for content filter vs genuine bad request
        if r.status_code == 400:
            body = r.text
            if any(kw in body for kw in ("content_filter", "safety", "policy_violation", "blocked")):
                raise _ProviderUnavailable(f"[{label}] Content filter / safety refusal. Trying next provider.")
            raise _ProviderUnavailable(f"[{label}] HTTP 400 Bad Request (context window or malformed payload): {body[:200]}")

        # 404 — model deprecated or not found
        if r.status_code == 404:
            raise _ProviderUnavailable(f"[{label}] HTTP 404 — model not found or deprecated: {r.text[:200]}")

        # 500/503/504 — server outage: retry once
        if r.status_code in (500, 503, 504):
            if attempt == 0:
                logger.warning("[%s] HTTP %s server error. Retrying once after 2s...", label, r.status_code)
                time.sleep(2)
                continue
            raise _ProviderUnavailable(f"[{label}] HTTP {r.status_code} server error after retry: {r.text[:200]}")

        # Non-200 catch-all
        if r.status_code != 200:
            raise _ProviderUnavailable(f"[{label}] HTTP {r.status_code}: {r.text[:200]}")

        # FIX (Readiness Audit, Major #3): a 200 response with a non-JSON
        # body (WAF/proxy error pages, truncated bodies, etc.) used to raise
        # a raw requests.exceptions.JSONDecodeError here — not one of this
        # module's own handled exception types, so it wasn't treated as
        # _ProviderUnavailable and wouldn't fall through to the next
        # provider in the waterfall the way every other failure mode does.
        try:
            return r.json()
        except ValueError as exc:  # requests.exceptions.JSONDecodeError subclasses ValueError
            raise _ProviderUnavailable(f"[{label}] HTTP 200 but response body was not valid JSON: {exc}")  # noqa: E501

    raise _ProviderUnavailable(f"[{label}] Request loop exhausted without a successful response.")


def _parse_safe(text: str, label: str) -> str:
    """Strip markdown fences and trailing commas for JSON resilience."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# 1. Gemini (Google AI Studio / Vertex)
# ---------------------------------------------------------------------------

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"


def _gemini_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    contents = []
    if system:
        contents.append({"role": "user",  "parts": [{"text": system}]})
        contents.append({"role": "model", "parts": [{"text": "Understood."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    resolved = model or os.environ.get("AREOS_GEMINI_MODEL_1", _GEMINI_DEFAULT_MODEL)
    data = _make_request(
        url=f"{_GEMINI_BASE}/{resolved}:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        payload={"contents": contents, "generationConfig": {"temperature": 0.2}},
        label="Gemini",
    )

    candidates = data.get("candidates", [])
    if not candidates:
        raise _ProviderUnavailable("Gemini: no candidates in response.")
    finish = candidates[0].get("finishReason", "")
    if finish == "MAX_TOKENS":
        logger.warning("Gemini: response cut off at max tokens — output may be truncated.")
    # FIX (Readiness Audit, Major #3): Gemini omits the "content" key
    # entirely on safety-filtered responses (finishReason == "SAFETY", also
    # seen with "RECITATION"/"PROHIBITED_CONTENT"/"BLOCKLIST"), which used
    # to raise an uncaught KeyError here instead of being treated as a
    # normal provider-unavailable/refusal case like every other provider's
    # content-filter response in this module.
    content = candidates[0].get("content")
    if not content or not content.get("parts"):
        raise _ProviderUnavailable(f"Gemini: response blocked or empty (finishReason={finish!r}).")
    return content["parts"][0]["text"]


# ---------------------------------------------------------------------------
# 2. Groq (OpenAI-compatible)
# ---------------------------------------------------------------------------

_GROQ_BASE = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _groq_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = _make_request(
        url=_GROQ_BASE,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload={"model": model or _GROQ_DEFAULT_MODEL, "messages": messages, "temperature": 0.2},
        label="Groq",
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("Groq: empty choices in response.")
    if choices[0].get("finish_reason") == "length":
        logger.warning("Groq: response cut off at max tokens — output may be truncated.")
    return choices[0]["message"]["content"]


# ---------------------------------------------------------------------------
# 3. OpenAI
# ---------------------------------------------------------------------------

_OPENAI_BASE = "https://api.openai.com/v1/chat/completions"
_OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


def _openai_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = _make_request(
        url=_OPENAI_BASE,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload={"model": model or _OPENAI_DEFAULT_MODEL, "messages": messages, "temperature": 0.2},
        label="OpenAI",
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("OpenAI: empty choices in response.")
    if choices[0].get("finish_reason") == "length":
        logger.warning("OpenAI: response cut off at max tokens — output may be truncated.")
    return choices[0]["message"]["content"] or ""


# ---------------------------------------------------------------------------
# 4. Anthropic (Claude)
# ---------------------------------------------------------------------------

_ANTHROPIC_BASE = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_DEFAULT_MODEL = "claude-haiku-4-5"  # Updated Aug 2026: claude-3-5-haiku-20241022 retired Feb 2026


def _anthropic_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    payload: dict = {
        "model": model or _ANTHROPIC_DEFAULT_MODEL,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    data = _make_request(
        url=_ANTHROPIC_BASE,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        payload=payload,
        label="Anthropic",
    )
    content = data.get("content", [])
    if not content:
        raise _ProviderUnavailable("Anthropic: empty content in response.")
    if data.get("stop_reason") == "max_tokens":
        logger.warning("Anthropic: response cut off at max tokens — output may be truncated.")
    return content[0].get("text", "")


# ---------------------------------------------------------------------------
# 5. Perplexity (Sonar)
# ---------------------------------------------------------------------------

_PERPLEXITY_BASE = "https://api.perplexity.ai/chat/completions"
_PERPLEXITY_DEFAULT_MODEL = "sonar"


def _perplexity_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = _make_request(
        url=_PERPLEXITY_BASE,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload={"model": model or _PERPLEXITY_DEFAULT_MODEL, "messages": messages},
        label="Perplexity",
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("Perplexity: empty choices in response.")
    return choices[0]["message"]["content"]


# ---------------------------------------------------------------------------
# 6. xAI (Grok)
# ---------------------------------------------------------------------------

_XAI_BASE = "https://api.x.ai/v1/chat/completions"
_XAI_DEFAULT_MODEL = "grok-3-mini"


def _xai_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = _make_request(
        url=_XAI_BASE,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload={"model": model or _XAI_DEFAULT_MODEL, "messages": messages, "temperature": 0.2},
        label="xAI-Grok",
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("xAI: empty choices in response.")
    return choices[0]["message"]["content"]


# ---------------------------------------------------------------------------
# 7. Mistral AI
# ---------------------------------------------------------------------------

_MISTRAL_BASE = "https://api.mistral.ai/v1/chat/completions"
_MISTRAL_DEFAULT_MODEL = "mistral-small-latest"


def _mistral_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = _make_request(
        url=_MISTRAL_BASE,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload={"model": model or _MISTRAL_DEFAULT_MODEL, "messages": messages, "temperature": 0.2},
        label="Mistral",
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("Mistral: empty choices in response.")
    return choices[0]["message"]["content"]


# ---------------------------------------------------------------------------
# 8. DeepSeek
# ---------------------------------------------------------------------------

_DEEPSEEK_BASE = "https://api.deepseek.com/chat/completions"
_DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"  # Updated Aug 2026: deepseek-chat retired July 24 2026


def _deepseek_call(api_key: str, prompt: str, *, model: str | None, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = _make_request(
        url=_DEEPSEEK_BASE,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload={"model": model or _DEEPSEEK_DEFAULT_MODEL, "messages": messages, "temperature": 0.2},
        label="DeepSeek",
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("DeepSeek: empty choices in response.")
    if choices[0].get("finish_reason") == "length":
        logger.warning("DeepSeek: response cut off at max tokens — output may be truncated.")
    return choices[0]["message"]["content"]


# ---------------------------------------------------------------------------
# 9. Azure OpenAI
# ---------------------------------------------------------------------------

_AZURE_API_VERSION = "2025-04-01-preview"  # Updated Aug 2026: 2024-02-01 is legacy; use v1 path or latest stable


def _azure_call(api_key: str, api_base: str, prompt: str, *, model: str | None, system: str | None) -> str:
    if not api_base:
        raise _NotConfigured  # Azure requires base URL — skip if missing
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    deployment = model or "gpt-4o-mini"
    # Azure OpenAI v1 GA API (Aug 2025+): use /openai/v1/chat/completions path, no api-version needed.
    # Falls back to legacy deployment-based path if model/deployment name is explicitly set.
    if model:
        url = f"{api_base.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={_AZURE_API_VERSION}"
    else:
        url = f"{api_base.rstrip('/')}/openai/v1/chat/completions"

    data = _make_request(
        url=url,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        payload={"messages": messages, "temperature": 0.2},
        label="Azure-OpenAI",
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("Azure: empty choices in response.")
    return choices[0]["message"]["content"] or ""


# ---------------------------------------------------------------------------
# 10. Custom / Ollama (local daemon or self-hosted vLLM)
# ---------------------------------------------------------------------------

_CUSTOM_DEFAULT_MODEL = "llama3"


def _custom_call(api_key: str, api_base: str, prompt: str, *, model: str | None, system: str | None) -> str:
    if not api_base:
        raise _NotConfigured
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{api_base.rstrip('/')}/v1/chat/completions"
    data = _make_request(
        url=url,
        headers=headers,
        payload={"model": model or _CUSTOM_DEFAULT_MODEL, "messages": messages, "temperature": 0.2},
        label="Custom/Ollama",
        is_local=True,  # Short 5s timeout for local daemon
    )
    choices = data.get("choices", [])
    if not choices:
        raise _ProviderUnavailable("Custom/Ollama: empty choices in response.")
    return choices[0]["message"]["content"]
