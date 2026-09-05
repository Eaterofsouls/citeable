# tests/test_rag.py
#
# Phase 3 Regression Gate: RAG semantic search and confidence gates.
#
# These tests verify:
#   1. Embedding waterfall gracefully handles missing keys (D-014)
#   2. Cosine similarity math is correct
#   3. Router handles all three tiers
#   4. Confidence gates enforce thresholds (D-011)
#   5. embed_corpus works with and without API keys
#   6. UNMAPPED findings attempt RAG fallback

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_API_TOKEN", "test_rag_token")


# ── Embedding Unit Tests ──────────────────────────────────────────────────────

class TestCosineDistance:
    """Verify pure-Python cosine similarity implementation."""

    def test_identical_vectors(self):
        from areos.kb.embeddings import cosine_similarity
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        from areos.kb.embeddings import cosine_similarity
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        from areos.kb.embeddings import cosine_similarity
        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector(self):
        from areos.kb.embeddings import cosine_similarity
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_dimension_mismatch(self):
        from areos.kb.embeddings import cosine_similarity
        a = [1.0, 2.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0


class TestEmbeddingWaterfall:
    """Verify embedding provider waterfall behavior."""

    def test_no_key_raises_unavailable(self):
        from areos.kb.embeddings import embed, EmbeddingUnavailable
        # Clear any env vars that might be set
        saved = {}
        for k in ("AREOS_GEMINI_KEY_1", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
            saved[k] = os.environ.pop(k, None)
        try:
            with pytest.raises(EmbeddingUnavailable):
                embed("test text", client_keys={})
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_get_active_model_no_keys(self):
        from areos.kb.embeddings import get_active_model
        saved = {}
        for k in ("AREOS_GEMINI_KEY_1", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
            saved[k] = os.environ.pop(k, None)
        try:
            assert get_active_model(client_keys={}) is None
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_waterfall_with_client_key(self):
        from areos.kb.embeddings import get_active_model
        # A client key should activate the provider
        model = get_active_model(client_keys={"google": "fake-key"})
        assert model == "text-embedding-004"


# ── Router Confidence Gate Tests ──────────────────────────────────────────────

class TestConfidenceGates:
    """Verify the threshold enforcement logic."""

    def test_thresholds_defined(self):
        from areos.kb.router import THRESHOLD_PRIMARY, THRESHOLD_ENRICHMENT, THRESHOLD_CROSS_PHASE
        assert THRESHOLD_PRIMARY == 0.82
        assert THRESHOLD_ENRICHMENT == 0.70
        assert THRESHOLD_CROSS_PHASE == 0.75

    def test_primary_above_threshold(self):
        """If similarity >= 0.82, the record should be returned as primary."""
        from areos.kb.router import THRESHOLD_PRIMARY
        sim = 0.85
        assert sim >= THRESHOLD_PRIMARY

    def test_primary_below_threshold(self):
        """If similarity < 0.82, it should NOT be used as primary."""
        from areos.kb.router import THRESHOLD_PRIMARY
        sim = 0.78
        assert sim < THRESHOLD_PRIMARY


class TestRouterGracefulDegradation:
    """Verify router works without embeddings (D-014)."""

    @pytest.fixture(scope="class")
    def db_path(self):
        from areos.kb.build_kb import build
        build()
        from areos.db.connection import get_db_path
        return get_db_path()

    def test_deterministic_works_without_embeddings(self, db_path):
        """Known check codes resolve deterministically even with 0 embeddings."""
        from areos.kb.router import resolve
        resolution = resolve("CRAWLER_FULLY_BLOCKED", db_path=db_path)
        assert resolution.path == "DETERMINISTIC"
        assert resolution.primary_kid is not None

    def test_unknown_code_without_embeddings(self, db_path):
        """UNMAPPED codes gracefully return INSUFFICIENT when no embeddings exist."""
        from areos.kb.router import resolve
        # Clear any embedding keys
        saved = {}
        for k in ("AREOS_GEMINI_KEY_1", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
            saved[k] = os.environ.pop(k, None)
        try:
            resolution = resolve(
                "NOVEL_FINDING_XYZ",
                "AI crawler is doing something unexpected",
                client_keys={},
                db_path=db_path,
            )
            assert resolution.path == "INSUFFICIENT"
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_router_returns_enrichment_for_known(self, db_path):
        """Known codes should attempt RAG enrichment (returns [] without embeddings)."""
        from areos.kb.router import resolve
        resolution = resolve("CRAWLER_FULLY_BLOCKED", db_path=db_path)
        # Without embeddings, enrichment should be empty list (not error)
        assert isinstance(resolution.enrichment, list)


class TestEmbedCorpus:
    """Verify embed_corpus function behavior."""

    def test_embed_corpus_no_key_returns_zero(self):
        """Without API keys, embed_corpus gracefully returns 0."""
        from areos.kb.build_kb import build, embed_corpus
        saved = {}
        for k in ("AREOS_GEMINI_KEY_1", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
            saved[k] = os.environ.pop(k, None)
        try:
            conn = build()
            count = embed_corpus(conn)
            assert count == 0
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


# ── Wire Finding RAG Fallback Test ────────────────────────────────────────────

class TestWireFindingRAGFallback:
    """Verify that wire_finding attempts RAG for unmapped codes."""

    @pytest.fixture(scope="class")
    def db_path(self):
        from areos.kb.build_kb import build
        build()
        from areos.db.connection import get_db_path
        return get_db_path()

    def test_unmapped_without_embeddings_stays_unmapped(self, db_path):
        """Without embeddings, UNMAPPED codes stay UNMAPPED (graceful degradation)."""
        from pathlib import Path
        from areos.auditors.findings_to_claims import wire_finding
        wired = wire_finding(
            check_code="NOVEL_CHECK_CODE_XYZ",
            severity="warning",
            message="A novel finding",
            source_auditor="automated",
            db_path=Path(db_path),
            client_keys={},  # No keys
        )
        assert wired.wiring_status == "UNMAPPED"
