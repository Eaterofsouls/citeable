# areos/db/schema/artifacts.py
#
# Declarative table specifications.
#
# `changelog: True`      -> generate_schema.py auto-emits AFTER INSERT/UPDATE triggers.
# `soft_delete_only: True` -> generate_schema.py auto-emits a BEFORE DELETE RAISE(ABORT) trigger.
#
# Source-tier stored as two columns (source_tier_vocab + source_tier_value) never
# as one collapsed enum — Bible §6.4 / ADR D5.
#
# The `findings` table adopts step2_architecture_v2_2.md's Diagnostic State enum
# in miniature (ADR D14). Nothing else from that document's 30-artifact ontology
# is generated at v1 — see §0 of the Technical Manifesto for rationale.

TABLES = {

    # -------------------------------------------------------------------------
    # Core Evidence Layer (Bible §6.2 / ADR D1)
    # -------------------------------------------------------------------------

    "claims": {
        "columns": [
            ("claim_id",          "TEXT", "PRIMARY KEY"),
            ("stage_id",          "TEXT", "REFERENCES audit_phase(audit_phase_id)"),
            ("claim_scope",       "TEXT",
             "CHECK (claim_scope IN ('retrieval-pipeline','audit-workflow','general-knowledge'))"),
            ("claim_type",        "TEXT", ""),
            ("statement",         "TEXT", "NOT NULL"),
            ("status",            "TEXT",
             "NOT NULL DEFAULT 'active' CHECK (status IN "
             "('active','deprecated','contested','superseded'))"),
            ("confidence",        "TEXT", ""),
            ("source_url",        "TEXT", ""),
            # ADR D5: two-column source-tier, never one collapsed enum
            ("source_tier_vocab", "TEXT",
             "NOT NULL CHECK (source_tier_vocab IN ('study_a','study_b','system_native'))"),
            ("source_tier_value", "TEXT", "NOT NULL"),
            ("source_date",       "TEXT", ""),
            ("last_verified",     "TEXT", ""),
            ("superseded_by",     "TEXT", "REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE"),
            ("is_client_evidence", "BOOLEAN", "GENERATED ALWAYS AS (claim_scope IS NULL OR claim_scope != 'general-knowledge') VIRTUAL"),
        ],
        "mixins":          [],
        "changelog":       True,
        "soft_delete_only": True,
    },

    "audit_phase": {
        "columns": [
            ("audit_phase_id",            "TEXT",    "PRIMARY KEY"),
            ("name",                      "TEXT",    "NOT NULL"),
            ("description",               "TEXT",    ""),
            ("automatable",               "INTEGER", "NOT NULL DEFAULT 1 CHECK (automatable IN (0,1))"),  # noqa: E501
            ("human_judgment_required",   "INTEGER", "NOT NULL DEFAULT 0 CHECK (human_judgment_required IN (0,1))"),  # noqa: E501
            ("phase_order",               "INTEGER", ""),
        ],
        "mixins":          [],
        # Reference/seed table — not a claim-lifecycle table, so no changelog needed.
        "changelog":       False,
        "soft_delete_only": False,
    },

    "tool_landscape": {
        "columns": [
            ("tool_id",    "TEXT", "PRIMARY KEY"),
            ("claim_id",   "TEXT", "NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE"),
            ("statement",  "TEXT", "NOT NULL"),
            ("status",     "TEXT",
             "NOT NULL DEFAULT 'active' CHECK (status IN "
             "('active','deprecated','contested','superseded'))"),
            ("confidence", "TEXT", ""),
        ],
        "mixins":          [],
        "changelog":       True,
        "soft_delete_only": True,
    },

    "policy_constraints": {
        "columns": [
            ("policy_id",  "TEXT", "PRIMARY KEY"),
            ("claim_id",   "TEXT", "NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE"),
            ("statement",  "TEXT", "NOT NULL"),
            ("status",     "TEXT",
             "NOT NULL DEFAULT 'active' CHECK (status IN "
             "('active','deprecated','contested','superseded'))"),
            ("confidence", "TEXT", ""),
        ],
        "mixins":          [],
        "changelog":       True,
        "soft_delete_only": True,
    },

    # -------------------------------------------------------------------------
    # Findings — minimal Diagnostic State (ADR D14)
    # Built at Task 3f. The full Issue/Inference table machinery from
    # step2_architecture_v2_2.md is NOT built at v1.
    # -------------------------------------------------------------------------

    "findings": {
        "columns": [
            ("finding_id",     "TEXT", "PRIMARY KEY"),
            ("check_type",     "TEXT",
             "NOT NULL CHECK (check_type IN "
             "('schema_ld','robots_llms','extractability','citation_sampler','content_format','authority'))"),
            ("site_id",        "TEXT", "NOT NULL"),
            ("run_id",         "TEXT", "NOT NULL"),
            ("claim_id",       "TEXT", "NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE"),
            # Diagnostic State enum from step2_architecture_v2_2.md, adopted in miniature
            ("evidence_state", "TEXT",
             "NOT NULL CHECK (evidence_state IN "
             "('CONFIRMED','STRONGLY_SUPPORTED','POSSIBLE','INSUFFICIENT','ESCALATE'))"),
            ("raw_output",     "TEXT", "NOT NULL"),   # JSON — the check's literal output
            ("observed_at",    "TEXT", "NOT NULL DEFAULT (datetime('now'))"),
        ],
        "mixins":          [],
        "changelog":       True,
        "soft_delete_only": True,
    },

    # -------------------------------------------------------------------------
    # Job Queue (§1.10 / ADR D11)
    # No Celery/Redis at this scale. One poller process, one table.
    # Forward-compatible with the public-launch queue requirement.
    # -------------------------------------------------------------------------

    "jobs": {
        "columns": [
            ("job_id",      "TEXT", "PRIMARY KEY"),
            ("task_name",   "TEXT", "NOT NULL"),
            ("status",      "TEXT",
             "NOT NULL DEFAULT 'queued' CHECK "
             "(status IN ('queued','running','done','failed'))"),
            ("payload",     "TEXT", "NOT NULL"),   # JSON
            ("result",      "TEXT", ""),           # JSON
            ("created_at",  "TEXT", "NOT NULL DEFAULT (datetime('now'))"),
            ("started_at",  "TEXT", ""),
            ("finished_at", "TEXT", ""),
        ],
        "mixins":          [],
        # Job rows are operational records, not evidence records.
        # Hard-deletes of old job rows are acceptable after archiving.
        "changelog":       False,
        "soft_delete_only": False,
    },

    # -------------------------------------------------------------------------
    # Source Registry (Citation Transparency feature)
    # Every external source used to back a claim gets a structured row here.
    # Trust tiers (T1–T7) are deterministic from source TYPE, not editorial opinion:
    #   T1 = Official platform docs (OpenAI, Google, Perplexity — primary)
    #   T2 = Primary research / peer-reviewed (named authors, methodology, sample sizes)
    #   T3 = Legal primary sources (court filings, actual ToS text)
    #   T4 = Reputable named practitioners (verified SEO/GEO analysts)
    #   T5 = Industry media (Search Engine Land, Ars Technica)
    #   T6 = Vendor research (BrightEdge, SE Ranking — useful, vendor-motivated)
    #   T7 = Community / social signals (Reddit, Twitter — signals only, never claim backbone)
    # -------------------------------------------------------------------------

    "sources": {
        "columns": [
            ("source_id",      "TEXT", "PRIMARY KEY"),
            ("name",           "TEXT", "NOT NULL"),
            ("domain",         "TEXT", "NOT NULL"),
            ("url",            "TEXT", ""),
            ("trust_tier",     "TEXT",
             "NOT NULL CHECK (trust_tier IN ('T1','T2','T3','T4','T5','T6','T7'))"),
            ("source_type",    "TEXT",
             "NOT NULL CHECK (source_type IN ("
             "'official-platform-doc','primary-research','legal-primary',"
             "'named-practitioner','industry-media','vendor-research','community'))"),
            ("verified",       "INTEGER", "NOT NULL DEFAULT 0 CHECK (verified IN (0,1))"),
            ("verified_date",  "TEXT", ""),    # ISO date when last confirmed live
            ("notes",          "TEXT", ""),    # Why this source is trusted (shown in UI tooltip)
            ("approved_count", "INTEGER", "NOT NULL DEFAULT 0"),
            ("rejected_count", "INTEGER", "NOT NULL DEFAULT 0"),
            ("created_at",     "TEXT", "NOT NULL DEFAULT (datetime('now'))"),
        ],
        "mixins":          [],
        "changelog":       False,   # seed/reference table
        "soft_delete_only": False,
    },

    # -------------------------------------------------------------------------
    # Claim-Sources join table — many-to-many link between claims and sources.
    # A claim may be backed by multiple sources; a source may back many claims.
    # The `primary_source` flag marks which source is the strongest single backing
    # (used to pick which badge to show in the compact citation chip in the UI).
    # -------------------------------------------------------------------------

    "claim_sources": {
        "columns": [
            ("claim_source_id", "TEXT", "PRIMARY KEY"),
            ("claim_id",        "TEXT", "NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE"),
            ("source_id",       "TEXT", "NOT NULL REFERENCES sources(source_id)"),
            ("primary_source",  "INTEGER", "NOT NULL DEFAULT 0 CHECK (primary_source IN (0,1))"),
            ("note",            "TEXT", ""),    # e.g. "Claude fetched this page directly, 2026-05-08"  # noqa: E501
            ("linked_at",       "TEXT", "NOT NULL DEFAULT (datetime('now'))"),
        ],
        "mixins":          [],
        "changelog":       False,
        "soft_delete_only": False,
    },

    # -------------------------------------------------------------------------
    # Check Code to Claim Mappings (Task 3f / Phase D)
    # Stores the relationship between auditor check_codes and the claim_ids they inform.
    # -------------------------------------------------------------------------

    "check_code_mappings": {
        "columns": [
            ("mapping_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
            ("check_code", "TEXT",    "NOT NULL"),
            ("claim_id",   "TEXT",    "NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE"),
        ],
        "mixins":          [],
        "changelog":       False,
        "soft_delete_only": False,
    },

    # -------------------------------------------------------------------------
    # Prompt Sets (AP-05 Citation Tracking / Gap 2)
    # Stores governed prompt queries for AI citation sampling.
    # -------------------------------------------------------------------------

    "prompt_sets": {
        "columns": [
            ("prompt_id",     "TEXT", "PRIMARY KEY"),
            ("label",         "TEXT", "NOT NULL"),
            ("prompt_text",   "TEXT", "NOT NULL"),
            ("target_domain", "TEXT", ""),
            ("funnel_stage",  "TEXT", ""),
            ("active",        "INTEGER", "NOT NULL DEFAULT 1 CHECK (active IN (0,1))"),
            ("created_at",    "TEXT", "NOT NULL DEFAULT (datetime('now'))"),
        ],
        "mixins":          [],
        "changelog":       True,
        "soft_delete_only": False,
    },

    # -------------------------------------------------------------------------
    # Audit Runs & Verdicts (v6 auditor subsystem) - SEC-11 consolidation
    # -------------------------------------------------------------------------

    "audit_runs": {
        "columns": [
            ("run_id",              "TEXT",    "PRIMARY KEY"),
            ("target_domain",       "TEXT",    "NOT NULL"),
            ("run_date",            "TEXT",    "NOT NULL"),
            ("audited_stages",      "TEXT",    "NOT NULL"),           # JSON
            ("automated_findings",  "TEXT",    "NOT NULL"),           # JSON
            ("status",              "TEXT",    "DEFAULT 'automated_complete'"),
            # SEC-24: persist computed score so B6 can use a real delta instead of Math.random()
            ("overall_score",       "INTEGER", ""),
            ("run_token",           "TEXT",    ""),
            ("created_at",          "TEXT",    "DEFAULT (datetime('now'))"),
            ("approved_count",      "INTEGER", "DEFAULT 0"),
            ("rejected_count",      "INTEGER", "DEFAULT 0"),
        ],
        "mixins":          [],
        "changelog":       False,
        "soft_delete_only": False,
        # SEC-21 indexes
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_audit_runs_domain ON audit_runs (target_domain);",
        ],
    },

    "manual_verdicts": {
        "columns": [
            ("id",           "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
            ("run_id",       "TEXT",    "NOT NULL"),
            ("card_id",      "TEXT",    "NOT NULL"),
            ("page_url",     "TEXT",    "DEFAULT ''"),
            ("verdict",      "TEXT",    "NOT NULL"),
            ("severity",     "TEXT",    "NOT NULL"),
            ("notes",        "TEXT",    "DEFAULT ''"),
            ("submitted_at", "TEXT",    "DEFAULT (datetime('now'))"),
        ],
        "mixins":          [],
        "changelog":       False,
        "soft_delete_only": False,
        # SEC-21: explicit index for FK-style queries
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_manual_verdicts_run ON manual_verdicts (run_id);",
        ],
    },

    # UX audit \u00a75.3: previously the three-step LLM synthesis result
    # (narrative, red-team flags, draft) only ever existed in the HTTP
    # response of POST /synthesize \u2014 nothing persisted it, so a page
    # reload silently lost the "final report" the whole hybrid flow builds
    # toward. This table gives the unified report endpoint (GET
    # /audit/runs/{run_id}/full) something durable to read back.
    "audit_synthesis": {
        "columns": [
            ("run_id",            "TEXT",    "PRIMARY KEY"),
            ("narrative",         "TEXT",    "DEFAULT ''"),
            ("draft",             "TEXT",    "DEFAULT ''"),
            ("flags_json",        "TEXT",    "DEFAULT '[]'"),           # JSON
            ("flags_resolved",    "INTEGER", "DEFAULT 0"),
            ("provider_log_json", "TEXT",    "DEFAULT '[]'"),           # JSON
            ("manual_verdicts_merged", "INTEGER", "DEFAULT 0"),
            ("created_at",        "TEXT",    "DEFAULT (datetime('now'))"),
        ],
        "mixins":          [],
        "changelog":       False,
        "soft_delete_only": False,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_audit_synthesis_run ON audit_synthesis (run_id);",
        ],
    },

    # -------------------------------------------------------------------------
    # Idempotency Keys (MF-6 / A3) - SEC-11 consolidation
    # -------------------------------------------------------------------------

    "idempotency_keys": {
        "columns": [
            ("idempotency_key", "TEXT",     "PRIMARY KEY"),
            ("endpoint",        "TEXT",     "NOT NULL"),
            ("response_status", "INTEGER",  ""),
            ("response_body",   "TEXT",     ""),
            ("created_at",      "DATETIME", "DEFAULT CURRENT_TIMESTAMP"),
        ],
        "mixins":          [],
        "changelog":       False,
        "soft_delete_only": False,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_idempotency_created ON idempotency_keys (created_at);",
        ],
    },
}

# SEC-21: Additional indexes not tied to a single table's DSL
STANDALONE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_prompt_sets_domain ON prompt_sets (target_domain);",
]
