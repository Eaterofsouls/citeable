import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_API_TOKEN", "test_token")

@pytest.fixture(scope="module")
def client():
    from areos.api.main import app
    from areos.kb.build_kb import build
    # Ensure KB is built
    build()
    return TestClient(app)


def test_knowledge_list(client):
    res = client.get("/api/v1/knowledge", headers={"Authorization": "Bearer test_token"})
    assert res.status_code == 200
    data = res.json()
    assert "total_count" in data
    assert "records" in data
    assert len(data["records"]) > 0

def test_knowledge_stats(client):
    res = client.get("/api/v1/knowledge/stats", headers={"Authorization": "Bearer test_token"})
    assert res.status_code == 200
    data = res.json()
    assert data["knowledge_count"] > 0
    assert "version" in data
    assert "rebuilt_at" in data

def test_knowledge_detail(client):
    # First get a list to find a valid kid
    res_list = client.get("/api/v1/knowledge?limit=1", headers={"Authorization": "Bearer test_token"})
    kid = res_list.json()["records"][0]["kid"]
    
    res = client.get(f"/api/v1/knowledge/{kid}", headers={"Authorization": "Bearer test_token"})
    assert res.status_code == 200
    data = res.json()
    assert "record" in data
    assert data["record"]["kid"] == kid
    assert "evidence" in data
    assert "sources" in data
    assert "related_check_codes" in data
