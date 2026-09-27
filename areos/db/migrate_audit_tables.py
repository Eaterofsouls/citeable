# areos/db/migrate_audit_tables.py
#
# Applies the consolidated operational schema against the target database.
# This file is hand-maintained; see tests/test_schema_matches_live_db.py
# for the parity check that keeps it honest.

import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from areos.db.connection import get_connection, get_db_path  # noqa: E402

_SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"


def _split_sql_statements(sql: str) -> list[str]:
    """Split a SQL script into individual complete statements using sqlite3.complete_statement."""
    statements = []
    current_statement = ""
    for line in sql.splitlines(keepends=True):
        current_statement += line
        if sqlite3.complete_statement(current_statement):
            stmt = current_statement.strip()
            if stmt:
                statements.append(stmt)
            current_statement = ""
    remainder = current_statement.strip()
    if remainder:
        statements.append(remainder)
    return statements


def migrate(db_path: Path | str | None = None) -> None:
    """
    Apply schema.sql against the target DB.
    Raises on failure — callers must NOT swallow this (MF-9).
    """
    if db_path is None:
        db_path = Path(get_db_path())

    if not _SCHEMA_SQL.exists():
        raise FileNotFoundError(
            f"schema.sql not found at {_SCHEMA_SQL}."
        )

    conn = get_connection(db_path)
    sql = _SCHEMA_SQL.read_text(encoding="utf-8")

    statements = _split_sql_statements(sql)
    for stmt in statements:
        conn.execute(stmt)
    conn.commit()

    # Ensure approved_count / rejected_count columns exist on sources
    # (backward-compat for DBs created before the sources schema update)
    for col in ("approved_count", "rejected_count"):
        try:
            conn.execute(f"SELECT {col} FROM sources LIMIT 1")
        except Exception:
            conn.execute(
                f"ALTER TABLE sources ADD COLUMN {col} INTEGER DEFAULT 0"
            )

    # SEC-24: ensure overall_score column exists on audit_runs
    # (backward-compat for DBs created before Batch A4)
    try:
        conn.execute("SELECT overall_score FROM audit_runs LIMIT 1")
    except Exception:
        conn.execute(
            "ALTER TABLE audit_runs ADD COLUMN overall_score INTEGER"
        )

    # Task 5: ensure run_token column exists on audit_runs
    try:
        conn.execute("SELECT run_token FROM audit_runs LIMIT 1")
    except Exception:
        conn.execute(
            "ALTER TABLE audit_runs ADD COLUMN run_token TEXT"
        )

    # Ensure kb_meta exists (areos/db/kb_version.py depends on it but no
    # schema generator currently defines it — this is dead code today, but
    # will hard-crash the moment anything calls increment_kb_version()).
    conn.execute(
        "CREATE TABLE IF NOT EXISTS kb_meta ("
        "  id INTEGER PRIMARY KEY CHECK (id = 1),"
        "  kb_version TEXT NOT NULL DEFAULT '2026.01.01.0',"
        "  last_updated TEXT,"
        "  total_claims INTEGER NOT NULL DEFAULT 0,"
        "  updated_by TEXT"
        ")"
    )
    try:
        conn.execute("INSERT OR IGNORE INTO kb_meta (id) VALUES (1)")
    except Exception:
        pass

    # areos/auditors/findings_to_claims.py's _lookup_claim() selects
    # is_client_evidence from claims, but no schema generator defines that
    # column — harmless today only because check_code_mappings is empty, so
    # that query path never actually runs. The moment both tables are
    # seeded, this will hard-crash wire_finding() with "no such column".
    # Computed purely from claim_scope (already on every row), not
    # fabricated data — safe to add unconditionally.
    # QA-C04: Guard against V2 KB where build_kb.py converts claims to a VIEW.
    # ALTER TABLE on a VIEW raises "Cannot add a column to a view".
    claims_type_row = conn.execute(
        "SELECT type FROM sqlite_master WHERE name='claims'"
    ).fetchone()
    if claims_type_row and claims_type_row[0] == 'table':
        try:
            conn.execute("SELECT is_client_evidence FROM claims LIMIT 1")
        except Exception:
            conn.execute(
                "ALTER TABLE claims ADD COLUMN is_client_evidence BOOLEAN "
                "GENERATED ALWAYS AS (claim_scope IS NULL OR claim_scope != 'general-knowledge') VIRTUAL"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_claims_client_evidence ON claims(is_client_evidence)"
            )

    # FIX (Readiness Audit, Blocker 2): claims.stage_id REFERENCES
    # audit_phase(audit_phase_id) with FK enforcement on (db/connection.py),
    # but no schema generator, migration, or seed script ever populated
    # audit_phase — every insert of a claim/outcome with a non-null stage_id
    # hard-crashed with sqlite3.IntegrityError. Seed every stage_id value
    # that actually appears in active_claims.json (both the STAGE-XX scheme
    # used by the majority of records and outcome_logger.py's
    # _REMEDIATION_TO_STAGE map, and the minority AP-XX scheme used by a
    # handful of records and audit_orchestrator.py's audited_stages
    # metadata), plus STAGE-99, the documented fallback for unmapped
    # remediation codes in outcome_logger._derive_stage_id().
    _AUDIT_PHASE_SEED = (
        [(f"STAGE-{n:02d}", f"Audit Stage {n:02d}", n) for n in range(1, 23)]
        + [("STAGE-99", "Unmapped / Fallback Stage", 99)]
        + [
            ("AP-01", "Audit Phase 01 — AI Crawling & Robots", 101),
            ("AP-02", "Audit Phase 02 — Schema & JSON-LD Structure", 102),
            ("AP-03", "Audit Phase 03 — Content Extractability", 103),
            ("AP-04", "Audit Phase 04 — Authority & Backlinks", 104),
            ("AP-05", "Audit Phase 05 — Live AI Citation Sampling", 105),
            ("AP-06", "Audit Phase 06 — Remediation Synthesis", 106),
            ("AP-07", "Audit Phase 07 — Manual Review / QA", 107),
            ("AP-08", "Audit Phase 08 — LLM Synthesis Pipeline", 108),
            ("AP-09", "Audit Phase 09 — Outcome Logging", 109),
            ("AP-10", "Audit Phase 10 — Historical Delta & Reporting", 110),
        ]
    )
    conn.executemany(
        "INSERT OR IGNORE INTO audit_phase (audit_phase_id, name, phase_order) VALUES (?, ?, ?)",  # noqa: E501
        _AUDIT_PHASE_SEED,
    )

    conn.commit()
    print("Migration complete (SEC-11 consolidated schema applied).")

    # 0008: synthesis_prompts table & defaults (Phase 2 LLM pipeline)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS synthesis_prompts ("
        "  step TEXT PRIMARY KEY,"
        "  system_prompt TEXT NOT NULL,"
        "  updated_at TEXT,"
        "  updated_by TEXT"
        ")"
    )
    try:
        from areos.llm.synthesis_pipeline import (
            _DEFAULT_SYNTHESIZER_PROMPT,
            _DEFAULT_RED_TEAMER_PROMPT,
            _DEFAULT_GROUNDER_PROMPT,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO synthesis_prompts (step, system_prompt, updated_at, updated_by) "
            "VALUES (?, ?, datetime('now'), 'system')",
            [
                ("synthesizer", _DEFAULT_SYNTHESIZER_PROMPT),
                ("red_teamer", _DEFAULT_RED_TEAMER_PROMPT),
                ("grounder", _DEFAULT_GROUNDER_PROMPT),
            ],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[Warning] Seeding synthesis_prompts defaults failed (non-fatal): {exc}")
    conn.commit()


if __name__ == "__main__":
    migrate()
