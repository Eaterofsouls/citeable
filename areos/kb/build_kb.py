import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

# Set admin token for KB build operations
os.environ.setdefault('AREOS_ADMIN_TOKEN', os.environ.get('AREOS_ADMIN_TOKEN', 'dev-build-kb'))

import shutil
import sqlite3

from areos.kb.models import KnowledgeRecord, EvidenceRecord, SourceRecord, CheckCodeMapping
from areos.db.connection import get_connection, get_db_path, close_all_connections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEMA_SQL = """
DROP TABLE IF EXISTS kb_metrics;
DROP TABLE IF EXISTS kb_embeddings;
DROP TABLE IF EXISTS kb_check_code_map;
DROP TABLE IF EXISTS kb_evidence;
DROP TABLE IF EXISTS kb_sources;
DROP TABLE IF EXISTS knowledge;

CREATE TABLE knowledge (
    kid TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('FACT','STANDARD','FINDING','UNCERTAINTY','GUIDANCE')),
    scope TEXT,
    statement TEXT NOT NULL,
    context TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    confidence TEXT DEFAULT 'medium',
    support TEXT DEFAULT 'partial',
    uncertainty TEXT,
    contradiction TEXT,
    guidance_json TEXT,
    aeog_phases TEXT,
    check_links TEXT,
    priority_score INTEGER,
    review_due TEXT,
    provenance_json TEXT,
    created_at TEXT,
    last_verified_at TEXT
);

CREATE TABLE kb_sources (
    sid TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    publisher TEXT,
    authority TEXT DEFAULT 'T3',
    pub_date TEXT,
    excerpt TEXT,
    notes TEXT
);

CREATE TABLE kb_evidence (
    eid TEXT PRIMARY KEY,
    kid TEXT NOT NULL REFERENCES knowledge(kid),
    sid TEXT NOT NULL REFERENCES kb_sources(sid),
    relationship TEXT DEFAULT 'supports',
    weight TEXT DEFAULT 'primary',
    note TEXT
);

CREATE TABLE kb_check_code_map (
    check_code TEXT NOT NULL,
    kid TEXT NOT NULL REFERENCES knowledge(kid),
    priority_score INTEGER NOT NULL DEFAULT 10,
    PRIMARY KEY (check_code, kid)
);

CREATE TABLE kb_embeddings (
    kid TEXT PRIMARY KEY REFERENCES knowledge(kid),
    vector_json TEXT NOT NULL,
    model TEXT NOT NULL,
    embedded_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS kb_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    kb_version TEXT NOT NULL DEFAULT '2026.01.01.0',
    last_updated TEXT,
    total_claims INTEGER NOT NULL DEFAULT 0,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS kb_metrics (
    key TEXT PRIMARY KEY,
    value TEXT
);

"""


def handle_claims_view(conn):
    cur = conn.cursor()
    cur.execute("SELECT type FROM sqlite_master WHERE name='claims'")
    row = cur.fetchone()
    if row:
        if row['type'] == 'table':
            logger.info("Renaming existing 'claims' table to 'claims_legacy'")
            cur.execute("DROP TABLE IF EXISTS claims_legacy")
            cur.execute("ALTER TABLE claims RENAME TO claims_legacy")
        elif row['type'] == 'view':
            logger.info("Dropping existing 'claims' view")
            cur.execute("DROP VIEW claims")
            
    view_sql = """
    CREATE VIEW IF NOT EXISTS claims AS
    SELECT 
        k.kid AS claim_id,
        NULL AS stage_id,
        k.scope AS claim_scope,
        k.type AS claim_type,
        k.statement,
        k.status,
        k.confidence,
        (SELECT s.url FROM kb_evidence e JOIN kb_sources s ON e.sid = s.sid 
         WHERE e.kid = k.kid AND e.weight = 'primary' LIMIT 1) AS source_url,
        'governed_corpus' AS source_tier_vocab,
        (SELECT s.authority FROM kb_evidence e JOIN kb_sources s ON e.sid = s.sid 
         WHERE e.kid = k.kid LIMIT 1) AS source_tier_value,
        NULL AS source_date,
        k.last_verified_at AS last_verified,
        NULL AS superseded_by,
        0 AS is_client_evidence
    FROM knowledge k;
    """
    cur.execute(view_sql)


def parse_jsonl(file_path: Path):
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return []
        
    items = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed JSONL line in {file_path.name}: {e}")
    return items

def build(db_path: Path | str | None = None, corpus_dir: Path | str | None = None):
    base_dir = Path(__file__).parent
    if corpus_dir is None:
        corpus_dir = base_dir / 'corpus'
    else:
        corpus_dir = Path(corpus_dir)
    
    if db_path is None:
        db_path = get_db_path()

    conn = get_connection(db_path)

    # Get current version from destination connection
    current_version = 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM kb_metrics WHERE key='version'")
        row = cur.fetchone()
        if row and row['value']:
            current_version = int(row['value'])
    except sqlite3.OperationalError:
        pass

    # Create staging in-memory database for atomic rebuild (DEC-15)
    staging_conn = sqlite3.connect(":memory:")
    staging_conn.row_factory = sqlite3.Row
    staging_conn.execute("PRAGMA foreign_keys = ON")

    # Copy existing database schema & data into staging to preserve non-KB tables
    try:
        conn.backup(staging_conn)
    except Exception:
        pass

    try:
        # Drop and recreate KB schema on staging
        for stmt in SCHEMA_SQL.split(";"):
            stmt = stmt.strip()
            if stmt:
                staging_conn.execute(stmt)
        
        # Handle claims view
        handle_claims_view(staging_conn)
        
        cur = staging_conn.cursor()
        
        # Parse and insert knowledge
        knowledge_items = parse_jsonl(corpus_dir / 'knowledge.jsonl')
        seen_kids = set()
        for item in knowledge_items:
            try:
                record = KnowledgeRecord(**item)
            except Exception as e:
                logger.error(f"Error parsing knowledge item: {e}")
                continue

            if record.kid in seen_kids:
                logger.warning(f"Duplicate KID encountered in knowledge.jsonl: {record.kid} — replacing existing record")
            seen_kids.add(record.kid)

            guidance_json = record.guidance.model_dump_json() if record.type == 'GUIDANCE' and record.guidance else None
            aeog_phases = json.dumps(record.aeog_phases) if record.aeog_phases else json.dumps([])
            check_links = json.dumps(record.check_links) if record.check_links else json.dumps([])
            provenance_json = json.dumps(record.provenance) if record.provenance else json.dumps({})
            
            review_due = record.provenance.get('review_due') if record.provenance else None
            
            # Handle history as dict or list
            created_at = None
            last_verified_at = None
            if isinstance(record.history, dict):
                created_at = record.history.get('created')
                last_verified_at = record.history.get('last_verified')
            elif isinstance(record.history, list) and record.history:
                # History is a list of {at, by, action, ...} entries
                created_at = record.history[0].get('at') if record.history else None
            
            if not last_verified_at and record.provenance:
                last_verified_at = record.provenance.get('last_verified')
                
            cur.execute("""
                INSERT OR REPLACE INTO knowledge (
                    kid, type, scope, statement, context, status, confidence, support,
                    uncertainty, contradiction, guidance_json, aeog_phases, check_links,
                    priority_score, review_due, provenance_json, created_at, last_verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.kid, record.type, record.scope, record.statement, record.context,
                record.status, record.confidence, record.support,
                record.uncertainty, record.contradiction,
                guidance_json, aeog_phases, check_links, record.priority_score,
                review_due, provenance_json, created_at, last_verified_at
            ))
            
        # Parse and insert sources
        sources_items = parse_jsonl(corpus_dir / 'sources.jsonl')
        for s_dict in sources_items:
            cur.execute("""
                INSERT INTO kb_sources (
                    sid, url, title, publisher, authority, pub_date, excerpt, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s_dict.get('sid'), s_dict.get('url'), s_dict.get('title'),
                s_dict.get('publisher'), s_dict.get('authority', 'T3'), s_dict.get('pub_date'), 
                s_dict.get('excerpt'), s_dict.get('notes')
            ))
            
        # Parse and insert evidence
        evidence_items = parse_jsonl(corpus_dir / 'evidence.jsonl')
        ev_skipped = 0
        for item in evidence_items:
            try:
                record = EvidenceRecord(**item)
            except Exception as e:
                logger.error(f"Error parsing evidence item: {e}")
                continue
                
            try:
                cur.execute("""
                    INSERT INTO kb_evidence (
                        eid, kid, sid, relationship, weight, note
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    record.eid, record.kid, record.sid, record.relationship,
                    record.weight, record.note
                ))
            except Exception as e:
                ev_skipped += 1
                logger.warning(f"Skipping evidence {record.eid}: {e}")

        # Parse and insert check code mappings
        cc_map_path = base_dir / 'check_code_to_knowledge_map.json'
        if not cc_map_path.exists():
            cc_map_path = corpus_dir / 'check_code_to_knowledge_map.json'
            
        check_code_count = 0
        if cc_map_path.exists():
            with open(cc_map_path, 'r', encoding='utf-8') as f:
                cc_map_data = json.load(f)
                
            for cc, data in cc_map_data.items():
                # Actual format: {"guidance_record": "KT-xxx", "backing_records": ["KT-yyy"]}
                guidance_kid = data.get('guidance_record') or data.get('guidance_id')
                knowledge_ids = data.get('knowledge_ids', [])
                backing_records = data.get('backing_records', [])
                priority = data.get('priority', 10)
                
                # Primary: guidance_record
                if guidance_kid:
                    try:
                        cur.execute("""
                            INSERT OR IGNORE INTO kb_check_code_map (check_code, kid, priority_score)
                            VALUES (?, ?, ?)
                        """, (cc, guidance_kid, priority))
                        check_code_count += 1
                    except Exception as e:
                        logger.warning(f"Skipping check code mapping {cc}->{guidance_kid}: {e}")
                
                # Backing records (TR-202) - assigned lower priority than primary guidance
                backing_priority = max(1, priority - 5)
                for kid in backing_records:
                    try:
                        cur.execute("""
                            INSERT OR IGNORE INTO kb_check_code_map (check_code, kid, priority_score)
                            VALUES (?, ?, ?)
                        """, (cc, kid, backing_priority))
                        check_code_count += 1
                    except Exception as e:
                        logger.warning(f"Skipping check code mapping {cc}->{kid}: {e}")
                
                # Fallback: knowledge_ids list (legacy format)
                for kid in knowledge_ids:
                    try:
                        cur.execute("""
                            INSERT OR IGNORE INTO kb_check_code_map (check_code, kid, priority_score)
                            VALUES (?, ?, ?)
                        """, (cc, kid, priority))
                        check_code_count += 1
                    except Exception as e:
                        logger.warning(f"Skipping check code mapping {cc}->{kid}: {e}")
                    
        # Metadata
        new_version = current_version + 1
        rebuilt_at = datetime.now(timezone.utc).isoformat()
        
        meta_items = [
            ('version', str(new_version)),
            ('rebuilt_at', rebuilt_at),
            ('record_count', str(len(knowledge_items))),
            ('evidence_count', str(len(evidence_items))),
            ('source_count', str(len(sources_items))),
            ('check_code_count', str(check_code_count)),
            ('embedding_count', '0'),
            ('embedding_model', '')
        ]
        
        cur.execute(
            "INSERT OR REPLACE INTO kb_meta (id, kb_version, last_updated, total_claims, updated_by) VALUES (1, ?, ?, ?, ?)",
            (new_version, rebuilt_at, len(knowledge_items), "build_kb")
        )
        cur.executemany("INSERT INTO kb_metrics (key, value) VALUES (?, ?)", meta_items)
        
        staging_conn.commit()

        # Atomic staging swap: backup staging database into live destination connection
        staging_conn.backup(conn)
        staging_conn.close()

    except Exception as e:
        logger.error(f"Error during KB build: {e}")
        try:
            staging_conn.close()
        except Exception:
            pass
        raise
    
    logger.info("Build complete. Summary stats:")
    logger.info(f"  Knowledge records: {len(knowledge_items)}")
    logger.info(f"  Evidence records: {len(evidence_items) - ev_skipped} (skipped {ev_skipped})")
    logger.info(f"  Source records: {len(sources_items)}")
    logger.info(f"  Check code mappings: {check_code_count}")
    logger.info(f"  Database Version: {new_version}")

    return conn


def embed_corpus(conn=None, force: bool = False) -> int:
    """Pre-compute embeddings for all active knowledge records.

    Uses server-side API keys (env vars). Gracefully skips if no key available (D-014).
    Returns the number of records embedded.

    Args:
        conn:  Optional DB connection. If None, creates one.
        force: If True, re-embed even if embeddings already exist.
    """
    from areos.kb.embeddings import embed, get_active_model, EmbeddingUnavailable

    if conn is None:
        db_path = get_db_path()
        conn = get_connection(db_path)

    # Check if embeddings already exist and we're not forcing
    if not force:
        count = conn.execute("SELECT count(*) FROM kb_embeddings").fetchone()[0]
        if count > 0:
            logger.info(f"  Embeddings already exist ({count} records). Use --embed-force to regenerate.")
            return count

    # Check if an embedding provider is available
    model_name = get_active_model()
    if not model_name:
        logger.info("  No embedding API key found (env vars). Skipping embedding. RAG will be unavailable.")
        logger.info("  Set AREOS_GEMINI_KEY_1, OPENAI_API_KEY, or MISTRAL_API_KEY to enable.")
        return 0

    logger.info(f"  Embedding corpus with model: {model_name}")

    # Load all active knowledge records
    rows = conn.execute(
        "SELECT kid, statement, context FROM knowledge WHERE status NOT IN ('archived', 'deprecated')"
    ).fetchall()

    embedded = 0
    failed = 0
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        kid = row["kid"]
        # Build embedding text: statement + context for richer semantics
        text = row["statement"]
        if row["context"]:
            text += f" | {row['context']}"

        try:
            vector = embed(text)
            conn.execute(
                "INSERT OR REPLACE INTO kb_embeddings (kid, vector_json, model, embedded_at) "
                "VALUES (?, ?, ?, ?)",
                (kid, json.dumps(vector), model_name, now),
            )
            embedded += 1
        except EmbeddingUnavailable:
            logger.warning(f"  Embedding provider unavailable mid-batch at {kid}. Stopping.")
            break
        except Exception as e:
            failed += 1
            logger.warning(f"  Failed to embed {kid}: {e}")

    conn.commit()

    # Update metadata
    conn.execute(
        "INSERT OR REPLACE INTO kb_metrics (key, value) VALUES ('embedding_count', ?)",
        (str(embedded),),
    )
    conn.execute(
        "INSERT OR REPLACE INTO kb_metrics (key, value) VALUES ('embedding_model', ?)",
        (model_name,),
    )
    conn.commit()

    logger.info(f"  Embedded {embedded} records (failed: {failed})")
    return embedded


if __name__ == '__main__':
    import sys
    conn = build()
    # Embed if --embed or --embed-force flag is passed
    if '--embed' in sys.argv or '--embed-force' in sys.argv:
        force = '--embed-force' in sys.argv
        embed_corpus(conn, force=force)
    elif os.environ.get('AREOS_EMBED_ON_BUILD', '').lower() in ('1', 'true', 'yes'):
        embed_corpus(conn)
