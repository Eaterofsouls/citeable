# areos/services/research_service.py
#
# Core logic for `areos research --stage N`.
#
# CONTRACT (non-negotiable):
#   - This service NEVER writes to the live DB.
#   - It returns CandidateBundle objects (plain dicts/dataclasses).
#   - Callers decide what to do with candidates (Task 2c diff, Task 2d approval).
#   - Every candidate carries a source_url and source_tier so PD-5 is satisfied.
#
# Architecture:
#   1. Load sources.yaml → get tier-1 and tier-2 sources for the requested stage.
#   2. Fetch content: Jina AI Reader if AREOS_JINA_KEY set (preferred — clean markdown,
#      bypasses anti-bot), else raw requests + BeautifulSoup fallback.
#   3. LLM-extract candidate claims (waterfall: Gemini → Groq → OpenAI).
#   4. Shape each candidate exactly like the ratified schema (artifacts.py).
#   5. Return the full bundle as a list of dicts — no DB touch.
#
# Required env vars (at least one LLM key):
#   AREOS_GROQ_KEY       — Groq (llama-3.3-70b) — confirmed live
#   AREOS_GEMINI_KEY_1   — Gemini Account 1 (primary, faster)
#   AREOS_GEMINI_KEY_2   — Gemini Account 2 (rotation)
#   OPENAI_API_KEY       — last resort
#   AREOS_JINA_KEY       — Jina AI Reader for clean web fetching (recommended)

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup

from areos.db.connection import get_db_path
from areos.llm.providers import complete as llm_complete

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCES_YAML_PATH = Path(__file__).resolve().parents[2] / "sources.yaml"
# FIX (data-quality pass): this constant is not actually consumed anywhere
# in this module (this service never touches the DB per the contract
# above) — it was only read by a test for a diagnostic print. Left in
# place for backwards compatibility, but now delegates to the canonical
# areos.db.connection.get_db_path() instead of reimplementing repo-root
# path logic, so it can't silently drift from the real resolver.
DEFAULT_DB_PATH   = Path(get_db_path())
FETCH_TIMEOUT      = 20          # seconds (Jina can be slightly slower)
JINA_FETCH_TIMEOUT = 25          # Jina adds an extra hop
MAX_CHARS_PER_DOC  = 8_000      # chars sent to LLM per source (cost control)
TODAY             = date.today().isoformat()

# Valid values from artifacts.py — checked before returning any candidate.
VALID_CLAIM_SCOPES  = {"retrieval-pipeline", "audit-workflow", "general-knowledge"}
VALID_STATUSES      = {"active", "deprecated", "contested", "superseded"}
VALID_TIER_VOCABS   = {"study_a", "study_b", "system_native"}
VALID_TRUST_TIERS   = {"T1", "T2", "T3", "T4", "T5", "T6", "T7"}
VALID_SOURCE_TYPES  = {
    "official-platform-doc", "primary-research", "legal-primary",
    "named-practitioner", "industry-media", "vendor-research", "community",
}

# Map sources.yaml tier labels → DB trust_tier values
TIER_MAP = {
    "tier-1": "T1",  # official platform docs
    "tier-2": "T4",  # ratified named practitioners (CLM-021 compliant)
}

# Map sources.yaml tier labels → DB source_type values
SOURCE_TYPE_MAP = {
    "tier-1": "official-platform-doc",
    "tier-2": "named-practitioner",
}

# Map sources.yaml tier labels → source_tier_vocab / source_tier_value (ADR D5)
# We use "system_native" vocab because these sources are native to AREOS's
# own tiering system (not imported from study_a or study_b).
TIER_VOCAB = "system_native"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_research(stage_id: str, *, sources_yaml_path: Path | None = None, client_keys: dict | None = None) -> dict[str, Any]:
    """
    Execute the research command for a given audit phase stage.

    Args:
        stage_id:           The audit_phase_id to research (e.g. "AP-03").
        sources_yaml_path:  Override path to sources.yaml (for tests).

    Returns:
        A CandidateBundle dict:
        {
            "stage_id":    str,
            "stage_name":  str,
            "run_id":      str,       # UUID for this research run
            "run_date":    str,       # ISO date
            "candidates":  list[CandidateClaim],
            "sources_hit": list[SourceRecord],
            "errors":      list[str], # fetch/parse errors, non-fatal
        }

    Raises:
        ValueError  if stage_id is not found in sources.yaml.
        EnvironmentError  if the LLM API key is not set (propagated from provider).
    """
    yaml_path = sources_yaml_path or SOURCES_YAML_PATH
    sources_data = _load_sources_yaml(yaml_path)

    if stage_id not in sources_data:
        valid = [k for k in sources_data if k.startswith("AP-")]
        raise ValueError(
            f"Stage '{stage_id}' not found in sources.yaml. "
            f"Valid stages: {sorted(valid)}"
        )

    stage_config = sources_data[stage_id]
    run_id = str(uuid.uuid4())

    candidates: list[dict] = []
    sources_hit: list[dict] = []
    errors: list[str] = []

    # Process tier-1 then tier-2 sources
    for tier_label in ("tier-1", "tier-2"):
        for source_entry in stage_config.get(tier_label, []):
            url  = source_entry.get("url", "")
            name = source_entry.get("name", "unknown")
            covers = source_entry.get("covers", "")

            if not url:
                errors.append(f"[{tier_label}] {name}: no URL — skipped")
                continue

            # --- Fetch ---
            text, fetch_error = _fetch_text(url, name)
            if fetch_error:
                errors.append(fetch_error)
                continue

            # --- LLM extract ---
            raw_candidates, extract_error = _extract_candidates(
                text=text,
                source_url=url,
                source_name=name,
                source_tier_label=tier_label,
                stage_id=stage_id,
                covers_hint=covers,
                client_keys=client_keys,
            )
            if extract_error:
                errors.append(extract_error)

            candidates.extend(raw_candidates)
            sources_hit.append({
                "source_id":    source_entry.get("id", f"auto-{uuid.uuid4().hex[:8]}"),
                "name":         name,
                "url":          url,
                "tier_label":   tier_label,
                "trust_tier":   TIER_MAP[tier_label],
                "source_type":  SOURCE_TYPE_MAP[tier_label],
                "candidates_extracted": len(raw_candidates),
            })

    return {
        "stage_id":    stage_id,
        "stage_name":  stage_config.get("name", stage_id),
        "run_id":      run_id,
        "run_date":    TODAY,
        "candidates":  candidates,
        "sources_hit": sources_hit,
        "errors":      errors,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_sources_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fetch_text(url: str, name: str) -> tuple[str, str | None]:
    """
    Fetch a URL and return (clean_text, error_string|None).
    Non-fatal: returns ("", error_str) on any HTTP/network failure.

    Strategy:
      1. If AREOS_JINA_KEY is set → use Jina AI Reader (r.jina.ai/<url>).
         Returns clean markdown directly; bypasses anti-bot systems.
      2. Otherwise → raw requests + BeautifulSoup fallback.
    """
    jina_key = os.environ.get("AREOS_JINA_KEY", "")
    if jina_key:
        return _fetch_via_jina(url, name, jina_key)
    return _fetch_via_requests(url, name)


def _fetch_via_jina(url: str, name: str, api_key: str) -> tuple[str, str | None]:
    """Fetch via Jina AI Reader — returns clean markdown, handles JS-rendered pages."""
    try:
        from areos.util.ssrf import safe_get
        r = safe_get(
            f"https://r.jina.ai/{url}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "text/plain",
                "X-Return-Format": "markdown",
            },
            timeout=JINA_FETCH_TIMEOUT,
        )
        if r.status_code == 200:
            return r.text[:MAX_CHARS_PER_DOC], None
        # Jina 402 = quota exceeded — fall back to raw requests
        if r.status_code == 402:
            return _fetch_via_requests(url, name)
        return "", f"[JINA ERROR] {name} ({url}): HTTP {r.status_code}"
    except Exception as e:
        # Fall back to raw requests on any network error
        return _fetch_via_requests(url, name)


def _fetch_via_requests(url: str, name: str) -> tuple[str, str | None]:
    """Raw requests + BeautifulSoup fallback fetcher."""
    headers = {
        "User-Agent": (
            "AREOS-Research-Agent/1.0 "
            "(automated SEO audit research tool; contact: areos-agent@localhost)"
        )
    }
    try:
        from areos.util.ssrf import safe_get
        resp = safe_get(url, headers=headers, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
        else:
            text = resp.text
        return text[:MAX_CHARS_PER_DOC], None
    except Exception as e:
        return "", f"[FETCH ERROR] {name} ({url}): {e}"


_EXTRACTION_SYSTEM = """\
You are a structured-data extraction assistant for AREOS, an AI citation audit system.
Your job is to read text fetched from a web page and extract factual claims that are
relevant to how AI systems (ChatGPT, Claude, Perplexity, Gemini, etc.) discover,
crawl, and cite web content.

STRICT RULES:
1. Extract only claims that are EXPLICITLY stated in the provided text.
   Do NOT infer, generalise, or add context the text doesn't provide.
2. Each claim must be a single, self-contained factual assertion.
3. If you cannot find any relevant claims, return an empty list — never fabricate.
4. Output ONLY valid JSON — no markdown fences, no preamble, no explanation.
"""

_EXTRACTION_PROMPT_TEMPLATE = """\
Source URL: {source_url}
Source name: {source_name}
Source tier: {source_tier_label}
Audit stage: {stage_id} — this source covers: {covers_hint}

Text fetched from the source (may be truncated):
---
{text}
---

Extract all factual claims relevant to AI crawling, citation, schema markup,
content discovery, or retrieval by AI systems (ChatGPT, Claude, Perplexity,
Google AI Mode, Bing Copilot, etc.).

Return a JSON array. Each element must have exactly these fields:
{{
  "statement":         "<single factual assertion, verbatim or close paraphrase>",
  "claim_scope":       "<one of: retrieval-pipeline | audit-workflow | general-knowledge>",
  "claim_type":        "<one of: empirical | policy | practitioner-observation | legal>",
  "confidence":        "<one of: high | medium | low>",
  "status":            "active",
  "source_tier_vocab": "system_native",
  "source_tier_value": "<tier-1 | tier-2>",
  "source_url":        "{source_url}",
  "source_date":       "{today}"
}}

If no relevant claims exist, return: []
"""


def _extract_candidates(
    *,
    text: str,
    source_url: str,
    source_name: str,
    source_tier_label: str,
    stage_id: str,
    covers_hint: str,
    client_keys: dict | None = None,
) -> tuple[list[dict], str | None]:
    """
    Call the LLM to extract candidate claims from fetched text.
    Returns (candidates_list, error_string|None).
    """
    prompt = _EXTRACTION_PROMPT_TEMPLATE.format(
        source_url=source_url,
        source_name=source_name,
        source_tier_label=source_tier_label,
        stage_id=stage_id,
        covers_hint=covers_hint,
        text=text,
        today=TODAY,
    )

    try:
        raw = llm_complete(prompt, system=_EXTRACTION_SYSTEM, client_keys=client_keys)
    except Exception as e:
        return [], f"[LLM ERROR] {source_name}: {e}"

    # Parse JSON — the LLM is instructed to return only JSON but may slip
    try:
        # Strip any accidental markdown fences
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        return [], f"[PARSE ERROR] {source_name}: could not parse LLM JSON — {e}\nRaw: {raw[:200]}"

    if not isinstance(parsed, list):
        return [], f"[SHAPE ERROR] {source_name}: LLM returned non-list: {type(parsed)}"

    # Validate and shape each candidate
    valid_candidates = []
    for i, item in enumerate(parsed):
        shaped, error = _shape_candidate(item, source_url=source_url, stage_id=stage_id, index=i)
        if error:
            # Log the validation failure but keep processing the rest
            pass
        if shaped:
            valid_candidates.append(shaped)

    return valid_candidates, None


def _shape_candidate(
    item: dict,
    *,
    source_url: str,
    stage_id: str,
    index: int,
) -> tuple[dict | None, str | None]:
    """
    Validate and shape one LLM-extracted item into the ratified schema shape.
    Returns (shaped_dict, error_string|None). Returns (None, error) if invalid.
    """
    if not isinstance(item, dict):
        return None, f"item[{index}]: not a dict"

    statement = str(item.get("statement", "")).strip()
    if not statement:
        return None, f"item[{index}]: empty statement"

    claim_scope = item.get("claim_scope", "general-knowledge")
    if claim_scope not in VALID_CLAIM_SCOPES:
        claim_scope = "general-knowledge"

    claim_type = str(item.get("claim_type", "practitioner-observation")).strip()
    confidence = str(item.get("confidence", "low")).strip()
    status = item.get("status", "active")
    if status not in VALID_STATUSES:
        status = "active"

    tier_vocab = item.get("source_tier_vocab", TIER_VOCAB)
    if tier_vocab not in VALID_TIER_VOCABS:
        tier_vocab = TIER_VOCAB

    tier_value = str(item.get("source_tier_value", "tier-1")).strip()
    source_date = str(item.get("source_date", TODAY)).strip()

    # Generate a deterministic-ish candidate ID (not a real claim_id — prefixed CAND-)
    cand_id = f"CAND-{uuid.uuid4().hex[:8].upper()}"

    shaped: dict[str, Any] = {
        # --- Candidate marker (stripped before DB insert in Task 2d) ---
        "_candidate": True,
        "_stage_id":  stage_id,

        # --- Mirrors claims table columns (artifacts.py) ---
        "claim_id":          cand_id,
        "stage_id":          stage_id,
        "claim_scope":       claim_scope,
        "claim_type":        claim_type,
        "statement":         statement,
        "status":            status,
        "confidence":        confidence,
        "source_url":        source_url,
        "source_tier_vocab": tier_vocab,
        "source_tier_value": tier_value,
        "source_date":       source_date,
        "last_verified":     TODAY,
        "superseded_by":     None,
    }
    return shaped, None
