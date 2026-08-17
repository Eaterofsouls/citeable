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
    "CRAWLER_FULLY_BLOCKED":          ("access",   20),  # entire layer wiped
    "NOSNIPPET_BLOCKING_AI":          ("access",    8),  # blocks snippet extraction
    "LLMS_TXT_MISSING":               ("access",    6),  # no AI context file at all
    "CRAWLER_PARTIAL":                ("access",    5),  # some bots blocked
    "GPTBOT_MISSING":                 ("access",    3),  # GPTBot not explicitly allowed
    "GOOGLE_EXTENDED_MISSING":        ("access",    3),  # Google-Extended not allowed
    "LLMS_TXT_MISSING_H1":            ("access",    2),  # file exists but malformed
    "LLMS_TXT_MISSING_SECTION":       ("access",    2),
    "LLMS_TXT_NO_LINKS":              ("access",    2),
    "LLMS_TXT_EMPTY_CONTENT":         ("access",    2),
    "INVALID_CRAWL_DELAY":            ("access",    1),

    # ── AP-02 Schema (max 15) ─────────────────────────────────────────────
    "MISSING_TYPE":                   ("schema",    8),  # no @type — schema invalid
    "JSON_PARSE_FAILURE":             ("schema",    7),  # unparseable JSON-LD block
    "MISSING_REQUIRED_FIELD":         ("schema",    5),  # required field absent
    "MISSING_RECOMMENDED_FIELD":      ("schema",    3),  # recommended field absent
    "UNKNOWN_FIELD":                  ("schema",    2),  # non-standard property used
    "UNKNOWN_SCHEMA_TYPE":            ("schema",    2),  # unrecognised @type
    "SCHEMA_MISSING":                 ("schema",   10),  # no JSON-LD at all

    # ── AP-03 Content (max 20) ────────────────────────────────────────────
    "EXTRACTABILITY_NONE":            ("content",  20),  # zero extractable content
    "EXTRACTABILITY_LOW":             ("content",  12),  # sparse/CSS-heavy content
    "EXTRACTABILITY_MEDIUM":          ("content",   6),  # partial extractability
    "ANSWER_NOT_NEAR_TOP":            ("content",   4),  # first answer >30% down page
    "ANSWER_NOT_SELF_CONTAINED":      ("content",   4),  # answer requires context
    "ANSWER_NOT_FACTUALLY_SPECIFIC":  ("content",   3),  # no numbers/dates/metrics
    "NO_LIST_OR_TABLE":               ("content",   2),  # no scannable structure

    # ── AP-04 Citation (max 30) ───────────────────────────────────────────
    "CITATION_NOT_OBSERVED":          ("citation", 30),  # not cited at all — full loss
    # CITATION_OBSERVED → no deduction (layer intact)

    # ── AP-05 Authority (max 15) ──────────────────────────────────────────
    "AUTHORITY_DR_LOW":               ("authority", 6),  # domain rating < threshold
    "REFERRING_DOMAINS_CRITICAL":     ("authority", 5),  # <50 referring domains
    "WIKIPEDIA_ENTITY_MISSING":       ("authority", 5),  # no Wikidata/Wikipedia entity
    "BRAND_MENTIONS_STAGNANT":        ("authority", 3),  # no recent brand mentions
}


# ── Access gate ────────────────────────────────────────────────────────────────
# If a gate trigger fires, overall_score = min(cap, computed_score).

ACCESS_GATE: dict[str, int] = {
    "CRAWLER_FULLY_BLOCKED": 25,  # hard ceiling — AI can't reach the site
    "CRAWLER_PARTIAL":       65,  # soft ceiling — some AI access but incomplete
}


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class LayerScore:
    layer_id:   str
    label:      str
    stage:      str
    score:      int          # points remaining after deductions (≥ 0)
    max_points: int
    deductions: list[dict] = field(default_factory=list)
    # Each deduction: {code, points, message, running_total}

    @property
    def pct(self) -> float:
        return round(self.score / self.max_points * 100, 1) if self.max_points else 0.0

    def as_dict(self) -> dict:
        return {
            "score":      self.score,
            "max":        self.max_points,
            "pct":        self.pct,
            "label":      self.label,
            "stage":      self.stage,
            "deductions": self.deductions,
        }


@dataclass
class ScorecardResult:
    overall_score:       int
    sub_scores:          dict[str, LayerScore]
    access_gate_applied: bool              = False
    access_gate_cap:     Optional[int]     = None
    raw_layer_total:     int               = 0  # before gate applied

    def as_dict(self) -> dict:
        return {
            "overall_score":       self.overall_score,
            "sub_scores":          {k: v.as_dict() for k, v in self.sub_scores.items()},
            "access_gate_applied": self.access_gate_applied,
            "access_gate_cap":     self.access_gate_cap,
            "raw_layer_total":     self.raw_layer_total,
            # Convenience: flat breakdown list ordered by running total for display
            "score_breakdown":     self._flat_breakdown(),
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

def compute_layered_score(findings: list[dict]) -> ScorecardResult:
    """
    Compute the layered AREOS score from a list of finding dicts.

    Each finding must have at least a 'code' key. The 'message' and
    'page_url' keys are used in the breakdown if present.

    Returns a ScorecardResult with overall_score (5–98), sub_scores
    per layer, and a full deduction ledger in score_breakdown.
    """
    # Initialise each layer at full points
    layers: dict[str, LayerScore] = {
        lid: LayerScore(
            layer_id=lid,
            label=meta["label"],
            stage=meta["stage"],
            score=meta["max"],
            max_points=meta["max"],
        )
        for lid, meta in LAYERS.items()
    }

    running_total = TOTAL_MAX
    gate_cap: Optional[int] = None

    for finding in findings:
        code = finding.get("code", "")
        if code not in LAYER_DEDUCTIONS:
            continue  # informational or unknown codes — no deduction

        layer_id, pts = LAYER_DEDUCTIONS[code]
        layer = layers[layer_id]

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

    raw_total = max(SCORE_FLOOR, min(SCORE_CEILING, running_total))
    gate_applied = False

    if gate_cap is not None and raw_total > gate_cap:
        overall = gate_cap
        gate_applied = True
    else:
        overall = raw_total

    return ScorecardResult(
        overall_score=overall,
        sub_scores=layers,
        access_gate_applied=gate_applied,
        access_gate_cap=gate_cap if gate_applied else None,
        raw_layer_total=raw_total,
    )


# ── Convenience: legacy error/warning count still used in some reporting ───────

def count_severity(findings: list[dict]) -> tuple[int, int]:
    """Returns (error_count, warning_count) from a findings list."""
    errors   = sum(1 for f in findings if f.get("severity") == "error")
    warnings = sum(1 for f in findings if f.get("severity") == "warning")
    return errors, warnings
