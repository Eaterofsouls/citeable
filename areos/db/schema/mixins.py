# areos/db/schema/mixins.py
#
# Declarative base-type mixins, adopted from step2_architecture_v2_2.md's four
# base types (Versionable, PipelineAware, EvidenceBacked, SessionScoped).
#
# Each mixin is a list of (column_name, sqlite_type, constraint_suffix) tuples.
# These are expanded verbatim by generate_schema.py into every table that declares
# the mixin. Edit here once; every consuming table regenerates identically.
#
# Rationale (ADR D2/D7): adopting the four base types at the generator level costs
# nothing extra to define once and solves the copy-paste-drift failure mode
# Bible §4.4 already observed once in this project. The full 30-artifact ontology
# from step2_architecture_v2_2.md is NOT built here — only the column-set primitives.

VERSIONABLE = [
    ("valid_from",        "TEXT", "NOT NULL DEFAULT (date('now'))"),
    ("valid_until",       "TEXT", ""),
    ("last_reviewed",     "TEXT", ""),
    ("review_frequency",  "TEXT",
     "CHECK (review_frequency IN ('MONTHLY','QUARTERLY','SEMI_ANNUAL','ANNUAL','ON_RELEASE'))"),
    ("deprecated",        "INTEGER", "NOT NULL DEFAULT 0 CHECK (deprecated IN (0,1))"),
    ("deprecated_reason", "TEXT", ""),
    ("superseded_by",     "TEXT", ""),  # FK added per-table at generation time if self-referential
]

PIPELINE_AWARE = [
    ("primary_stage",    "TEXT", "NOT NULL REFERENCES pipeline_stage(stage_id)"),
    ("also_relevant_to", "TEXT", "DEFAULT '[]'"),  # JSON array of stage_id, queried via json_each()
]

EVIDENCE_BACKED = [
    ("evidence_tier",       "TEXT",
     "NOT NULL CHECK (evidence_tier IN ('T1','T2','T3','T4','T5'))"),
    ("evidence_origin",     "TEXT",
     "NOT NULL CHECK (evidence_origin IN ('OBSERVED','DECLARED','INFERRED','DERIVED'))"),
    # points at claims.claim_id when the evidence is a tracked claim
    ("evidence_source_ref", "TEXT", "NOT NULL"),
]

SESSION_SCOPED = [
    ("session_id",   "TEXT", "NOT NULL REFERENCES audit_session(session_id)"),
    ("run_id",       "TEXT", "NOT NULL REFERENCES audit_run(run_id)"),
    ("collected_at", "TEXT", "NOT NULL DEFAULT (datetime('now'))"),
]

MIXINS = {
    "VERSIONABLE":   VERSIONABLE,
    "PIPELINE_AWARE": PIPELINE_AWARE,
    "EVIDENCE_BACKED": EVIDENCE_BACKED,
    "SESSION_SCOPED":  SESSION_SCOPED,
}
