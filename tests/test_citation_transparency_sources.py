import sqlite3
import pytest
from areos.services.sources import get_sources_for_claim
from areos.services.report_generator import get_report_data


def test_citation_transparency_reads_kb_evidence_and_sources(tmp_path):
    """Verify get_sources_for_claim and get_report_data return non-empty sources from kb_evidence/kb_sources."""
    db_file = tmp_path / "test_kb.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    # Create tables: knowledge, kb_sources, kb_evidence, and claims view
    conn.execute("""
        CREATE TABLE knowledge (
            kid TEXT PRIMARY KEY,
            scope TEXT,
            type TEXT,
            statement TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            confidence REAL DEFAULT 1.0,
            last_verified_at TEXT
        );
    """)
    conn.execute("""
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
    """)
    conn.execute("""
        CREATE TABLE kb_evidence (
            eid TEXT PRIMARY KEY,
            kid TEXT NOT NULL REFERENCES knowledge(kid),
            sid TEXT NOT NULL REFERENCES kb_sources(sid),
            relationship TEXT DEFAULT 'supports',
            weight TEXT DEFAULT 'primary',
            note TEXT
        );
    """)
    conn.execute("""
        CREATE VIEW claims AS
            SELECT 
                k.kid AS claim_id,
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
                k.last_verified_at AS last_verified
            FROM knowledge k;
    """)

    # Seed knowledge row + kb_sources row + kb_evidence row
    test_kid = "K-TEST-001"
    test_sid = "SRC-TEST-001"
    test_url = "https://example.com/verified-source-doc"

    conn.execute(
        "INSERT INTO knowledge (kid, statement, status) VALUES (?, ?, ?)",
        (test_kid, "Structured testing statement.", "active"),
    )
    conn.execute(
        "INSERT INTO kb_sources (sid, url, title, publisher, authority) VALUES (?, ?, ?, ?, ?)",
        (test_sid, test_url, "Verified Source Title", "Test Publisher", "T1"),
    )
    conn.execute(
        "INSERT INTO kb_evidence (eid, kid, sid, relationship, weight, note) VALUES (?, ?, ?, ?, ?, ?)",
        ("E-TEST-001", test_kid, test_sid, "supports", "primary", "Official specification document"),
    )
    conn.commit()

    # 1. Test get_sources_for_claim from sources.py
    sources = get_sources_for_claim(conn, test_kid)
    assert len(sources) > 0, "Expected non-empty source list from get_sources_for_claim"
    assert sources[0]["url"] == test_url
    assert sources[0]["source_id"] == test_sid
    assert sources[0]["sid"] == test_sid
    assert sources[0]["trust_tier"] == "T1"
    assert sources[0]["primary_source"] == 1

    # 2. Test get_report_data from report_generator.py
    report_claims = get_report_data(conn)
    matching = [c for c in report_claims if c["claim_id"] == test_kid]
    assert len(matching) == 1
    assert len(matching[0]["sources"]) > 0, "Expected non-empty sources in report_generator"
    assert matching[0]["sources"][0]["url"] == test_url
    assert matching[0]["sources"][0]["source_id"] == test_sid
