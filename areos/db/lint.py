# areos/db/lint.py
#
# Pre-insert linter for the claims table.
# Spec: AREOS_KNOWLEDGE_INGESTION_SPEC.md §2.6
#
# MUST be called before every INSERT into claims, regardless of source.
# Never raises — all errors are collected and returned.

import re
from typing import Any

LEGAL_STATUSES = {"active", "deprecated", "contested", "superseded"}
LEGAL_CLAIM_SCOPES = {"retrieval-pipeline", "audit-workflow", "general-knowledge"}
LEGAL_SOURCE_TIER_VOCABS = {"study_a", "study_b", "system_native", "corpus_handbook"}
LEGAL_CLAIM_TYPES = {
    # Original five core types
    "empirical", "operational", "policy", "heuristic", "outcome",
    # Study A (CLM-series — AEO/GEO analysis)
    "serp-feature", "schema-validity", "crawler-behavior",
    "ai-citation-effect", "ranking-factor", "other",
    # Study B (C0-series — automatability ratings)
    "automatability_rating", "empirical_stat", "claim_type_caveat",
    "process_note", "tooling_existence",
    # Corpus Handbook (C200–C324 — retrieval pipeline stages)
    "stage-technical-explainer", "stage-technical-fact",
    "stage-official-evidence", "stage-technical-explanation",
    "stage-industry-consensus",
}
LEGAL_SOURCE_TIER_COMBINATIONS = {
    ("study_a", "official-platform-docs"),
    ("study_a", "primary-research"),
    ("study_a", "reputable-practitioner"),
    ("study_a", "forum-or-vendor-blog"),
    ("study_a", "mixed"),
    ("study_b", "T1"),
    ("study_b", "T2"),
    ("study_b", "T3"),
    ("study_b", "T4"),
    ("study_b", "T5"),
    # FIX (Claims<->Sources Integrity Pass, Finding 2 / Blocker 2): sources.trust_tier's
    # own CHECK constraint (areos/db/schema/artifacts.py) has always
    # permitted T1..T7, but this list stopped at T5 — a gap, not a
    # documented governance decision anywhere in the Bible/ADRs. Once
    # claims.source_tier_value is correctly derived from a linked source's
    # real trust_tier (see genesis_loader.py), a claim whose only available
    # primary source is tiered T6 or T7 needs a legal value to land on
    # instead of being silently clamped to a nearby tier. Extended to match
    # what sources has always allowed.
    ("study_b", "T6"),
    ("study_b", "T7"),
    ("system_native", "internal-playbook"),
    ("system_native", "outcome-log"),
}
STAGE_ID_PATTERN = re.compile(r"^(STAGE-\d{2}|AP-\d{2})$")
CLAIM_ID_PATTERN = re.compile(r"^(C|CLM-|M)\d+")
FORBIDDEN_STATEMENT_PREFIXES = (
    "parent claim for tool ",
    "parent claim for policy ",
    "parent claim for ",
)
CANDIDATE_ID_PATTERN = re.compile(r"^CAND-")


def lint_claim(row: dict) -> list[str]:
    """
    Validate a candidate claims row before INSERT.
    Returns a list of error strings. Empty list = row is valid.
    Never raises — all errors are collected and returned.
    """
    errors: list[str] = []

    # Check 1: statement
    stmt: Any = row.get("statement")
    if stmt is None or str(stmt).strip() == "":
        errors.append("statement is null or empty")
    else:
        stmt_str = str(stmt).strip()
        if len(stmt_str) <= 20:
            errors.append(f"statement is too short ({len(stmt_str)} chars, minimum 21)")
        if stmt_str.lower().startswith(FORBIDDEN_STATEMENT_PREFIXES):
            errors.append(f"statement starts with forbidden placeholder prefix: '{stmt_str[:40]}'")

    # Check 2: stage_id (nullable, but if present must match pattern)
    stage: Any = row.get("stage_id")
    if stage is not None and str(stage).strip() != "":
        if not STAGE_ID_PATTERN.match(str(stage).strip()):
            errors.append(
                f"stage_id '{stage}' does not match ^(STAGE-\\d{{2}}|AP-\\d{{2}})$ — "
                "use stage_id_aliases.yaml to normalize"
            )

    # Check 3: claim_scope — NULL is a hard error
    scope: Any = row.get("claim_scope")
    if scope is None:
        errors.append(
            "claim_scope is NULL — must be one of: retrieval-pipeline, audit-workflow, general-knowledge"
        )
    elif str(scope).strip() not in LEGAL_CLAIM_SCOPES:
        errors.append(f"claim_scope '{scope}' is not a legal value")

    # Check 4: source_tier_vocab and source_tier_combination
    vocab: Any = row.get("source_tier_vocab")
    value: Any = row.get("source_tier_value")
    if vocab is None or str(vocab).strip() == "":
        errors.append("source_tier_vocab is null or empty")
    elif str(vocab).strip() not in LEGAL_SOURCE_TIER_VOCABS:
        errors.append(f"source_tier_vocab '{vocab}' is not a legal value")
    if value is None or str(value).strip() == "":
        errors.append("source_tier_value is null or empty")
    if vocab and value:
        pair = (str(vocab).strip(), str(value).strip())
        # corpus_handbook uses descriptive free-text values (e.g. "official-platform-doc (T1)")
        # rather than bare tier codes — exempt from strict pair validation.
        if str(vocab).strip() not in ("corpus_handbook",) and pair not in LEGAL_SOURCE_TIER_COMBINATIONS:
            errors.append(
                f"source_tier_vocab '{vocab}' + source_tier_value '{value}' "
                "is not a permitted combination (see Governance \u00a71.4)"
            )

    # Check 5: status
    status: Any = row.get("status")
    if status is None or str(status).strip() == "":
        errors.append("status is null or empty")
    elif str(status).strip().lower() not in LEGAL_STATUSES:
        errors.append(f"status '{status}' is not a legal value — must be one of: {LEGAL_STATUSES}")

    # Check 6: claim_id pattern and candidate block
    cid: Any = row.get("claim_id")
    if cid is None or str(cid).strip() == "":
        errors.append("claim_id is null or empty")
    else:
        cid_str = str(cid).strip()
        if CANDIDATE_ID_PATTERN.match(cid_str):
            errors.append(
                f"claim_id '{cid_str}' matches CAND- prefix — candidates cannot be "
                "inserted directly; run apply_candidates.py instead"
            )
        elif not CLAIM_ID_PATTERN.match(cid_str):
            errors.append(
                f"claim_id '{cid_str}' does not match ^(C|CLM-|M)\\d+ — unrecognized ID format"
            )

    # Check 7: claim_type
    ctype: Any = row.get("claim_type")
    if ctype is None or str(ctype).strip() == "":
        errors.append("claim_type is null or empty")
    elif str(ctype).strip().lower() not in LEGAL_CLAIM_TYPES:
        errors.append(
            f"claim_type '{ctype}' is not in the legal vocabulary "
            f"({LEGAL_CLAIM_TYPES}) — see Ontology §3.4"
        )

    # Check 8: superseded_by required if status = 'superseded'
    if status and str(status).strip().lower() == "superseded":
        sup_by: Any = row.get("superseded_by")
        if sup_by is None or str(sup_by).strip() == "":
            errors.append(
                "status is 'superseded' but superseded_by is null — "
                "must reference the replacement claim_id"
            )

    return errors
