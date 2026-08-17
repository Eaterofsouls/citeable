# areos/db/migrate_audit_tables.py
#
# Applies the consolidated schema (SEC-11) against the target database.
# This is an idempotent-apply strategy using CREATE TABLE IF NOT EXISTS —
# see docs/architecture/migrations.md for the documented limitations.
#
# Source of truth for DDL: areos/db/schema/mixins.py + areos/db/schema/artifacts.py
# Generated SQL file:      areos/db/schema.sql (kept in sync with the root schema.sql)
#
# FIX (Readiness Audit, Blocker 1): this file previously read a second,
# drifted copy of the schema (produced by the now-deprecated generate_ddl.py)
# that was missing the _txn_context/changelog tables and triggers write_as()
# depends on. There must be exactly one generator. To regenerate schema.sql
# after changing mixins.py or artifacts.py:
#   python generate_schema.py            # writes the canonical root schema.sql
#   cp schema.sql areos/db/schema.sql    # keep this copy in sync

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from areos.db.connection import get_connection, get_db_path  # noqa: E402

_SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"


def migrate(db_path: Path | str | None = None) -> None:
    """
    Apply the generated schema.sql against the target DB.
    Raises on failure — callers must NOT swallow this (MF-9).
    """
    if db_path is None:
        # FIX (data-quality pass, follow-up sweep): this used to default to
        # a hardcoded `_ROOT / "areos.db"`, ignoring AREOS_TEST_DB entirely
        # — unlike every other DB entry point in the codebase, which goes
        # through get_db_path(). Confirmed live (not just latent): pytest's
        # `tests/test_audit_orchestrator.py` and `tests/test_prompts_api.py`
        # both call `migrate()` with no args from an autouse fixture, so on
        # any checkout where the real root areos.db hasn't already had the
        # full schema applied, a routine `pytest` run would silently write
        # schema changes into the real seed DB instead of the isolated test
        # DB conftest.py sets up. Delegate to the single canonical resolver.
        db_path = Path(get_db_path())

    if not _SCHEMA_SQL.exists():
        raise FileNotFoundError(
            f"schema.sql not found at {_SCHEMA_SQL}. "
            "Run: python -m areos.db.schema.generate_ddl"
        )

    conn = get_connection(db_path)
    sql = _SCHEMA_SQL.read_text(encoding="utf-8")
    conn.executescript(sql)

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
    conn.execute("INSERT OR IGNORE INTO kb_meta (id) VALUES (1)")

    # areos/auditors/findings_to_claims.py's _lookup_claim() selects
    # is_client_evidence from claims, but no schema generator defines that
    # column — harmless today only because check_code_mappings is empty, so
    # that query path never actually runs. The moment both tables are
    # seeded, this will hard-crash wire_finding() with "no such column".
    # Computed purely from claim_scope (already on every row), not
    # fabricated data — safe to add unconditionally.
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

    # 0008: synthesis_prompts table (Phase 2 LLM pipeline)
    try:
        import importlib, sys as _sys
        _spec = importlib.util.spec_from_file_location(
            "migration_0008",
            Path(__file__).resolve().parents[2] / "migrations" / "0008_add_synthesis_prompts.py"
        )
        _m = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_m)
        _m.migrate(db_path=str(db_path))
    except FileNotFoundError:
        pass  # migration file not present yet
    except Exception as exc:  # noqa: BLE001
        print(f"[Warning] Migration 0008 failed (non-fatal): {exc}")


if __name__ == "__main__":
    migrate()
