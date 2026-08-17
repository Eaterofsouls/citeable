-- ==========================================================================
-- schema.sql  —  GENERATED FILE. DO NOT EDIT BY HAND.
-- ==========================================================================
-- Source:  areos/db/schema/mixins.py  +  areos/db/schema/artifacts.py
-- Tool:    generate_schema.py
-- Rationale: Bible §4.4/§17.1 (copy-paste drift) / ADR D2.
--
-- To update the schema:
--   1. Edit mixins.py or artifacts.py.
--   2. Run:  python generate_schema.py
--   3. Commit the resulting schema.sql alongside the source change.
-- ==========================================================================

-- These PRAGMAs are set per-connection in areos/db/connection.py.
-- They are documented here for reference but schema.sql does NOT execute them
-- (PRAGMAs are connection-level settings, not schema objects).
--
-- PRAGMA foreign_keys = ON;     -- Bible Law 6.5 — not optional
-- PRAGMA journal_mode = WAL;    -- readers don't block on a writer (ADR D1)
-- PRAGMA synchronous = NORMAL;  -- safe under WAL at this scale
-- PRAGMA busy_timeout = 30000;  -- wait, don't throw, on lock contention

-- _txn_context: one-row staging table.
-- Every write path calls: UPDATE _txn_context SET actor = ?, reason = ? WHERE id = 1
-- inside the same transaction, BEFORE performing the real write.
-- Triggers read actor/reason from here — this is how semantic context reaches the
-- database engine without the trigger needing to know anything about the application.
-- See areos/db/context.py for the write_as() context manager that owns this pattern.
CREATE TABLE IF NOT EXISTS _txn_context (
    id     INTEGER PRIMARY KEY CHECK (id = 1),
    actor  TEXT,
    reason TEXT
);
INSERT OR IGNORE INTO _txn_context (id, actor, reason) VALUES (1, NULL, NULL);

-- changelog: polymorphic audit log shared by every changelog: True table.
-- Populated exclusively by AFTER INSERT/UPDATE triggers — never by application code.
-- Bible §6.3 / ADR D3.
CREATE TABLE IF NOT EXISTS changelog (
    changelog_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_table  TEXT NOT NULL,
    entity_id     TEXT NOT NULL,
    operation     TEXT NOT NULL CHECK (operation IN ('INSERT','UPDATE')),
    actor         TEXT,
    reason        TEXT,
    before_json   TEXT,
    after_json    TEXT,
    changed_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_changelog_entity ON changelog (entity_table, entity_id);
-- ========================================================================
-- Table: claims
-- ========================================================================
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    stage_id TEXT REFERENCES audit_phase(audit_phase_id),
    claim_scope TEXT CHECK (claim_scope IN ('retrieval-pipeline','audit-workflow','general-knowledge')),
    claim_type TEXT,
    statement TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deprecated','contested','superseded')),
    confidence TEXT,
    source_url TEXT,
    source_tier_vocab TEXT NOT NULL CHECK (source_tier_vocab IN ('study_a','study_b','system_native')),
    source_tier_value TEXT NOT NULL,
    source_date TEXT,
    last_verified TEXT,
    superseded_by TEXT REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE,
    is_client_evidence BOOLEAN GENERATED ALWAYS AS (claim_scope IS NULL OR claim_scope != 'general-knowledge') VIRTUAL
);

CREATE INDEX IF NOT EXISTS idx_claims_stage_type   ON claims (stage_id, claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_status       ON claims (status);
CREATE INDEX IF NOT EXISTS idx_claims_source_tier  ON claims (source_tier_vocab, source_tier_value);
CREATE INDEX IF NOT EXISTS idx_claims_client_evidence ON claims (is_client_evidence);

CREATE TRIGGER IF NOT EXISTS trg_claims_after_update
AFTER UPDATE ON claims
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'claims', OLD.claim_id, 'UPDATE',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        json_object('claim_scope', OLD.claim_scope, 'claim_type', OLD.claim_type, 'statement', OLD.statement, 'status', OLD.status, 'confidence', OLD.confidence, 'source_url', OLD.source_url, 'source_tier_vocab', OLD.source_tier_vocab, 'source_tier_value', OLD.source_tier_value, 'source_date', OLD.source_date, 'last_verified', OLD.last_verified, 'superseded_by', OLD.superseded_by),
        json_object('claim_scope', NEW.claim_scope, 'claim_type', NEW.claim_type, 'statement', NEW.statement, 'status', NEW.status, 'confidence', NEW.confidence, 'source_url', NEW.source_url, 'source_tier_vocab', NEW.source_tier_vocab, 'source_tier_value', NEW.source_tier_value, 'source_date', NEW.source_date, 'last_verified', NEW.last_verified, 'superseded_by', NEW.superseded_by),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_claims_after_insert
AFTER INSERT ON claims
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'claims', NEW.claim_id, 'INSERT',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        NULL,
        json_object('claim_scope', NEW.claim_scope, 'claim_type', NEW.claim_type, 'statement', NEW.statement, 'status', NEW.status, 'confidence', NEW.confidence, 'source_url', NEW.source_url, 'source_tier_vocab', NEW.source_tier_vocab, 'source_tier_value', NEW.source_tier_value, 'source_date', NEW.source_date, 'last_verified', NEW.last_verified, 'superseded_by', NEW.superseded_by),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_claims_block_hard_delete
BEFORE DELETE ON claims
BEGIN
    SELECT RAISE(ABORT, 'Hard delete forbidden on claims (Bible 6.3 / INVARIANT-08). Transition status to deprecated or superseded instead.');
END;

-- ========================================================================
-- Table: audit_phase
-- ========================================================================
CREATE TABLE IF NOT EXISTS audit_phase (
    audit_phase_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    automatable INTEGER NOT NULL DEFAULT 1 CHECK (automatable IN (0,1)),
    human_judgment_required INTEGER NOT NULL DEFAULT 0 CHECK (human_judgment_required IN (0,1)),
    phase_order INTEGER
);

-- ========================================================================
-- Table: tool_landscape
-- ========================================================================
CREATE TABLE IF NOT EXISTS tool_landscape (
    tool_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE,
    statement TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deprecated','contested','superseded')),
    confidence TEXT
);

CREATE TRIGGER IF NOT EXISTS trg_tool_landscape_after_update
AFTER UPDATE ON tool_landscape
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'tool_landscape', OLD.tool_id, 'UPDATE',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        json_object('statement', OLD.statement, 'status', OLD.status, 'confidence', OLD.confidence),
        json_object('statement', NEW.statement, 'status', NEW.status, 'confidence', NEW.confidence),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_tool_landscape_after_insert
AFTER INSERT ON tool_landscape
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'tool_landscape', NEW.tool_id, 'INSERT',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        NULL,
        json_object('statement', NEW.statement, 'status', NEW.status, 'confidence', NEW.confidence),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_tool_landscape_block_hard_delete
BEFORE DELETE ON tool_landscape
BEGIN
    SELECT RAISE(ABORT, 'Hard delete forbidden on tool_landscape (Bible 6.3 / INVARIANT-08). Transition status to deprecated or superseded instead.');
END;

-- ========================================================================
-- Table: policy_constraints
-- ========================================================================
CREATE TABLE IF NOT EXISTS policy_constraints (
    policy_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE,
    statement TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deprecated','contested','superseded')),
    confidence TEXT
);

CREATE TRIGGER IF NOT EXISTS trg_policy_constraints_after_update
AFTER UPDATE ON policy_constraints
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'policy_constraints', OLD.policy_id, 'UPDATE',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        json_object('statement', OLD.statement, 'status', OLD.status, 'confidence', OLD.confidence),
        json_object('statement', NEW.statement, 'status', NEW.status, 'confidence', NEW.confidence),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_policy_constraints_after_insert
AFTER INSERT ON policy_constraints
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'policy_constraints', NEW.policy_id, 'INSERT',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        NULL,
        json_object('statement', NEW.statement, 'status', NEW.status, 'confidence', NEW.confidence),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_policy_constraints_block_hard_delete
BEFORE DELETE ON policy_constraints
BEGIN
    SELECT RAISE(ABORT, 'Hard delete forbidden on policy_constraints (Bible 6.3 / INVARIANT-08). Transition status to deprecated or superseded instead.');
END;

-- ========================================================================
-- Table: findings
-- ========================================================================
CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    check_type TEXT NOT NULL CHECK (check_type IN ('schema_ld','robots_llms','extractability','citation_sampler','content_format','authority')),
    site_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE,
    evidence_state TEXT NOT NULL CHECK (evidence_state IN ('CONFIRMED','STRONGLY_SUPPORTED','POSSIBLE','INSUFFICIENT','ESCALATE')),
    raw_output TEXT NOT NULL,
    observed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_findings_claim    ON findings (claim_id);
CREATE INDEX IF NOT EXISTS idx_findings_site_run ON findings (site_id, run_id);

CREATE TRIGGER IF NOT EXISTS trg_findings_after_update
AFTER UPDATE ON findings
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'findings', OLD.finding_id, 'UPDATE',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        json_object('check_type', OLD.check_type, 'site_id', OLD.site_id, 'run_id', OLD.run_id, 'claim_id', OLD.claim_id, 'evidence_state', OLD.evidence_state, 'raw_output', OLD.raw_output, 'observed_at', OLD.observed_at),
        json_object('check_type', NEW.check_type, 'site_id', NEW.site_id, 'run_id', NEW.run_id, 'claim_id', NEW.claim_id, 'evidence_state', NEW.evidence_state, 'raw_output', NEW.raw_output, 'observed_at', NEW.observed_at),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_findings_after_insert
AFTER INSERT ON findings
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'findings', NEW.finding_id, 'INSERT',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        NULL,
        json_object('check_type', NEW.check_type, 'site_id', NEW.site_id, 'run_id', NEW.run_id, 'claim_id', NEW.claim_id, 'evidence_state', NEW.evidence_state, 'raw_output', NEW.raw_output, 'observed_at', NEW.observed_at),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_findings_block_hard_delete
BEFORE DELETE ON findings
BEGIN
    SELECT RAISE(ABORT, 'Hard delete forbidden on findings (Bible 6.3 / INVARIANT-08). Transition status to deprecated or superseded instead.');
END;

-- ========================================================================
-- Table: jobs
-- ========================================================================
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed')),
    payload TEXT NOT NULL,
    result TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status, created_at);

-- ========================================================================
-- Table: sources
-- ========================================================================
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    url TEXT,
    trust_tier TEXT NOT NULL CHECK (trust_tier IN ('T1','T2','T3','T4','T5','T6','T7')),
    source_type TEXT NOT NULL CHECK (source_type IN ('official-platform-doc','primary-research','legal-primary','named-practitioner','industry-media','vendor-research','community')),
    verified INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0,1)),
    verified_date TEXT,
    notes TEXT,
    approved_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sources_tier ON sources (trust_tier);
CREATE INDEX IF NOT EXISTS idx_sources_type ON sources (source_type);

-- ========================================================================
-- Table: claim_sources
-- ========================================================================
CREATE TABLE IF NOT EXISTS claim_sources (
    claim_source_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    primary_source INTEGER NOT NULL DEFAULT 0 CHECK (primary_source IN (0,1)),
    note TEXT,
    linked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_claim_sources_claim  ON claim_sources (claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_sources_source ON claim_sources (source_id);

-- ========================================================================
-- Table: check_code_mappings
-- ========================================================================
CREATE TABLE IF NOT EXISTS check_code_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_code TEXT NOT NULL,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ========================================================================
-- Table: prompt_sets
-- ========================================================================
CREATE TABLE IF NOT EXISTS prompt_sets (
    prompt_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    target_domain TEXT,
    funnel_stage TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TRIGGER IF NOT EXISTS trg_prompt_sets_after_update
AFTER UPDATE ON prompt_sets
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'prompt_sets', OLD.prompt_id, 'UPDATE',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        json_object('label', OLD.label, 'prompt_text', OLD.prompt_text, 'target_domain', OLD.target_domain, 'funnel_stage', OLD.funnel_stage, 'active', OLD.active, 'created_at', OLD.created_at),
        json_object('label', NEW.label, 'prompt_text', NEW.prompt_text, 'target_domain', NEW.target_domain, 'funnel_stage', NEW.funnel_stage, 'active', NEW.active, 'created_at', NEW.created_at),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_prompt_sets_after_insert
AFTER INSERT ON prompt_sets
FOR EACH ROW
BEGIN
    INSERT INTO changelog (entity_table, entity_id, operation, actor, reason, before_json, after_json, changed_at)
    VALUES (
        'prompt_sets', NEW.prompt_id, 'INSERT',
        (SELECT actor  FROM _txn_context WHERE id = 1),
        (SELECT reason FROM _txn_context WHERE id = 1),
        NULL,
        json_object('label', NEW.label, 'prompt_text', NEW.prompt_text, 'target_domain', NEW.target_domain, 'funnel_stage', NEW.funnel_stage, 'active', NEW.active, 'created_at', NEW.created_at),
        datetime('now')
    );
END;

-- ========================================================================
-- Table: audit_runs
-- ========================================================================
CREATE TABLE IF NOT EXISTS audit_runs (
    run_id TEXT PRIMARY KEY,
    target_domain TEXT NOT NULL,
    run_date TEXT NOT NULL,
    audited_stages TEXT NOT NULL,
    automated_findings TEXT NOT NULL,
    status TEXT DEFAULT 'automated_complete',
    overall_score INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_audit_runs_domain ON audit_runs (target_domain);

-- ========================================================================
-- Table: manual_verdicts
-- ========================================================================
CREATE TABLE IF NOT EXISTS manual_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    page_url TEXT DEFAULT '',
    verdict TEXT NOT NULL,
    severity TEXT NOT NULL,
    notes TEXT DEFAULT '',
    submitted_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_manual_verdicts_run ON manual_verdicts (run_id);

-- ========================================================================
-- Table: audit_synthesis
-- Added: UX audit §5.3 — persists the three-step LLM synthesis result
-- (previously only existed transiently in the POST /synthesize response,
-- so it vanished on page reload). See areos/db/schema/artifacts.py.
-- ========================================================================
CREATE TABLE IF NOT EXISTS audit_synthesis (
    run_id TEXT PRIMARY KEY,
    narrative TEXT DEFAULT '',
    draft TEXT DEFAULT '',
    flags_json TEXT DEFAULT '[]',
    flags_resolved INTEGER DEFAULT 0,
    provider_log_json TEXT DEFAULT '[]',
    manual_verdicts_merged INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_synthesis_run ON audit_synthesis (run_id);

-- ========================================================================
-- Table: idempotency_keys
-- ========================================================================
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_idempotency_created ON idempotency_keys (created_at);

-- ========================================================================
-- Standalone indexes (not tied to a single table's DSL, SEC-21)
-- ========================================================================
CREATE INDEX IF NOT EXISTS idx_prompt_sets_domain ON prompt_sets (target_domain);

-- claims_display_rank: a read-only VIEW for UI sorting across two source-tier vocabularies.
-- The mapping inside this view is a human judgment call (Bible §6.4 / ADR D5).
-- It is a UI convenience and is NEVER a write target.
CREATE VIEW IF NOT EXISTS claims_display_rank AS
SELECT claim_id,
       CASE
         WHEN source_tier_vocab = 'study_a' AND source_tier_value = 'official-platform-docs' THEN 1
         WHEN source_tier_vocab = 'study_b' AND source_tier_value = 'T1'                     THEN 1
         WHEN source_tier_vocab = 'study_a' AND source_tier_value = 'primary-research'       THEN 2
         WHEN source_tier_vocab = 'study_b' AND source_tier_value = 'T2'                     THEN 2
         WHEN source_tier_vocab = 'study_a' AND source_tier_value = 'reputable-practitioner' THEN 3
         WHEN source_tier_vocab = 'study_b' AND source_tier_value = 'T3'                     THEN 3
         WHEN source_tier_vocab = 'study_a' AND source_tier_value = 'forum-or-vendor-blog'   THEN 4
         WHEN source_tier_vocab = 'study_b' AND source_tier_value = 'T4'                     THEN 4
         WHEN source_tier_vocab = 'study_a' AND source_tier_value = 'mixed'                  THEN 5
         WHEN source_tier_vocab = 'study_b' AND source_tier_value = 'T5'                     THEN 5
         ELSE 99
       END AS display_rank
FROM claims;
