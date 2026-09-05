# areos/llm/synthesis_pipeline.py
#
# Phase 2: Three-Step LLM Synthesis Pipeline
#
# CONTRACT:
#   Input  : enriched_recs (list[dict]) — output of audit_orchestrator enrichment loop,
#             already claim-cited, scope-tagged, evidence-labelled.
#   Step 1 : Synthesizer — complete()             — primary waterfall — draft narrative
#   Step 2 : Red Teamer  — complete_adversarial() — REVERSE waterfall (different model)
#                        — returns JSON flags
#   Step 3 : Grounder    — complete()             — primary waterfall — final grounded text
#   Output : dict with narrative, draft, flags, metadata
#
# GUARANTEES:
#   - The LLM never reads from or writes to the claims DB.
#   - All claim_ids the LLM sees come from the deterministic enrichment layer.
#   - System prompts are loaded from synthesis_prompts table (runtime-auditable).
#     If the table is missing, hardcoded defaults are used transparently.
#   - Every step has an independent try/except. A single-step failure degrades
#     gracefully rather than aborting the entire audit.
#   - Returns {llm_synthesis_used: False} when all providers are exhausted —
#     the caller always gets a valid dict, never an exception.

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from areos.llm.providers import (
    check_any_provider_configured,
    complete,
    complete_adversarial,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hardcoded defaults (used when synthesis_prompts table is absent/empty)
# ---------------------------------------------------------------------------

_DEFAULT_SYNTHESIZER_PROMPT: str = (
    "You are a search engineering auditor producing a remediation narrative. "
    "Follow these rules STRICTLY:\n"
    "1. Reference ONLY the claim_ids provided in the input JSON. Do not introduce "
    "any outside claims, statistics, or citations.\n"
    "2. Group findings into root causes using exactly three layers: "
    "Access Layer, Content Layer, Authority Layer.\n"
    "3. Each recommendation MUST reference its governing claim_id in square brackets "
    "e.g. [C050].\n"
    "4. Do NOT invent percentages, timelines, or metrics not present in the input data.\n"
    "5. Each recommendation must be specific and actionable — name the exact file, "
    "tag, or API endpoint to change.\n"
    "6. If human_review_notes are provided for a finding, you MUST explicitly integrate "
    "those observations into the narrative as a qualitative insight from human auditors.\n"
    "7. Use the provided evidence_chain, source_citations, and backing_facts to enrich your "
    "recommendations with direct quotes or references to authoritative sources.\n"
    "8. Use plain prose, no markdown headers. Be concise and direct.\n"
    "9. If a human_diagnosis_text is provided, use it as the opening framing of your "
    "narrative. Do not contradict or replace it — expand on it with supporting evidence "
    "from the findings.\n"
    "10. The structured remediation actions have already been determined. Your job is to "
    "explain WHY each action matters, not to invent new actions.\n"
    "11. If a finding is based on a claim where `is_stale=True`, you MUST explicitly caveat "
    "that the guidance may be outdated.\n"
    "12. If a finding is based on a claim where `is_contested=True`, you MUST explicitly "
    "warn the user that industry consensus on this action is actively debated.\n"
)

_DEFAULT_RED_TEAMER_PROMPT: str = (
    "You are an adversarial citation auditor reviewing a remediation narrative. "
    "For each recommendation, check for these specific violations:\n"
    "- HALLUCINATED_CLAIM: a claim_id is cited that does not appear in the provided "
    "findings data\n"
    "- UNSUPPORTED_LEAP: the recommendation does not logically follow from the cited "
    "claim statement\n"
    "- FABRICATED_STAT: a percentage, timeline, or metric appears that was not in the "
    "input data\n"
    "- VAGUE: the recommendation is generic advice with no domain-specific or "
    "file-specific action\n\n"
    "Return ONLY a valid JSON array of flag objects. Each object must have keys: "
    "text_excerpt (short quote from the narrative), flag (one of the four types above), "
    "reason (one sentence explanation).\n"
    "If no violations found, return exactly: []\n"
    "Do not return any text outside the JSON array."
)

_DEFAULT_GROUNDER_PROMPT: str = (
    "You are a remediation plan editor. You have a draft narrative and a list of "
    "adversarial flags.\n"
    "Rules:\n"
    "1. Remove or rewrite any content tagged HALLUCINATED_CLAIM or FABRICATED_STAT "
    "— do not preserve fabricated data.\n"
    "2. For UNSUPPORTED_LEAP flags: rewrite the recommendation to stay strictly within "
    "what the cited claim supports.\n"
    "3. For VAGUE flags: add domain-specific context from the provided findings data "
    "(domain name, specific URLs, specific check codes).\n"
    "4. Do NOT add any new claim_ids, statistics, or citations not in the original input.\n"
    "5. Prefix each recommendation with [Knowledge Base Principle] if its claim_scope "
    "is 'general-knowledge', or [Site-Specific Evidence] otherwise.\n"
    "6. Output the final corrected narrative only. No meta-commentary, no JSON, plain prose."
)


# ---------------------------------------------------------------------------
# Prompt loader — DB-first, hardcoded-default fallback
# ---------------------------------------------------------------------------

def _load_prompts(db_path: Path | None = None) -> dict[str, str]:
    """Return {step: system_prompt} from synthesis_prompts table. Falls back to defaults."""
    defaults: dict[str, str] = {
        "synthesizer": _DEFAULT_SYNTHESIZER_PROMPT,
        "red_teamer":  _DEFAULT_RED_TEAMER_PROMPT,
        "grounder":    _DEFAULT_GROUNDER_PROMPT,
    }
    if db_path is None:
        return defaults
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT step, system_prompt FROM synthesis_prompts"
        ).fetchall()
        conn.close()
        loaded = {r[0]: r[1] for r in rows if r[1] and r[1].strip()}
        return {**defaults, **loaded}   # DB values win over defaults
    except Exception as exc:
        logger.warning(
            "synthesis_pipeline: could not load prompts from DB (%s) — using defaults", exc
        )
        return defaults


# ---------------------------------------------------------------------------
# Input serialiser for Step 1
# ---------------------------------------------------------------------------

def _build_synthesizer_input(enriched_recs: list[dict], target_domain: str) -> str:
    # Build findings including V2 evidence chains for grounded citations
    findings = []
    for r in enriched_recs:
        item = {
            "check_code":       r.get("check_code"),
            "severity":         r.get("severity"),
            "title":            r.get("title"),
            "description":      r.get("description"),
            "claim_id":         r.get("claim_id") or r.get("governing_claim_id"),
            "claim_statement":  r.get("claim_statement") or r.get("governing_claim_statement"),
            "claim_scope":      r.get("claim_scope", "general-knowledge"),
            "evidence_label":   r.get("evidence_label"),
            "human_review_notes": r.get("human_review_notes"),
        }
        # Add V2 Evidence fields if present
        if "resolution_path" in r:
            item["resolution_path"] = r["resolution_path"]
        if "evidence_chain" in r:
            item["evidence_chain"] = r["evidence_chain"]
        if "source_citations" in r:
            item["source_citations"] = r["source_citations"]
        if "backing_facts" in r:
            item["backing_facts"] = r["backing_facts"]
        if r.get("is_contested"):
            item["is_contested"] = True
            item["contested_reason"] = r.get("contested_reason")
        if r.get("is_stale"):
            item["is_stale"] = True
            item["stale_since"] = r.get("stale_since")
            
        findings.append(item)

    findings_json = json.dumps(findings, indent=2, ensure_ascii=False)
    safe_target_domain = target_domain.replace("</untrusted_crawled_data>", "")
    safe_findings = findings_json.replace("</untrusted_crawled_data>", "")
    return (
        f"Domain under audit: <untrusted_crawled_data>{safe_target_domain}</untrusted_crawled_data>\n\n"
        f"Wired findings (deterministic, claim-cited):\n<untrusted_crawled_data>{safe_findings}</untrusted_crawled_data>\n\n"
        "Write a remediation narrative for this domain based solely on the findings above."
    )


# ---------------------------------------------------------------------------
# Red Teamer output parser
# ---------------------------------------------------------------------------

def _parse_flags(raw: str) -> list[dict]:
    """Parse Red Teamer JSON output. Returns [] on any failure — never raises."""
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            if "flags" in parsed and isinstance(parsed["flags"], list):
                return parsed["flags"]
            if "issues" in parsed and isinstance(parsed["issues"], list):
                return parsed["issues"]
            if "verdicts" in parsed and isinstance(parsed["verdicts"], list):
                return parsed["verdicts"]
            if "flag" in parsed:
                return [parsed]
            return []
        if not isinstance(parsed, list):
            logger.warning("synthesis_pipeline: Red Teamer returned %s, expected list", type(parsed))
            return []
        return parsed
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("synthesis_pipeline: Red Teamer output not valid JSON (%s) — no flags", exc)
        return []


def _count_serious_flags(flags: list[dict]) -> int:
    """Count flags that require Grounder rewrite (excludes VAGUE which is softer)."""
    serious = {"HALLUCINATED_CLAIM", "UNSUPPORTED_LEAP", "FABRICATED_STAT"}
    return sum(1 for f in flags if isinstance(f, dict) and f.get("flag") in serious)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_llm_synthesis(
    enriched_recs: list[dict],
    target_domain: str,
    client_keys: dict | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """
    Run the three-step LLM synthesis pipeline.

    Returns:
        {
            "llm_synthesis_used": bool,
            "narrative":          str,          # Grounder's final grounded output
            "draft":              str,          # Synthesizer's raw output (auditable)
            "flags":              list[dict],   # Red Teamer flags (may be empty)
            "flags_resolved":     int,          # serious flags that required Grounder fix
            "provider_log":       list[str],    # steps that ran (transparency)
            "reason":             str,          # set only when llm_synthesis_used=False
        }
    """
    if not enriched_recs:
        return {"llm_synthesis_used": False, "reason": "No recommendations to synthesize"}

    prompts = _load_prompts(db_path)
    provider_log: list[str] = []

    # ── Step 1: Synthesizer (primary waterfall) ─────────────────────────────
    try:
        draft = complete(
            prompt=_build_synthesizer_input(enriched_recs, target_domain),
            system=prompts["synthesizer"],
            client_keys=client_keys,
        )
        provider_log.append("synthesizer:forward_waterfall")
        logger.info("[LLM Synthesis] Step 1 complete — %d chars", len(draft))
    except RuntimeError as exc:
        logger.warning("[LLM Synthesis] Step 1 exhausted all providers: %s", exc)
        return {"llm_synthesis_used": False, "reason": "No LLM provider available for synthesis"}

    # ── Step 2: Red Teamer (REVERSE waterfall — different model) ────────────
    try:
        red_input = (
            f"Original claim_ids in findings: "
            f"{json.dumps([r.get('governing_claim_id') for r in enriched_recs])}\n\n"
            f"Draft narrative to audit:\n{draft}"
        )
        red_raw = complete_adversarial(
            prompt=red_input,
            system=prompts["red_teamer"],
            client_keys=client_keys,
        )
        flags = _parse_flags(red_raw)
        provider_log.append("red_teamer:reverse_waterfall")
        logger.info("[LLM Synthesis] Step 2 complete — %d flags", len(flags))
    except RuntimeError as exc:
        logger.warning("[LLM Synthesis] Step 2 failed (%s) — proceeding with no flags", exc)
        flags = []

    serious_count = _count_serious_flags(flags)

    # ── Step 3: Grounder (primary waterfall again) ──────────────────────────
    # Always runs — even when flags=[] — to apply evidence tier prefixes
    try:
        grounder_input = (
            f"Domain: {target_domain}\n\n"
            f"Findings context (claim_ids and scopes):\n"
            f"{json.dumps([{'claim_id': r.get('governing_claim_id'), 'claim_scope': r.get('claim_scope', 'general-knowledge'), 'evidence_label': r.get('evidence_label'), 'is_stale': r.get('is_stale'), 'is_contested': r.get('is_contested')} for r in enriched_recs], indent=2, ensure_ascii=False)}\n\n"  # noqa: E501
            f"Draft narrative:\n{draft}\n\n"
            f"Adversarial flags to resolve:\n{json.dumps(flags, indent=2, ensure_ascii=False)}"
        )
        narrative = complete(
            prompt=grounder_input,
            system=prompts["grounder"],
            client_keys=client_keys,
        )
        provider_log.append("grounder:forward_waterfall")
        logger.info("[LLM Synthesis] Step 3 complete — %d chars", len(narrative))
    except RuntimeError as exc:
        logger.warning("[LLM Synthesis] Step 3 failed (%s) — using draft as narrative", exc)
        narrative = draft   # graceful fallback: draft is still claim-grounded

    return {
        "llm_synthesis_used": True,
        "narrative":          narrative,
        "draft":              draft,
        "flags":              flags,
        "flags_resolved":     serious_count,
        "provider_log":       provider_log,
    }
