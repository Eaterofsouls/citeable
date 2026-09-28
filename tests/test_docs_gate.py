import os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")
from starlette.testclient import TestClient
from areos.api import main as api_main
from areos.api.main import app

PROTECTED = [
    "/docs/internal/01-architecture.md",
    "/docs//internal/01-architecture.md",
    "/docs///internal/01-architecture.md",
    "/docs/./internal/01-architecture.md",
    "/docs/internal/../internal/01-architecture.md",
    "/docs/%2finternal/01-architecture.md",
    "/docs/%252finternal/01-architecture.md",
    "/docs/INTERNAL/01-architecture.md",
    "/docs/internal_legacy.md",
    "/docs/external_legacy.md",
    "/docs/session_artifacts/VISUAL_MASTER_CONVERGENCE_REPORT.md",
    "/docs//session_artifacts/VISUAL_MASTER_CONVERGENCE_REPORT.md",
]

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.parametrize("path", PROTECTED)
def test_never_served_without_token(client, path):
    assert client.get(path).status_code in (401, 403, 404)

@pytest.mark.parametrize("path", PROTECTED)
def test_wrong_token_rejected(client, path):
    r = client.get(path, headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code in (401, 403, 404)

def test_valid_token_still_reads_internal_docs(client):
    token = api_main._INTERNAL_DOCS_TOKEN
    assert token
    h = {"Authorization": f"Bearer {token}"}
    for p in ("/docs/internal/01-architecture.md", "/docs//internal/01-architecture.md"):
        assert client.get(p, headers=h).status_code == 200

def test_public_docs_still_served(client):
    assert client.get("/docs/scoring.md").status_code == 200
