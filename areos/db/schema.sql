-- ==========================================================================
-- schema.sql  —  HAND-MAINTAINED FILE.
-- ==========================================================================
-- Operational database schema for Citeable / AREOS.
-- Parity is verified via tests/test_schema_matches_live_db.py.
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

CREATE INDEX IF NOT EXISTS idx_prompt_sets_domain ON prompt_sets (target_domain);

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
    run_token TEXT,
    score_detail_json TEXT,
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
-- Table: manual_observations (T-B01)
-- Track B: Structured observation storage for the 11-question review system.
-- Coexists with manual_verdicts for backward compatibility with older runs.
-- ========================================================================
CREATE TABLE IF NOT EXISTS manual_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    structured_data TEXT NOT NULL,
    severity TEXT NOT NULL,
    diagnosis_text TEXT,
    submitted_at TEXT DEFAULT (datetime('now')),
    UNIQUE(run_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_manual_observations_run ON manual_observations (run_id);

-- ========================================================================
-- Table: audit_synthesis
-- Added: UX audit §5.3 — persists the three-step LLM synthesis result
-- (previously only existed transiently in the POST /synthesize response,
-- so it vanished on page reload).
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
-- Table: synthesis_prompts (Phase 2 LLM pipeline)
-- ========================================================================
CREATE TABLE IF NOT EXISTS synthesis_prompts (
    step          TEXT PRIMARY KEY,
    system_prompt TEXT NOT NULL,
    updated_at    TEXT,
    updated_by    TEXT
);
