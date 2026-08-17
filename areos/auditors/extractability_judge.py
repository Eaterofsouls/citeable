# areos/auditors/extractability_judge.py
#
# Task 3d: Content Extractability / Chunk-Quality LLM-as-Judge
#
# CONTRACT:
#   - Receives page content signals (extracted by the crawler).
#   - Produces an extractability rating: "high" | "medium" | "low" | "none"
#   - Uses an LLM as a judge, but MUST be validated against 3d-labels before
#     being used in any real report.
#   - Includes a compare_with_labels() function for benchmarking accuracy.
#
# IMPORTANT (per backlog): Compare judge output to your own labels first.
# Do not trust this in a report until that comparison is done.

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from areos.llm import providers as llm_providers
import json
import os

# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class ExtractabilityResult:
    page_id: str
    url: str
    label: str          # "high" | "medium" | "low" | "none"
    confidence: str     # "high" | "medium" | "low"
    rationale: str
    # Signal snapshot fed to judge
    signals_summary: dict


# ── Signal extraction ─────────────────────────────────────────────────────────

def build_signals(page_data: dict) -> dict:
    """
    Build a concise, judge-readable signal snapshot from crawler output.
    Works with the output format of advanced_deep_audit.py.
    """
    rag = page_data.get("rag_chunkability", {})
    return {
        "url": page_data.get("url", ""),
        "status_code": page_data.get("status_code", 0),
        "substantive_paragraphs": rag.get("total_substantive_paragraphs", 0),
        "avg_paragraph_word_count": round(rag.get("avg_paragraph_word_count", 0), 1),
        "heading_count": rag.get("heading_count", 0),
        "list_item_count": rag.get("list_item_count", 0),
        "faq_indicators": rag.get("faq_indicators", 0),
        "dom_node_count": page_data.get("dom_node_count", 0),
        "inline_script_bytes": page_data.get("script_stats", {}).get("inline_script_bytes", 0),
        "json_ld_count": len(page_data.get("json_lds", [])),
        "has_faq_schema": any(
            isinstance(b, dict) and b.get("@type") == "FAQPage"
            for b in page_data.get("json_lds", [])
        ),
    }


# ── Heuristic fast path (no LLM needed for obvious cases) ────────────────────

def _heuristic_check(signals: dict) -> Optional[str]:
    """
    Returns a label if the case is clear-cut enough to skip the LLM.
    Returns None if LLM judgment is genuinely needed.
    """
    # Non-200 or empty page → none
    if signals["status_code"] not in (200, 0):
        return "none"

    # Effectively no text content
    if signals["substantive_paragraphs"] < 2 and signals["list_item_count"] < 3:
        return "none"

    # Strong FAQ signal → high
    if signals["has_faq_schema"] and signals["faq_indicators"] >= 2:
        return "high"

    # No LLM needed — ambiguous
    return None


# ── LLM judge call ────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """\
You are an AEO/GEO (Answer Engine Optimisation) content extractability judge.
You will be given a set of technical signals about a web page.
Your task is to rate how well an AI answer engine (like ChatGPT, Perplexity, or Google AI Overviews) could extract a direct, citable answer from this page.

Output a JSON object with exactly these keys:
  "label": one of "high" | "medium" | "low" | "none"
  "confidence": one of "high" | "medium" | "low"
  "rationale": a one- to three-sentence explanation (be specific about the signals that drove your label)

Definitions:
  high   = A well-informed AI can extract a direct, complete, citable answer. Strong structural signals (FAQs, short bullets, clear headings).
  medium = Content is relevant but requires interpretation, or chunks poorly (long prose, multi-topic pages, interview-style text).
  low    = Content is present but buried behind JS, images, or poor structure.
  none   = No substantive content to extract (redirect, nav-only, login wall, error page).

Respond with ONLY valid JSON. No explanation outside the JSON object.
"""

def _call_llm_judge(signals: dict, client_keys: dict | None = None) -> dict:
    """
    Calls the LLM waterfall to perform judgment.
    Returns the parsed JSON response dict.
    """
    prompt = f"Page signals:\n{json.dumps(signals, indent=2)}\n\nRate this page's content extractability.\n\nRespond with ONLY valid JSON."
    
    raw = llm_providers.complete(prompt, system=JUDGE_SYSTEM_PROMPT, client_keys=client_keys)
    
    # Clean markdown formatting if present
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
        
    return json.loads(cleaned.strip())


# ── Main judge function ───────────────────────────────────────────────────────

def judge_page(
    page_data: dict,
    page_id: str = "",
    api_key: Optional[str] = None,
    model: str = "gemini-2.0-flash",
    client_keys: dict | None = None,
) -> ExtractabilityResult:
    """
    Judge a page's content extractability.
    Falls back to heuristics for clear-cut cases to save API calls.
    """
    url = page_data.get("url", "")
    signals = build_signals(page_data)

    # Fast-path heuristics first
    heuristic_label = _heuristic_check(signals)
    if heuristic_label is not None:
        return ExtractabilityResult(
            page_id=page_id,
            url=url,
            label=heuristic_label,
            confidence="high",
            rationale="Determined by heuristic (no LLM call needed).",
            signals_summary=signals,
        )

    ck = client_keys or {}
    # Make sure we have SOME key before calling
    has_key = api_key or ck.get("google") or ck.get("openai") or ck.get("groq") or ck.get("anthropic") or llm_providers.check_any_provider_configured(ck)
    
    if not has_key:
        return ExtractabilityResult(
            page_id=page_id,
            url=url,
            label="medium",
            confidence="low",
            rationale="No API key available; defaulted to medium.",
            signals_summary=signals,
        )

    try:
        result_dict = _call_llm_judge(signals, client_keys=client_keys)
        return ExtractabilityResult(
            page_id=page_id,
            url=url,
            label=result_dict.get("label", "medium"),
            confidence=result_dict.get("confidence", "low"),
            rationale=result_dict.get("rationale", ""),
            signals_summary=signals,
        )
    except Exception as e:
        return ExtractabilityResult(
            page_id=page_id,
            url=url,
            label="medium",
            confidence="low",
            rationale=f"LLM call failed ({e}); defaulted to medium.",
            signals_summary=signals,
        )


# ── Label comparison (for 3d-labels benchmarking) ────────────────────────────

@dataclass
class LabelComparison:
    page_id: str
    url: str
    human_label: str
    judge_label: str
    match: bool
    judge_rationale: str

def compare_with_labels(label_set_path: str, judge_results: list[ExtractabilityResult]) -> list[LabelComparison]:
    """
    Load 3d_label_set.yaml and compare human labels with judge results.
    Prints a summary report showing agreement rate.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML not installed. Run: pip install pyyaml")

    with open(label_set_path, encoding="utf-8") as f:
        label_data = yaml.safe_load(f)

    labels_by_id = {item["page_id"]: item for item in label_data.get("label_set", [])}
    comparisons = []

    for result in judge_results:
        human_entry = labels_by_id.get(result.page_id)
        if not human_entry:
            continue
        human_label = human_entry.get("your_label", "").strip()
        if not human_label:
            continue  # Not yet labeled

        match = human_label.lower() == result.label.lower()
        comparisons.append(LabelComparison(
            page_id=result.page_id,
            url=result.url,
            human_label=human_label,
            judge_label=result.label,
            match=match,
            judge_rationale=result.rationale,
        ))

    # Print summary
    if comparisons:
        matched = sum(1 for c in comparisons if c.match)
        print(f"\n== 3d Label Comparison Report ==")
        print(f"Pages compared: {len(comparisons)}")
        print(f"Agreement:      {matched}/{len(comparisons)} ({100*matched//len(comparisons)}%)")
        print()
        for c in comparisons:
            icon = "✅" if c.match else "❌"
            print(f"  {icon} {c.page_id} | Human: {c.human_label:6} | Judge: {c.judge_label:6} | {c.url}")
            if not c.match:
                print(f"       Judge rationale: {c.judge_rationale}")
    else:
        print("No labeled pages found to compare. Fill in 3d_label_set.yaml first.")

    return comparisons
