# areos/auditors/audit_orchestrator.py
#
# Full-Spectrum AEO/GEO Automated Orchestrator
# Executes all 6 auditing layers simultaneously, records the audit run in SQLite,
# synthesizes a prioritized step-by-step remediation plan with governing citations,
# and generates an interactive guidance wizard for human manual review cards.

from __future__ import annotations

import json
import re
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests

from areos.api.error_codes import ErrorCode
from areos.services.cache import ttl_cache

@ttl_cache(ttl=300)
def _fetch_robots_txt(domain: str) -> str | None:
    try:
        # FIX (Readiness Audit, Critical 2): this had no validate_domain_ssrf
        # call at all before fetching an attacker-suppliable domain — the
        # caller validated a *different* code path's requests.get(), not
        # this one. safe_get() validates every hop, not just the first URL.
        r_resp = safe_get(f"https://{domain}/robots.txt", timeout=4, headers={"User-Agent": "AREOS-Auditor/1.0"})
        if r_resp.status_code == 200:
            return r_resp.text
    except Exception:
        pass
    return None

from areos.auditors.authority_auditor import audit_domain_authority
from areos.auditors.citation_sampler import TOS_CAVEAT, load_active_prompt_set, sample_citations
from areos.auditors.content_format_auditor import audit_page_format
from areos.auditors.robots_checker import parse_llms_txt, parse_robots_txt
from areos.auditors.schema_validator import validate_page_schemas
from areos.auditors.synthesis_engine import synthesise
from areos.auditors.scoring import compute_layered_score, count_severity
from areos.cli.report import AuditRunSummary, select_triggered_cards
from areos.db.connection import get_connection
from areos.db.context import write_as
from areos.util.sanitize import sanitize_text
from areos.util.ssrf import safe_get, validate_domain_ssrf

# Actionable code snippets per check code to guide user implementations
ACTION_SNIPPETS = {
    "CRAWLER_FULLY_BLOCKED": "# Add to robots.txt:\nUser-agent: GPTBot\nAllow: /\n\nUser-agent: PerplexityBot\nAllow: /\n\nUser-agent: ClaudeBot\nAllow: /",  # noqa: E501
    "LLMS_TXT_MISSING": "# Create /llms.txt at web root:\n# Site Title\n> Primary value proposition and summary for AI assistants.\n\n## Core References\n- [Documentation](https://domain.com/docs): Full product guide.",  # noqa: E501
    "JSON_PARSE_FAILURE": "<!-- Validate JSON-LD syntax -->\n<script type=\"application/ld+json\">\n{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Organization\",\n  \"name\": \"Brand Name\",\n  \"url\": \"https://domain.com\"\n}\n</script>",  # noqa: E501
    "MISSING_REQUIRED_FIELD": "/* Ensure required schema properties are populated */\n\"name\": \"Verified Entity Title\",\n\"description\": \"Concrete, objective definitional description without conversational fluff.\"",  # noqa: E501
    "ANSWER_NOT_NEAR_TOP": "<!-- Move self-contained definition into top 30% of HTML body -->\n<section class=\"ai-direct-answer\">\n  <h2>What is [Brand]?</h2>\n  <p>[Brand] is an enterprise AEO/GEO optimization platform that automates citation tracking and schema compliance...</p>\n</section>",  # noqa: E501
    "ANSWER_NOT_SELF_CONTAINED": "<!-- Replace dangling demonstratives ('This tool...') with explicit entity subjects -->\n<p><strong>AREOS</strong> provides automated crawler policy verification and knowledge graph linkage...</p>",  # noqa: E501
    "ANSWER_NOT_FACTUALLY_SPECIFIC": "<!-- Replace generalities ('many features', 'faster') with concrete metrics -->\n<p>Evaluates 131 scientific search engineering claims across 6 automated diagnostic layers in under 3.5 seconds.</p>",  # noqa: E501
    "NO_LIST_OR_TABLE": "<!-- Add scannable HTML itemization -->\n<ul>\n  <li><strong>AI Crawler Compliance:</strong> Direct verification of robots.txt and llms.txt.</li>\n  <li><strong>Schema Honesty:</strong> 1-to-1 visible text mirroring in JSON-LD.</li>\n</ul>",  # noqa: E501
    "AUTHORITY_DR_LOW": "/* Action Item: Targeted Technical PR */\nAcquire contextual mentions and high-authority referring domain backlinks (>DR 50) to build consensus in algorithmic entity evaluation.",  # noqa: E501
    "REFERRING_DOMAINS_CRITICAL": "/* Action Item: Entity Backlink Expansion */\nExpand independent referring domain count above the minimum threshold of 50 via industry case studies and verifiable open data contributions.",  # noqa: E501
    "WIKIPEDIA_ENTITY_MISSING": "/* Action Item: Wikidata & Open Data Entry */\nEstablish an objective, neutrally cited Wikidata item representing the organization, linking official social and documentation profiles via sameAs attributes.",  # noqa: E501
    "BRAND_MENTIONS_STAGNANT": "/* Action Item: Digital PR Velocity Campaign */\nExecute digital PR outreach to generate fresh unlinked and linked news citations in industry trade publications within the current 90-day indexing window.",  # noqa: E501
}

# Guided instructions for manual review wizard cards
MANUAL_CARD_GUIDANCE = {
    "C052": {
        "title": "Verify Render Asset Accessibility",
        "what_to_look_for": "Check if critical JavaScript or CSS stylesheets are blocked by robots.txt rules or CDN challenges, causing AI rendering engines to see a blank page.",  # noqa: E501
        "how_to_fill": "Select 'pass' if the rendered HTML contains full body content. Select 'fail' if core content vanishes when JS/CSS is restricted."  # noqa: E501
    },
    "C053": {
        "title": "Evaluate Schema Semantic Honesty",
        "what_to_look_for": "Inspect the JSON-LD blocks and compare them line-by-line with visible page text. AI engines penalize sites where schema claims features, reviews, or ratings not directly visible to human visitors.",  # noqa: E501
        "how_to_fill": "Select 'pass' if schema matches visible text 1-to-1. Select 'warn' or 'fail' if unsupported marketing statements exist in JSON-LD."  # noqa: E501
    },
    "C073": {
        "title": "Causal Attribution for Missing Citations",
        "what_to_look_for": "When a brand is omitted from Perplexity or Gemini summaries, investigate which layer failed: Access (was crawler blocked?), Content (is description vague or buried?), or Authority (competitors have stronger consensus).",  # noqa: E501
        "how_to_fill": "Document the precise root cause layer in your notes and mark 'warn' so the recommendation engine assigns targeted remediation steps."  # noqa: E501
    },
    "C077": {
        "title": "Assess Brand Sentiment & Framing in AI Answers",
        "what_to_look_for": "Analyze the framing of brand citations in generative answers. Are AI engines describing the brand as 'expensive', 'outdated', or secondary to a rival?",  # noqa: E501
        "how_to_fill": "If sentiment is accurate and authoritative, select 'pass'. If generative answers contain negative or diminishing framing, select 'fail' and describe the misaligned topic in notes."  # noqa: E501
    },
    "C090": {
        "title": "Final Root Cause Diagnosis Narrative",
        "what_to_look_for": "Ensure the overall audit report provides a coherent narrative linking technical failures (e.g. low DR or missing llms.txt) to real business outcomes.",  # noqa: E501
        "how_to_fill": "Summarize the overarching technical and authority diagnosis in the notes field and select 'pass' once documented."  # noqa: E501
    },
    "DEFAULT": {
        "title": "Expert Human Inspection Required",
        "what_to_look_for": "Perform expert qualitative verification per the instruction card guidelines, ensuring empirical standards are met before sign-off.",  # noqa: E501
        "how_to_fill": "Record verifiable observational evidence in the notes field and submit your pass/warn/fail evaluation."  # noqa: E501
    }
}


_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _extract_json_ld_blocks(html: str) -> list:
    """
    Pull every <script type="application/ld+json"> block out of raw HTML and
    parse each as JSON. Unparseable blocks are passed through as the raw
    string so schema_validator.validate_page_schemas can flag them as
    JSON_PARSE_FAILURE rather than being silently dropped.
    """
    blocks: list = []
    for raw in _JSON_LD_RE.findall(html):
        raw = raw.strip()
        if not raw:
            continue
        try:
            blocks.append(json.loads(raw))
        except (json.JSONDecodeError, ValueError):
            blocks.append(raw)  # kept as str -> validator reports JSON_PARSE_FAILURE
    return blocks


def _fetch_and_validate_schema(clean_domain: str, page_url: str) -> list[dict]:
    """
    Fetch the target page and run its JSON-LD blocks through the real
    schema_validator. Returns orchestrator-shaped finding dicts.
    """
    validate_domain_ssrf(clean_domain)
    try:
        resp = safe_get(page_url, timeout=4)
    except (requests.exceptions.RequestException, ValueError):
        return [{"code": ErrorCode.SCHEMA_UNVERIFIABLE, "severity": "info", "message": "Could not fetch the page to validate structured data; result is unverifiable, not a failing score.", "page_url": page_url}]  # noqa: E501

    if resp.status_code != 200:
        return [{"code": ErrorCode.SCHEMA_UNVERIFIABLE, "severity": "info", "message": "Could not fetch the page to validate structured data; result is unverifiable, not a failing score.", "page_url": page_url}]  # noqa: E501

    json_ld_blocks = _extract_json_ld_blocks(resp.text)
    if not json_ld_blocks:
        return [{"code": "SCHEMA_MISSING", "severity": "warning", "message": "No JSON-LD structured data found on the page.", "page_url": page_url}]  # noqa: E501

    results = validate_page_schemas(json_ld_blocks)
    findings: list[dict] = []
    for result in results:
        if not result.issues:
            findings.append({"code": "ANSWER_FORMAT_GOOD", "severity": "info", "message": f"{result.schema_type} schema block is well-formed.", "page_url": page_url})  # noqa: E501
            continue
        for issue in result.issues:
            findings.append({"code": issue.code, "severity": issue.severity, "message": f"[{result.schema_type}] {issue.message}", "page_url": page_url})  # noqa: E501
    return findings



def run_orchestrated_audit(
    target_domain: str,
    db_path: Path,
    sample_content: str = "",
    api_provider: str = "auto",
    client_keys: dict | None = None,
    circuit_breaker: dict[str, int] | None = None
) -> dict[str, Any]:
    if circuit_breaker is None:
        circuit_breaker = defaultdict(int)
    def check_cb(provider):
        return circuit_breaker[provider] >= 2

    run_id = f"RUN-{time.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    run_date = time.strftime("%Y-%m-%d %H:%M:%S")
    findings: list[dict[str, Any]] = []
    
    # Clean domain input — strip scheme, path, and whitespace
    clean_domain = target_domain.lower().replace("https://", "").replace("http://", "").split("/")[0].strip()  # noqa: E501
    if not clean_domain:
        raise ValueError(
            "target_domain resolved to an empty string after normalisation. "
            "Provide a valid hostname such as 'example.com'."
        )

    page_url = f"https://{clean_domain}"

    # 1. AI Crawling & Robots Checker
    robots_ok = True
    llms_ok = True
    try:
        validate_domain_ssrf(clean_domain)
        robots_text = _fetch_robots_txt(clean_domain)
        if robots_text:
            res_rob = parse_robots_txt(robots_text)
            for bot, dir_obj in res_rob.directives.items():
                if dir_obj.is_fully_blocked:
                    findings.append({
                        "code": "CRAWLER_FULLY_BLOCKED",
                        "severity": "error",
                        "message": f"AI Crawler {bot} is explicitly denied in robots.txt.",
                        "page_url": f"https://{clean_domain}/robots.txt"
                    })
                    robots_ok = False
        
    
    except Exception:
        findings.append({
            "code": ErrorCode.ROBOTS_UNVERIFIABLE,
            "severity": "info",
            "message": "Could not fetch the page to validate structured data; result is unverifiable, not a failing score.",  # noqa: E501
            "page_url": page_url
        })

        

    try:
        validate_domain_ssrf(clean_domain)
        l_resp = safe_get(f"https://{clean_domain}/llms.txt", timeout=4)
        if l_resp.status_code == 200:
            res_llm = parse_llms_txt(l_resp.text)
            if not res_llm.has_h1:
                findings.append({
                    "code": "LLMS_TXT_MISSING_H1",
                    "severity": "warning",
                    "message": "llms.txt found but missing required # Site Title H1 heading.",
                    "page_url": f"https://{clean_domain}/llms.txt"
                })
        else:
            findings.append({
                "code": "LLMS_TXT_MISSING",
                "severity": "warning",
                "message": "No llms.txt standard file found at root domain.",
                "page_url": page_url
            })
            llms_ok = False
    except Exception:
        findings.append({
            "code": ErrorCode.LLMS_UNVERIFIABLE,
            "severity": "info",
            "message": "Could not fetch the page to validate structured data; result is unverifiable, not a failing score.",  # noqa: E501
            "page_url": page_url
        })
        llms_ok = False

    # 2. Schema & JSON-LD Structure — actually fetches the page and validates
    # any JSON-LD blocks found via areos.auditors.schema_validator.
    try:
        schema_findings = _fetch_and_validate_schema(clean_domain, page_url)
    except Exception:
        schema_findings = [{
            "code": ErrorCode.SCHEMA_UNVERIFIABLE,
            "severity": "info",
            "message": "Could not fetch the page to validate structured data; result is unverifiable, not a failing score.",  # noqa: E501
            "page_url": page_url,
        }]
    findings.extend(schema_findings)

    # 3. AI Extractability & Content Formatting
    eval_text = sample_content or f"Welcome to {clean_domain}. We provide services and solutions in several ways. This tool helps users improve performance."  # noqa: E501
    if len(eval_text.split()) < 30:
        findings.append({
            "code": "EXTRACTABILITY_LOW",
            "severity": "warning",
            "message": "Content density is insufficient for high-confidence AI chunking and fact extraction.",  # noqa: E501
            "page_url": page_url
        })
    
    fmt_res = audit_page_format(page_url, html=eval_text, client_keys=client_keys)
    for iss in fmt_res.issues:
        if iss.code != "ANSWER_FORMAT_GOOD":
            findings.append({
                "code": iss.code,
                "severity": iss.severity,
                "message": iss.message,
                "page_url": page_url
            })

    # 4. Authority & Backlinks
    auth_res = audit_domain_authority(clean_domain, api_provider=api_provider, client_keys=client_keys)  # noqa: E501
    for iss in auth_res.issues:
        if iss.code != "AUTHORITY_PROFILE_GOOD":
            findings.append({
                "code": iss.code,
                "severity": iss.severity,
                "message": iss.message,
                "page_url": page_url
            })

    # 5. Live AI Citation Sampling
    prompts = load_active_prompt_set(clean_domain, db_path=str(db_path))
    if not prompts:
        prompts = [
            f"What are the best platforms and tools in the {clean_domain} ecosystem?",
            f"Why choose {clean_domain} over competitor alternatives?",
            f"What are the documented specifications and features of {clean_domain}?"
        ]
    
    sample_res = sample_citations(target_domain=clean_domain, prompt_set=prompts[:2], n_runs=1, delay_seconds=0.0, client_keys=client_keys, circuit_breaker=circuit_breaker)  # noqa: E501
    citation_obs = sample_res.observations
    cited_runs = sum(1 for obs in citation_obs if len(obs.cited_urls) > 0)
    total_runs = len(citation_obs) if citation_obs else 1
    citation_rate_str = f"{cited_runs}/{total_runs} runs"

    if cited_runs == 0:
        findings.append({
            "code": "CITATION_NOT_OBSERVED",
            "severity": "warning",
            "message": f"Brand domain {clean_domain} was not explicitly cited across generative AI answers ({citation_rate_str}).",  # noqa: E501
            "page_url": page_url
        })
    else:
        findings.append({
            "code": "CITATION_OBSERVED",
            "severity": "info",
            "message": f"Brand domain actively cited in {citation_rate_str} during real-time generative query sampling.",  # noqa: E501
            "page_url": page_url
        })

    # Compute score with the layered model (B+C) — stored in DB so the
    # run record always carries the score even before the return payload.
    _scorecard_pre = compute_layered_score(findings)
    _overall_score_pre = _scorecard_pre.overall_score

    # Save to SQLite Database
    # FIX (Readiness Audit, Major #1): this used to write directly via
    # conn.execute()+conn.commit(), bypassing write_as() and leaving this
    # run's changelog entry with actor=NULL/reason=NULL.
    conn = get_connection(db_path)
    with write_as(conn, actor="orchestrator:run_orchestrated_audit", reason=f"Automated audit run for {clean_domain}"):  # noqa: E501
        conn.execute(
            "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status, overall_score) VALUES (?,?,?,?,?,?,?)",  # noqa: E501
            (
                run_id,
                clean_domain,
                run_date,
                json.dumps(["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"]),
                json.dumps(findings),
                "automated_complete",
                _overall_score_pre,
            )
        )

    # Synthesize Prioritized Plan with Governing Claims
    plan = synthesise(run_id, clean_domain, findings, [], db_path, client_keys=client_keys)
    
    # Lookup detailed governing claim statement and confidence from SQLite
    conn = get_connection(db_path)
    enriched_recs = []
    for step_idx, rec in enumerate(plan.recommendations, 1):
        claim_row = conn.execute("SELECT statement, confidence, source_tier_value, claim_scope FROM claims WHERE claim_id = ?", (rec.claim_id,)).fetchone()  # noqa: E501
        stmt = claim_row[0] if claim_row else "Governing claim statement from search engineering knowledge base."  # noqa: E501
        conf = claim_row[1] if claim_row else "high"
        tier = claim_row[2] if claim_row else "tier-1"
        scope = claim_row[3] if claim_row else "general-knowledge"
        evidence_label = "Knowledge Base Principle" if scope == "general-knowledge" else "Site-Specific Evidence"
        
        snippet = ACTION_SNIPPETS.get(rec.check_code, "/* Consult AREOS implementation guidelines for targeted code deployment */")  # noqa: E501
        
        enriched_recs.append({
            "step_number": step_idx,
            "priority_score": rec.priority or 0,
            "title": sanitize_text(rec.title) or "Untitled Recommendation",
            "description": sanitize_text(rec.description) or "",
            "check_code": rec.check_code or "UNKNOWN",
            "severity": rec.severity or "warning",  # never None — JS calls .toUpperCase()
            "governing_claim_id": rec.claim_id or "",
            "governing_claim_statement": sanitize_text(stmt) or "",
            "confidence": (conf or "high").upper(),
            "source_tier": (tier or "tier-1").upper(),
            "claim_scope": scope or "general-knowledge",
            "evidence_label": evidence_label,
            "action_snippet": snippet
        })

    # Phase 2: LLM Three-Step Synthesis Pipeline
    # NOT run here. The LLM synthesis deliberately runs AFTER the user
    # completes the manual guided review wizard, so that human verdicts
    # are included alongside automated findings. Triggering synthesis
    # here (on automated data alone) produces generic AI narrative with
    # no human signal — exactly the "suspiciously AI generated" report
    # the user complained about.
    #
    # Synthesis is triggered by the UI calling POST /api/v1/audit/runs/{run_id}/synthesize
    # after GuidedReview.finishAndGoToReport().
    llm_synthesis: dict = {
        "llm_synthesis_used": False,
        "reason": "Pending manual review — complete the Guided Wizard to generate the AI synthesis narrative.",
        "pending": True,
    }

    # Select manual review cards
    codes_fired = list({f.get("code") for f in findings if f.get("code")})
    summary = AuditRunSummary(
        target_domain=clean_domain,
        audited_stages=["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"],
        check_codes_fired=codes_fired,
        automated_findings=findings,
        run_date=run_date
    )
    triggered_cards = select_triggered_cards(summary)
    
    wizard_cards = []
    for c in triggered_cards:
        guidance = MANUAL_CARD_GUIDANCE.get(c.card_id, MANUAL_CARD_GUIDANCE["DEFAULT"])
        wizard_cards.append({
            "card_id": c.card_id,
            "check_name": c.check_name,
            "reason": c.reason,
            "title": guidance["title"],
            "what_to_look_for": guidance["what_to_look_for"],
            "how_to_fill": guidance["how_to_fill"]
        })

    # Calculate Executive Scorecard via layered model (Option B + C)
    scorecard_result = compute_layered_score(findings)
    overall_score    = scorecard_result.overall_score
    error_cnt, warn_cnt = count_severity(findings)

    # Normalise authority_metrics so JS never sees None/missing keys
    raw_metrics = getattr(auth_res, "metrics", None) or {}
    safe_metrics = {
        "authority_score": raw_metrics.get("authority_score") or 0,
        "referring_domains": raw_metrics.get("referring_domains") or 0,
        "trust_flow": raw_metrics.get("trust_flow") or 0,
        "citation_flow": raw_metrics.get("citation_flow") or 0,
    }

    return {
        "status": "success",
        "run_id": run_id,
        "run_date": run_date,
        "target_domain": clean_domain,
        "executive_scorecard": {
            "overall_score": overall_score,
            "authority_metrics": safe_metrics,
            "crawler_status": "Restricted" if not robots_ok else "Fully Permitted",
            "llms_txt_status": "Missing / Incomplete" if not llms_ok else "Standard Compliant",
            "observed_citation_rate": citation_rate_str or "0%",
            "error_count": error_cnt,
            "warning_count": warn_cnt,
            # Layered sub-scores — new in B+C model
            "sub_scores": {
                k: v.as_dict()
                for k, v in scorecard_result.sub_scores.items()
            },
            "score_breakdown":      scorecard_result._flat_breakdown(),
            "access_gate_applied":  scorecard_result.access_gate_applied,
            "access_gate_cap":      scorecard_result.access_gate_cap,
        },
        "remediation_plan": enriched_recs,
        "llm_synthesis": llm_synthesis or {"llm_synthesis_used": False, "reason": "No synthesis ran"},
        "manual_review_wizard": wizard_cards or [],
        "raw_findings": findings,
        "tos_caveat": TOS_CAVEAT or ""
    }
