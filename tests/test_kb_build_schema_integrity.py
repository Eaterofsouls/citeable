import sqlite3
import pytest
from areos.kb.build_kb import build
from areos.db.kb_version import get_kb_version

def test_kb_build_preserves_kb_meta_check_constraint(tmp_path):
    db_file = tmp_path / "test_integrity.db"
    
    # 1. First build
    build(str(db_file))
    
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    v1 = get_kb_version(conn)
    assert v1 is not None
    assert v1["kb_version"] is not None
    
    # Verify CHECK(id=1) on kb_meta is intact and rejects id=2
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO kb_meta (id, kb_version, last_updated, total_claims, updated_by) VALUES (2, 'v2', '2026-01-01', 10, 'tester')")
    conn.close()
    
    # 2. Successive build
    build(str(db_file))
    conn2 = sqlite3.connect(str(db_file))
    conn2.row_factory = sqlite3.Row
    v2 = get_kb_version(conn2)
    assert v2 is not None
    conn2.close()
