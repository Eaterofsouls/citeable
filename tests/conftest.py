import os
import tempfile
import pytest
from pathlib import Path
from areos.db.migrate_audit_tables import migrate
from areos.kb.build_kb import build

@pytest.fixture(autouse=True, scope="session")
def _isolate_test_db():
    """Autouse session fixture ensuring all tests use an isolated test database with full schema and KB."""
    if not os.environ.get("AREOS_TEST_DB"):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db_path = tmp.name
        tmp.close()
        os.environ["AREOS_TEST_DB"] = temp_db_path
        
        # Initialize schema and KB tables in test database
        migrate(temp_db_path)
        build(temp_db_path)
        
        try:
            yield temp_db_path
        finally:
            for suffix in ["", "-wal", "-shm"]:
                p = temp_db_path + suffix
                if os.path.exists(p):
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
    else:
        yield os.environ["AREOS_TEST_DB"]
