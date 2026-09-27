# areos/auditors/citation_sampler.py
#
# Task 3e: AI-Engine Citation Sampler
#
# CONTRACT:
#   - Executes a fixed prompt set N times against AI engine APIs.
#   - Reports observed citation frequency as "N/M runs" — never a pass/fail score.
#   - The ToS caveat is HARDCODED into this module's output string. It cannot be
#     removed without editing this source file, ensuring it always travels with results.
#
# POLICY DECISION (Task 3e-policy, ratified 2026-07-30):
#   ACCEPTED engines and methods:
#     - Perplexity AI API (sonar models): paid API, ToS-compliant, explicitly allows
#       programmatic access and research use.
#     - Gemini API (grounded search mode): Google's own API with grounding toggle.
#   EXCLUDED engines (for this version):
#     - Google AI Overviews: no public API; scraping violates Google ToS.
#     - ChatGPT/GPT-4 browsing: no citation-extraction API; screen-scraping gray zone.
#     - Claude citations: Anthropic has no structured citation API.
#   FRAMING: All outputs are OBSERVED FREQUENCY, not a guaranteed measurement.
#   The statistical noise of a small N (default 5 runs) is acknowledged explicitly.
#
# NOTE ON ToS: Querying Perplexity/Gemini APIs with programmatic prompts
# is within their documented Terms of Service as of mid-2026. Citation
# sampling via unofficial scraping of ChatGPT, Google AI Overviews, or
# Bing Copilot is NOT included in this tool. If you add such capability,
# you must re-review the ToS of those services and update this policy section.

from __future__ import annotations

import json
import os
import time
import requests
from areos.util.ssrf import safe_get
from dataclasses import dataclass, field

def get_tos_caveat(engines: list[str] | str | None = None) -> str:
    """Return the mandatory ToS caveat string customized for the engines queried."""
    if isinstance(engines, str):
        engines = [e.strip() for e in engines.split(",") if e.strip()]
    normalized = [e.lower().strip() for e in (engines or []) if e.strip() and e.strip() != "none"]
    if not normalized:
        return (
            "[METHODOLOGY NOTE] No live citation sampling occurred because no supported AI engine API keys "
            "(Perplexity or Gemini) were configured. "
            "Google AI Overviews, ChatGPT browsing, and Bing Copilot are NOT sampled "
            "by this tool due to absence of a compliant API or ToS restrictions."
        )

    engine_names = []
    if "perplexity" in normalized:
        engine_names.append("the Perplexity sonar API")
    if "gemini" in normalized:
        engine_names.append("the Google Gemini grounded search API")
    for e in normalized:
        if e not in ("perplexity", "gemini"):
            engine_names.append(f"the {e} API")

    if len(engine_names) == 1:
        sampling_phrase = f"Sampling was performed via {engine_names[0]} — a programmatic API with compliant ToS."
    else:
        sampling_phrase = f"Sampling was performed via {' and '.join(engine_names)} — programmatic APIs with compliant ToS."

    return (
        "[METHODOLOGY NOTE] These citation results represent OBSERVED FREQUENCY only "
        "(cited in N/M sampled runs), not a guaranteed or reproducible measurement. "
        "AI engine outputs are probabilistic and vary across runs. "
        f"{sampling_phrase} "
        "Google AI Overviews, ChatGPT browsing, and Bing Copilot are NOT sampled "
        "by this tool due to absence of a compliant API or ToS restrictions."
    )


TOS_CAVEAT = get_tos_caveat


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class CitationObservation:
    run_index: int
    prompt: str
    engine: str
    cited_urls: list[str] = field(default_factory=list)
    raw_answer_snippet: str = ""
    full_answer_text: str = ""   # T-207: untruncated answer text
    error: str | None = None


@dataclass
class CitationSampleResult:
    target_domain: str
    prompt_set: list[str]
    engine: str
    n_runs: int
    observations: list[CitationObservation] = field(default_factory=list)
    tos_caveat: str = ""

    def __post_init__(self):
        if not self.tos_caveat:
            engines = [e.strip() for e in self.engine.split(",") if e.strip() and e.strip() != "none"] if self.engine else []
            self.tos_caveat = TOS_CAVEAT(engines)

    @property
    def citation_count(self) -> int:
        """How many runs cited the target domain at least once."""
        return sum(
            1
            for obs in self.observations
            if any(self.target_domain in url for url in obs.cited_urls)
        )

    @property
    def citation_rate_str(self) -> str:
        """Human-readable fraction, e.g. '3/5 runs'."""
        return f"{self.citation_count}/{self.n_runs} runs"

    def format_report(self) -> str:
        lines = [
            "Citation Sampling Report",
            "=" * 60,
            f"Target domain: {self.target_domain}",
            f"Engine:        {self.engine}",
            f"Runs:          {self.n_runs}",
            f"Cited:         {self.citation_rate_str}",
            "",
            "Per-run results:",
        ]
        for obs in self.observations:
            status = (
                "✓ CITED"
                if any(self.target_domain in u for u in obs.cited_urls)
                else "✗ not cited"  # noqa: E501
            )
            lines.append(f"  Run {obs.run_index+1}: {status}")
            if obs.cited_urls:
                for url in obs.cited_urls[:3]:
                    lines.append(f"    → {url}")
            if obs.error:
                lines.append(f"    ⚠ error: {obs.error}")
        lines += ["", self.tos_caveat]
        return "\n".join(lines)


# ── Perplexity API adapter ────────────────────────────────────────────────────


def _query_perplexity(prompt: str, api_key: str) -> tuple[list[str], str]:
    """
    Query Perplexity sonar API. Returns (cited_urls, answer_snippet).
    """
    payload = json.dumps(
        {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [{"role": "user", "content": prompt}],
            "return_citations": True,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.perplexity.ai/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_data = resp.read(5 * 1024 * 1024)
        if resp.read(1):  # if there's still data after 5MB
            raise ValueError("Response too large")
        data = json.loads(raw_data)

    answer = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])
    return citations, answer[:300], answer


# ── Gemini grounded search adapter ───────────────────────────────────────────


def _query_gemini_grounded(prompt: str, api_key: str) -> tuple[list[str], str, str]:
    """
    Query Gemini API with Google Search grounding. Returns (cited_urls, answer_snippet, full_answer).
    """
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }
    ).encode("utf-8")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent"
    )
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_data = resp.read(5 * 1024 * 1024)
        if resp.read(1):
            raise ValueError("Response too large")
        data = json.loads(raw_data)

    answer_parts = data["candidates"][0]["content"]["parts"]
    full_answer = " ".join(p.get("text", "") for p in answer_parts)

    # Extract grounding citations
    cited = []
    grounding = data["candidates"][0].get("groundingMetadata", {})
    for chunk in grounding.get("groundingChunks", []):
        web = chunk.get("web", {})
        if web.get("uri"):
            cited.append(web["uri"])

    return cited, full_answer[:300], full_answer


# ── Main sampler ──────────────────────────────────────────────────────────────


def load_active_prompt_set(
    target_domain: str | None = None, db_path: str | None = None
) -> list[str]:
    """Load active prompt texts from the governed prompt_sets database table."""
    from pathlib import Path

    from areos.db.connection import get_connection, get_db_path

    if db_path is None:
        # FIX (data-quality pass): this used to reimplement its own copy
        # of the test/RENDER/default three-way path resolution, which
        # matched the canonical logic today but could silently drift out
        # of sync with it over time. Delegate to the single source of
        # truth instead (areos.db.connection.get_db_path()).
        db_path = Path(get_db_path())
    else:
        db_path = Path(db_path)
    if not db_path.exists():
        return []
    try:
        conn = get_connection(db_path)
        if target_domain:
            rows = conn.execute(
                "SELECT prompt_text FROM prompt_sets WHERE active = 1 AND (target_domain = ? OR target_domain = '' OR target_domain IS NULL)",  # noqa: E501
                (target_domain,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT prompt_text FROM prompt_sets WHERE active = 1").fetchall()
        return [r["prompt_text"] if hasattr(r, "keys") else r[0] for r in rows]
    except Exception:
        return []


def sample_citations(
    target_domain: str,
    prompt_set: list[str] | None = None,
    engine: str = "perplexity",
    n_runs: int = 5,
    api_key: str | None = None,
    delay_seconds: float = 2.0,
    client_keys: dict | None = None,
    circuit_breaker: dict | None = None,
) -> CitationSampleResult:
    if circuit_breaker is None:
        circuit_breaker = {}
    """
    Run each prompt in prompt_set N times against the chosen engine.
    Returns a CitationSampleResult with observations and the mandatory ToS caveat.

    Args:
        target_domain: Domain to track (e.g. "areos.io").
        prompt_set:    List of prompts (if None, loaded from active prompt_sets DB table).
        engine:        "perplexity" or "gemini".
        n_runs:        Number of times to run each prompt.
        api_key:       API key for the chosen engine. Falls back to env vars.
        delay_seconds: Pause between runs (rate-limit courtesy).
    """
    if not prompt_set:
        prompt_set = load_active_prompt_set(target_domain)

    ck = client_keys or {}
    if engine == "perplexity":
        key = api_key or ck.get("perplexity") or os.environ.get("PERPLEXITY_API_KEY", "")
    else:
        key = api_key or ck.get("google") or ck.get("gemini") or os.environ.get("AREOS_GEMINI_KEY_1", "")

    result = CitationSampleResult(
        target_domain=target_domain,
        prompt_set=prompt_set,
        engine=engine,
        n_runs=n_runs * len(prompt_set),
        tos_caveat=TOS_CAVEAT([engine]) if key else TOS_CAVEAT([]),
    )

    run_index = 0
    for prompt in prompt_set:
        for _ in range(n_runs):
            obs = CitationObservation(run_index=run_index, prompt=prompt, engine=engine)
            if not key:
                obs.error = "No API key available. Set PERPLEXITY_API_KEY or AREOS_GEMINI_KEY_1."
                result.observations.append(obs)
                run_index += 1
                continue
            if circuit_breaker.get(engine, 0) >= 3:
                obs.error = f"Circuit breaker open for {engine}"
                result.observations.append(obs)
                run_index += 1
                continue
            try:
                if engine == "perplexity":
                    obs.cited_urls, obs.raw_answer_snippet, obs.full_answer_text = _query_perplexity(prompt, key)
                elif engine == "gemini":
                    obs.cited_urls, obs.raw_answer_snippet, obs.full_answer_text = _query_gemini_grounded(prompt, key)
                else:
                    raise ValueError(f"Unknown engine: {engine}")
            except Exception as e:
                obs.error = str(e)
                err_str = str(e).lower()
                circuit_breaker[engine] = circuit_breaker.get(engine, 0) + 1
                if "429" in err_str or "rate" in err_str or "quota" in err_str or "500" in err_str or "502" in err_str or "503" in err_str or "504" in err_str or "timeout" in err_str or "connection" in err_str:
                    backoff = min(16.0, max(delay_seconds, 1.0) * (2 ** circuit_breaker[engine]))
                    time.sleep(backoff)
            else:
                circuit_breaker[engine] = 0
            finally:
                result.observations.append(obs)
                run_index += 1
                if delay_seconds > 0:
                    time.sleep(delay_seconds)

    return result


# ── Citation analytics (T-208) ───────────────────────────────────────────────


def compute_citation_analytics(sample_result: CitationSampleResult) -> dict:
    """Calculate share-of-voice and competitor domain analysis from citation results.

    Returns a dict with:
      - target_domain: str
      - total_runs: int
      - cited_runs: int — runs where target domain appeared
      - citation_rate: float — cited_runs / total_runs
      - share_of_voice: float — target URLs / all URLs across runs
      - competitor_domains: list[dict] — [{domain, count, share}] sorted desc
      - total_unique_urls: int
    """
    from urllib.parse import urlparse
    from collections import Counter

    target = sample_result.target_domain.lower()
    observations = sample_result.observations or []
    total_runs = len(observations) or 1

    all_urls: list[str] = []
    cited_runs = 0
    for obs in observations:
        all_urls.extend(obs.cited_urls)
        if any(target in url.lower() for url in obs.cited_urls):
            cited_runs += 1

    total_urls = len(all_urls) or 1
    target_urls = sum(1 for u in all_urls if target in u.lower())

    # Count domains
    domain_counts: Counter[str] = Counter()
    for url in all_urls:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().lstrip("www.")
            domain_counts[domain] += 1
        except Exception:
            continue

    # Build competitor list (exclude target domain)
    competitors = []
    for domain, count in domain_counts.most_common():
        if target in domain:
            continue
        competitors.append({
            "domain": domain,
            "count": count,
            "share": round(count / total_urls, 4),
        })

    return {
        "target_domain": target,
        "total_runs": total_runs,
        "cited_runs": cited_runs,
        "citation_rate": round(cited_runs / total_runs, 4),
        "share_of_voice": round(target_urls / total_urls, 4),
        "competitor_domains": competitors,
        "total_unique_urls": len(set(all_urls)),
    }
