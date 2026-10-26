"""
areos/auditors/scoring.py
=========================
Layered AREOS Scoring Engine — Option B + C

Replaces the flat `100 - (errors×18) - (warnings×7)` formula with a
5-layer model where each layer carries its own weight and check codes
deduct points from the layer they belong to.

Model
-----
  AP-01  Access          20 pts  Prerequisite — gate layer
  AP-02  Schema          15 pts  Structural table stakes
  AP-03  Content         20 pts  Extractability signal
  AP-04  Citation        30 pts  Ground truth — cited or not
  AP-05  Authority       15 pts  External consensus

Access Gate (Option C)
-----------------------
If CRAWLER_FULLY_BLOCKED fires, overall score is hard-capped at 25
regardless of other layers. A well-structured site that blocks AI
crawlers has near-zero real-world AI readiness.

If CRAWLER_PARTIAL fires, cap is 65.

Stacking rule
-------------
Multiple findings in the same layer stack (sum), but each layer's
score is floored at 0. The overall score is floored at 5.

Usage
-----
    from areos.auditors.scoring import compute_layered_score

    result = compute_layered_score(findings)  # findings: list[dict]
    result.overall_score      # int, 5-98
    result.sub_scores         # dict layer_id → {score, max, label}
    result.score_breakdown    # dict layer_id → {deductions: [...]}
    result.access_gate_applied  # bool
    result.access_gate_cap      # int | None
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ── Layer definitions ──────────────────────────────────────────────────────────

LAYERS: dict[str, dict] = {
    "access": {
        "label":    "Access",
        "stage":    "AP-01",
        "max":      20,
        "rationale": "Prerequisite layer — AI crawlers must be able to reach the site. "
                     "If blocked, all other layers are irrelevant.",
    },
    "schema": {
        "label":    "Schema & Structure",
        "stage":    "AP-02",
        "max":      15,
        "rationale": "Structured data helps AI engines parse entity type, properties, "
                     "and relationships. Table stakes — necessary but not sufficient.",
    },
    "content": {
        "label":    "Content Format",
        "stage":    "AP-03",
        "max":      20,
        "rationale": "The #2 predictor of AI citation. If content cannot be chunked "
                     "and fact-extracted, AI models cannot form a coherent brand description.",
    },
    "citation": {
        "label":    "Citation Sampling",
        "stage":    "AP-04",
        "max":      30,
        "rationale": "Ground truth signal. Carries 30/100 because it directly measures "
                     "the outcome AREOS exists to improve — whether AI models cite the brand.",
    },
    "authority": {
        "label":    "Entity & Authority",
        "stage":    "AP-05",
        "max":      15,
        "rationale": "The #3 predictor. External consensus (Wikipedia entity, referring "
                     "domains, brand mentions) is how AI models validate brand legitimacy.",
    },
}

TOTAL_MAX = sum(v["max"] for v in LAYERS.values())   # 100
SCORE_FLOOR   = 5
SCORE_CEILING = 98


# ── Deduction table ────────────────────────────────────────────────────────────
# Maps check_code → (layer_id, points_deducted)
# Points are POSITIVE integers representing the deduction magnitude.
# Multiple findings in the same layer stack, floored at 0 for that layer.

LAYER_DEDUCTIONS: dict[str, tuple[str, int]] = {
    # ── AP-01 Access (max 20) ──────────────────────────────────────────────
    "CRAWLER_FULLY_BLOCKED":          ("access",    7),  # entire layer wiped
    "SEARCH_CRAWLER_BLOCKED":         ("access",   10),  # search-specific AI crawler blocked
    "AI_CRAWLER_HOST_BLOCKED":        ("access",    8),  # host/WAF blocks AI bots at infrastructure level
    "AI_OPTOUT_SIGNAL_PRESENT":       ("access",    0),  # informational Bing/Copilot opt-out signal
    "NOSNIPPET_BLOCKING_AI":          ("access",    3),  # blocks snippet extraction
    "CRAWLER_PARTIAL":                ("access",    2),  # some bots blocked
    "AUDIT_PHASE_CRASHED":            ("access",    2),  # audit sub-phase failure
    "INVALID_CRAWL_DELAY":            ("access",    1),

    # ── AP-02 Schema (max 15) ─────────────────────────────────────────────
    "MISSING_TYPE":                   ("schema",    4),  # no @type — schema invalid
    "JSON_PARSE_FAILURE":             ("schema",    3),  # unparseable JSON-LD block
    "MISSING_REQUIRED_FIELD":         ("schema",    2),  # required field absent
    "MISSING_RECOMMENDED_FIELD":      ("schema",    1),  # recommended field absent
    "UNKNOWN_FIELD":                  ("schema",    1),  # non-standard property used
    "UNKNOWN_SCHEMA_TYPE":            ("schema",    1),  # unrecognised @type
    "SCHEMA_MISSING":                 ("schema",    4),  # no JSON-LD at all

    # ── AP-03 Content (max 20) ────────────────────────────────────────────
    "EXTRACTABILITY_NONE":            ("content",   9),  # zero extractable content
    "EXTRACTABILITY_LOW":             ("content",   5),  # sparse/CSS-heavy content
    "EXTRACTABILITY_MEDIUM":          ("content",   3),  # partial extractability
    "ANSWER_NOT_NEAR_TOP":            ("content",   2),  # first answer >30% down page
    "ANSWER_NOT_SELF_CONTAINED":      ("content",   2),  # answer requires context
    "ANSWER_NOT_FACTUALLY_SPECIFIC":  ("content",   1),  # no numbers/dates/metrics
    "NO_LIST_OR_TABLE":               ("content",   1),  # no scannable structure

    # ── AP-04 Citation (max 30) ───────────────────────────────────────────
    "CITATION_NOT_OBSERVED":          ("citation", 30),  # not cited at all — full loss
    # CITATION_OBSERVED → no deduction (layer intact)

    # ── AP-05 Authority (max 15) ──────────────────────────────────────────
    "REFERRING_DOMAINS_CRITICAL":     ("authority", 5),  # <50 referring domains
    "WIKIPEDIA_ENTITY_MISSING":       ("authority", 5),  # no Wikidata/Wikipedia entity
    "BRAND_MENTIONS_STAGNANT":        ("authority", 3),  # no recent brand mentions

    # ── Phase 2-6 additions (T-301) ──────────────────────────────────────

    # AP-01 Access — redirect, cloaking, sitemap
    "REDIRECT_CHAIN_LONG":             ("access",    1),
    "REDIRECT_CHAIN_EXCESSIVE":        ("access",    3),
    "META_NOINDEX":                    ("access",    3),
    "CLOAKING_DETECTED":               ("access",    4),
    "CLOAKING_SUSPECTED":              ("access",    2),
    "AI_BOT_BLOCKED_HTTP":             ("access",    3),
    "SITEMAP_MISSING":                 ("access",    1),
    "SITEMAP_EMPTY":                   ("access",    1),
    "SITEMAP_NOT_IN_ROBOTS":           ("access",    1),
    "SITEMAP_PAGES_UNREACHABLE":       ("access",    1),

    # AP-02 Schema — canonical, entity, multi-page
    "CANONICAL_MISMATCH":              ("schema",    2),
    "CANONICAL_MISSING":               ("schema",    1),
    "REDIRECT_DOMAIN_CHANGE":          ("schema",    1),
    "ENTITY_NAME_MISSING":             ("schema",    2),
    "SAMEAS_MISSING":                  ("schema",    1),
    "SAMEAS_INCOMPLETE":               ("schema",    1),
    "SAMEAS_DEAD_LINK":                ("schema",    1),
    "WIKIDATA_MISSING":                ("schema",    1),

    # AP-03 Content — freshness, media, rendering
    "CONTENT_STALE":                   ("content",   2),
    "CONTENT_AGING":                   ("content",   1),
    "DATE_MISSING":                    ("content",   1),
    "IFRAME_HEAVY":                    ("content",   2),
    "IMAGES_MISSING_ALT":              ("content",   1),
    "ALL_CONTENT_IN_MEDIA":            ("content",   4),
    "VIDEO_NO_TRANSCRIPT":             ("content",   1),
    "SITEMAP_NO_LASTMOD":              ("content",   1),

    # AP-04 Citation — analytics
    "CITATION_RATE_LOW":               ("citation", 15),
    "SHARE_OF_VOICE_LOW":              ("citation", 10),

    # Additional Phase Findings & Auditor Integrations
    "MULTI_PAGE_SCHEMA_GAPS":          ("schema",    2),
    "MULTI_PAGE_THIN_CONTENT":         ("content",   2),
    "NEAR_DUPLICATE_PAGES":            ("content",   2),
    "COMPETITOR_SCHEMA_ADVANTAGE":     ("schema",    1),
    "COMPETITOR_CONTENT_ADVANTAGE":    ("content",   1),
    "JS_CRITICAL_CONTENT_GATED":       ("access",    4),
    "CLOAKING_FETCH_FAILED":           ("access",    2),
    "PAGE_FETCH_FAILED":               ("access",    4),
}


# ── Access gate ────────────────────────────────────────────────────────────────
# If a gate trigger fires, overall_score = min(cap, computed_score).

ACCESS_GATE: dict[str, int] = {
    "CRAWLER_FULLY_BLOCKED": 25,  # hard ceiling — AI can't reach the site
    "CRAWLER_PARTIAL":       65,  # soft ceiling — some AI access but incomplete
    "CLOAKING_DETECTED":     35,  # T-302: cloaked content → near-zero AI trust
    "META_NOINDEX":          15,  # T-302: noindex → page explicitly excluded from AI
}


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class LayerScore:
    layer_id:     str
    label:        str
    stage:        str
    score:        Optional[int]  # points remaining after deductions (≥ 0), or None if unconfigured
    max_points:   int
    deductions:   list[dict] = field(default_factory=list)
    unconfigured: bool = False
    # Each deduction: {code, points, message, running_total}

    @property
    def pct(self) -> Optional[float]:
        if self.unconfigured or self.score is None:
            return None
        return round(self.score / self.max_points * 100, 1) if self.max_points else 0.0

    def as_dict(self) -> dict:
        return {
            "score":        self.score,
            "max":          self.max_points,
            "pct":          self.pct,
            "label":        self.label,
            "stage":        self.stage,
            "deductions":   self.deductions,
            "unconfigured": self.unconfigured,
        }


@dataclass
class ScorecardResult:
    overall_score:          int
    sub_scores:             dict[str, LayerScore]
    access_gate_applied:    bool              = False
    access_gate_cap:        Optional[int]     = None
    raw_layer_total:        int               = 0  # before gate applied
    authority_excluded:     bool              = False
    readiness_score:        int               = 0  # WP-5.2 Model B (0-100)
    visibility_score:       int               = 0  # WP-5.2 Model B (0-100)
    visibility_confidence:  str               = "low"  # low (<5), medium (5-9), high (>=10)
    citation_samples_count: int               = 0

    def as_dict(self) -> dict:
        return {
            "overall_score":          self.overall_score,
            "overall_max":            85 if self.authority_excluded else 100,
            "authority_excluded":     self.authority_excluded,
            "readiness_score":        self.readiness_score,
            "visibility_score":       self.visibility_score,
            "visibility_confidence":  self.visibility_confidence,
            "citation_samples_count": self.citation_samples_count,
            "sub_scores":             {k: v.as_dict() for k, v in self.sub_scores.items()},
            "access_gate_applied":    self.access_gate_applied,
            "access_gate_cap":        self.access_gate_cap,
            "raw_layer_total":        self.raw_layer_total,
            # Convenience: flat breakdown list ordered by running total for display
            "score_breakdown":        self._flat_breakdown(),
        }

    def _flat_breakdown(self) -> list[dict]:
        """Returns a single ordered deduction ledger across all layers."""
        rows = []
        running = TOTAL_MAX
        for layer in self.sub_scores.values():
            for d in layer.deductions:
                rows.append(d)
        # Sort by running_total descending (order of deduction)
        return sorted(rows, key=lambda r: r.get("running_total", 0), reverse=True)


# ── Main computation ───────────────────────────────────────────────────────────

def compute_layered_score(
    findings: list[dict],
    authority_unconfigured: bool | None = None,
    citation_samples_count: int = 0,
) -> ScorecardResult:
    """
    Compute the layered AREOS score from a list of finding dicts.

    Each finding must have at least a 'code' key. The 'message' and
    'page_url' keys are used in the breakdown if present.

    Returns a ScorecardResult with overall_score (5–98), sub_scores
    per layer, and a full deduction ledger in score_breakdown.
    """
    if authority_unconfigured is None:
        authority_unconfigured = any(
            f.get("code") in ("AUTHORITY_UNCONFIGURED", "AUTHORITY_PROVIDER_UNAVAILABLE", "AUTHORITY_EXCLUDED")
            for f in findings
        )

    # Initialise each layer
    layers: dict[str, LayerScore] = {
        lid: LayerScore(
            layer_id=lid,
            label=meta["label"],
            stage=meta["stage"],
            score=None if (lid == "authority" and authority_unconfigured) else meta["max"],
            max_points=meta["max"],
            unconfigured=(lid == "authority" and authority_unconfigured),
        )
        for lid, meta in LAYERS.items()
    }

    # If authority is unconfigured, active points are out of 85 (WP-1.4 / DEF-04)
    active_max = sum(v["max"] for k, v in LAYERS.items() if not (k == "authority" and authority_unconfigured))
    running_total = active_max
    gate_cap: Optional[int] = None

    for finding in findings:
        code = finding.get("code", "")
        if code not in LAYER_DEDUCTIONS:
            continue  # informational or unknown codes — no deduction

        layer_id, pts = LAYER_DEDUCTIONS[code]
        if layer_id == "authority" and authority_unconfigured:
            continue

        layer = layers[layer_id]
        if layer.score is None:
            continue

        actual_pts = min(pts, layer.score)  # can't deduct more than what's left
        if actual_pts <= 0:
            continue  # layer already at 0

        layer.score -= actual_pts
        running_total -= actual_pts

        layer.deductions.append({
            "code":          code,
            "points":        -actual_pts,
            "message":       finding.get("message", ""),
            "page_url":      finding.get("page_url", ""),
            "running_total": running_total,
        })

        # Track strictest access gate triggered
        if code in ACCESS_GATE:
            cap = ACCESS_GATE[code]
            if gate_cap is None or cap < gate_cap:
                gate_cap = cap

    max_possible = min(active_max, SCORE_CEILING)
    raw_total = max(SCORE_FLOOR, min(max_possible, running_total))
    gate_applied = False

    if gate_cap is not None and raw_total > gate_cap:
        overall = gate_cap
        gate_applied = True
    else:
        overall = raw_total

    # ── Model B: Dual Readiness & Visibility scores (WP-5.2) ─────────────────
    access_pts = layers["access"].score or 0
    schema_pts = layers["schema"].score or 0
    content_pts = layers["content"].score or 0
    readiness = max(0, min(100, round(100 * (access_pts + schema_pts + content_pts) / 55)))

    citation_pts = layers["citation"].score or 0
    if authority_unconfigured:
        visibility = max(0, min(100, round(100 * citation_pts / 30)))
    else:
        authority_pts = layers["authority"].score or 0
        visibility = max(0, min(100, round(100 * (citation_pts + authority_pts) / 45)))

    if citation_samples_count < 5:
        vis_confidence = "low"
    elif citation_samples_count < 10:
        vis_confidence = "medium"
    else:
        vis_confidence = "high"

    return ScorecardResult(
        overall_score=overall,
        sub_scores=layers,
        access_gate_applied=gate_applied,
        access_gate_cap=gate_cap if gate_applied else None,
        raw_layer_total=raw_total,
        authority_excluded=authority_unconfigured,
        readiness_score=readiness,
        visibility_score=visibility,
        visibility_confidence=vis_confidence,
        citation_samples_count=citation_samples_count,
    )


# ── Convenience: legacy error/warning count still used in some reporting ───────

def count_severity(findings: list[dict]) -> tuple[int, int]:
    """Returns (error_count, warning_count) from a findings list."""
    errors   = sum(1 for f in findings if f.get("severity") == "error")
    warnings = sum(1 for f in findings if f.get("severity") == "warning")
    return errors, warnings
