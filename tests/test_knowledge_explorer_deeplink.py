import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_API_TOKEN", "test_token")

from areos.api.main import app

UI = Path(__file__).resolve().parents[1] / "areos" / "ui"

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_knowledge_explorer_script_has_deeplink_logic():
    src = (UI / "knowledge_explorer.js").read_text(encoding="utf-8")
    assert "getTargetKidFromUrl" in src
    assert "setUrlKid" in src
    assert "focusAndHighlightTarget" in src
    assert "loadAndOpenDrawer" in src
    assert "popstate" in src
    assert "hashchange" in src
    assert "highlight-target" in src

def test_knowledge_explorer_css_has_highlight_animation():
    css = (UI / "index.css").read_text(encoding="utf-8")
    assert "@keyframes highlight-pulse" in css
    assert ".index-row.highlight-target" in css

def test_knowledge_api_returns_kt113_detail_for_deeplink(client):
    headers = {"Authorization": "Bearer test_token"}
    res = client.get("/api/v1/knowledge/KT-113", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["record"]["kid"] == "KT-113"
    assert "evidence" in data
    assert "sources" in data
    assert len(data["evidence"]) >= 1

def test_knowledge_api_query_returns_kt113_in_full_batch(client):
    headers = {"Authorization": "Bearer test_token"}
    res = client.get("/api/v1/knowledge?limit=250", headers=headers)
    assert res.status_code == 200
    data = res.json()
    kids = [r["kid"] for r in data["records"]]
    assert "KT-113" in kids
