# areos/db/ingest_claims.py
#
# One-time (idempotent) knowledge-base seed loader.
#
# Loads active_claims.json into the `claims` table (supports both list format
# and the newer dict-wrapped {"claims": [...]} format from Claude's rebuild),
# then populates `check_code_mappings` from the in-file dict.
#
# Design decisions (see Preparing-Areos-for-deployment.md for the full
# reasoning trail):
#
#   * We do NOT invent claim content. Every row inserted comes verbatim from
#     active_claims.json's own fields (claim_id, claim_type, claim_scope,
#     stage_id, confidence, statement).
#   * active_claims.json may carry status, source_tier_vocab, source_tier_value,
#     source_url, and source_date. When present, _build_row reads them directly;
#     the disclosed defaults are only used when a field is absent.
#   * Every row is run through the project's own areos/db/lint.py::lint_claim
#     before insert (the documented pre-insert contract). Rows that fail
#     lint are skipped, not coerced — coercing bad legacy data into passing
#     silently would be worse than an honest gap in a product about citation
#     accuracy. Skips are collected and reported.
#   * check_code_mappings has a FOREIGN KEY into claims. Four of the twelve
#     check-code -> claim_id mappings (C310, C284, C292, C293) reference
#     claim_ids that do not exist anywhere in active_claims.json — they were
#     apparently never added to this file. We do NOT fabricate placeholder
#     claims to satisfy the FK. Those four mappings are skipped and reported;
#     everything else wires normally. This is a legitimate, disclosed content
#     gap (see the "Your actual options" section of the prep doc) — not a
#     code defect.
#   * Idempotent: safe to run multiple times against the same DB
#     (INSERT OR IGNORE on claim_id / (check_code, claim_id)).
#   * Never calls conn.close() — respects the MF-11 pooled-connection
#     contract in areos/db/connection.py.

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from areos.db.connection import get_connection, get_db_path  # noqa: E402
from areos.db.context import write_as  # noqa: E402
from areos.db.kb_version import increment_kb_version  # noqa: E402
from areos.db.lint import lint_claim  # noqa: E402
from areos.db.migrate_audit_tables import migrate  # noqa: E402
from areos.db.stage_normalization import normalize_stage_id  # noqa: E402

_CLAIMS_JSON = _ROOT / "active_claims.json"

# Disclosed default for the two NOT NULL columns active_claims.json never
# carried, plus the status column it never carried either. See module
# docstring above for why this specific pair is the right default.
_DEFAULT_SOURCE_TIER_VOCAB = "system_native"
_DEFAULT_SOURCE_TIER_VALUE = "internal-playbook"
_DEFAULT_STATUS = "active"

# check_code -> claim_id, copied verbatim from the two pre-existing,
# already-correct one-off migration scripts. Kept here (rather than
# importing those scripts) because they are standalone entry points with
# their own __main__ / hardcoded DB_PATH, not importable modules.
_CHECK_CODE_MAPPINGS: dict[str, list[str]] = {
    "MISSING_REQUIRED_FIELD": ["C054"],
    "MISSING_RECOMMENDED_FIELD": ["C054"],
    "UNKNOWN_FIELD": ["C054"],
    "MISSING_TYPE": ["C054"],
    "JSON_PARSE_FAILURE": ["C054"],
    "UNKNOWN_SCHEMA_TYPE": ["C054"],
    "CRAWLER_FULLY_BLOCKED": ["C050"],
    "CRAWLER_PARTIAL": ["C050"],
    "CRAWLER_ALLOWED": ["C050"],
    "NO_DIRECTIVE": ["C050"],
    "GOOGLE_EXTENDED_MISSING": ["C050"],
    "GPTBOT_MISSING": ["C050"],
    "INVALID_CRAWL_DELAY": ["C050"],
    "LLMS_TXT_MISSING": ["C051"],
    "LLMS_TXT_MISSING_H1": ["C051"],
    "LLMS_TXT_MISSING_SECTION": ["C051"],
    "LLMS_TXT_NO_LINKS": ["C051"],
    "LLMS_TXT_EMPTY_CONTENT": ["C051"],
    "EXTRACTABILITY_HIGH": ["C057"],
    "EXTRACTABILITY_MEDIUM": ["C061"],
    "EXTRACTABILITY_LOW": ["C058"],
    "EXTRACTABILITY_NONE": ["C058"],
    "CITATION_OBSERVED": ["C071"],
    "CITATION_NOT_OBSERVED": ["C071"],
    "CITATION_WHY_UNKNOWN": ["C073"],
    "ANSWER_NOT_NEAR_TOP": ["C051"],
    "ANSWER_NOT_SELF_CONTAINED": ["C057"],
    "ANSWER_NOT_FACTUALLY_SPECIFIC": ["C061"],
    "NO_LIST_OR_TABLE": ["C050"],
    "NOSNIPPET_BLOCKING_AI": ["C310"],
    "ANSWER_FORMAT_GOOD": ["C050"],
    "AUTHORITY_DR_LOW": ["C292"],
    "REFERRING_DOMAINS_CRITICAL": ["C292"],
    "WIKIPEDIA_ENTITY_MISSING": ["C284"],
    "BRAND_MENTIONS_STAGNANT": ["C293"],
    "AUTHORITY_PROFILE_GOOD": ["C293"],
}


def _load_source_rows() -> list[dict[str, Any]]:
    """Load claims from active_claims.json. Handles both list and dict-wrapped formats."""
    data = json.loads(_CLAIMS_JSON.read_text(encoding="utf-8"))
    # Claude's rebuilt JSON uses {"claims": [...], "sources": [...]} wrapper
    return data["claims"] if isinstance(data, dict) else data


def _build_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Map an active_claims.json record onto the claims table's columns.

    Reads status, source_tier_vocab, source_tier_value, source_url and
    source_date from the JSON when present; falls back to the disclosed
    defaults only when the field is absent.
    """
    return {
        "claim_id": raw.get("claim_id"),
        "stage_id": raw.get("stage_id"),
        "claim_scope": raw.get("claim_scope"),
        "claim_type": raw.get("claim_type"),
        "statement": raw.get("statement"),
        "status": raw.get("status", _DEFAULT_STATUS),
        "confidence": raw.get("confidence"),
        "source_url": raw.get("source_url"),
        "source_tier_vocab": raw.get("source_tier_vocab", _DEFAULT_SOURCE_TIER_VOCAB),
        "source_tier_value": raw.get("source_tier_value", _DEFAULT_SOURCE_TIER_VALUE),
        "source_date": raw.get("source_date"),
        "last_verified": None,
        "superseded_by": None,
    }


def ingest(db_path: Path | str | None = None, *, verbose: bool = True) -> dict[str, Any]:
    """
    Idempotently load active_claims.json into `claims`, then wire
    `check_code_mappings` on top. Returns a summary dict; never raises for
    data-quality issues (those are collected), but does raise on hard
    infrastructure failures (missing file, migration failure — MF-9).
    """
    if db_path is None:
        # FIX (Readiness Audit, Blocker 3): resolve via the shared,
        # Render-aware get_db_path() instead of a hardcoded repo-root path,
        # so `python -m areos.db.ingest_claims` seeds the same file the
        # running app actually reads (including /data/areos.db on Render).
        db_path = get_db_path()

    # Ensure schema (including the is_client_evidence column and kb_meta
    # table) exists before we touch claims/check_code_mappings.
    migrate(db_path)
    conn = get_connection(db_path)

    summary: dict[str, Any] = {
        "claims_seen": 0,
        "claims_inserted": 0,
        "claims_already_present": 0,
        "claims_rejected": [],  # list of (claim_id, [lint errors])
        "mappings_inserted": 0,
        "mappings_already_present": 0,
        "mappings_skipped_missing_claim": [],  # list of (check_code, claim_id)
    }

    rows = _load_source_rows()
    summary["claims_seen"] = len(rows)
    _alias_file = _ROOT / "stage_id_aliases.yaml"

    for raw in rows:
        row = _build_row(raw)
        # FIX (Readiness Audit, Major #2): active_claims.json mixes two
        # stage-id schemes (STAGE-XX, the majority, and a minority of AP-XX
        # records), and lint.py's STAGE_ID_PATTERN accepted both, so both
        # ended up inserted as-is into claims.stage_id — the actual, correct
        # single source of truth for this normalization already exists
        # (stage_id_aliases.yaml + db/stage_normalization.py, per
        # AREOS_KNOWLEDGE_INGESTION_SPEC.md §2.7) but was never called from
        # here. Normalize every non-null stage_id to its canonical STAGE-XX
        # before linting/inserting, instead of allowing both schemes into
        # the same column.
        raw_stage = row.get("stage_id")
        if raw_stage:
            normalized, norm_error = normalize_stage_id(str(raw_stage), _alias_file)
            if norm_error:
                summary["claims_rejected"].append((raw.get("claim_id"), [norm_error]))
                continue
            row["stage_id"] = normalized
        errors = lint_claim(row)
        cid = row.get("claim_id")
        if errors:
            summary["claims_rejected"].append((cid, errors))
            continue

        existing = conn.execute(
            "SELECT 1 FROM claims WHERE claim_id = ?", (cid,)
        ).fetchone()
        if existing:
            summary["claims_already_present"] += 1
            continue

        conn.execute(
            """
            INSERT INTO claims (
                claim_id, stage_id, claim_scope, claim_type, statement,
                status, confidence, source_url, source_tier_vocab,
                source_tier_value, source_date, last_verified, superseded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["claim_id"], row["stage_id"], row["claim_scope"],
                row["claim_type"], row["statement"], row["status"],
                row["confidence"], row["source_url"], row["source_tier_vocab"],
                row["source_tier_value"], row["source_date"],
                row["last_verified"], row["superseded_by"],
            ),
        )
        summary["claims_inserted"] += 1

    conn.commit()

    # Now wire check_code_mappings, skipping any target claim_id that isn't
    # actually present (FK would otherwise reject the whole insert).
    for check_code, claim_ids in _CHECK_CODE_MAPPINGS.items():
        for claim_id in claim_ids:
            has_claim = conn.execute(
                "SELECT 1 FROM claims WHERE claim_id = ?", (claim_id,)
            ).fetchone()
            if not has_claim:
                summary["mappings_skipped_missing_claim"].append((check_code, claim_id))
                continue

            existing = conn.execute(
                "SELECT 1 FROM check_code_mappings WHERE check_code = ? AND claim_id = ?",
                (check_code, claim_id),
            ).fetchone()
            if existing:
                summary["mappings_already_present"] += 1
                continue

            conn.execute(
                "INSERT INTO check_code_mappings (check_code, claim_id) VALUES (?, ?)",
                (check_code, claim_id),
            )
            summary["mappings_inserted"] += 1

    conn.commit()

    # FIX (Readiness Audit, Major #6): increment_kb_version() was fully
    # implemented per AREOS_ONTOLOGY_EVOLUTION_SPEC.md §3.6 but never called
    # anywhere — wire it in here, the one place claims actually get added to
    # the KB in bulk. Only bump the version if this run actually changed
    # anything, so idempotent re-runs against an already-seeded DB don't
    # inflate the version number for a no-op.
    if summary["claims_inserted"] > 0:
        with write_as(conn, actor="ingest_claims", reason="Bulk KB seed from active_claims.json"):  # noqa: E501
            new_version = increment_kb_version(conn, actor="ingest_claims")
        summary["kb_version"] = new_version

    if verbose:
        _print_summary(summary)

    return summary


def _print_summary(summary: dict[str, Any]) -> None:
    print("=== AREOS knowledge-base ingestion ===")
    print(f"claims.json records seen:        {summary['claims_seen']}")
    print(f"claims inserted:                 {summary['claims_inserted']}")
    print(f"claims already present (skip):   {summary['claims_already_present']}")
    print(f"claims rejected by lint:         {len(summary['claims_rejected'])}")
    for cid, errors in summary["claims_rejected"]:
        print(f"  - {cid}: {'; '.join(errors)}")
    print(f"mappings inserted:               {summary['mappings_inserted']}")
    print(f"mappings already present (skip): {summary['mappings_already_present']}")
    skipped = summary["mappings_skipped_missing_claim"]
    print(f"mappings skipped (no such claim): {len(skipped)}")
    for check_code, claim_id in skipped:
        print(f"  - {check_code} -> {claim_id} (claim not in corpus)")
    print("=======================================")


if __name__ == "__main__":
    ingest()
