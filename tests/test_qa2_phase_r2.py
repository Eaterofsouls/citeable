"""Phase R2 Regression Suite: Knowledge Base and RAG Optimization (TR-201 to TR-205)."""
import json
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch

from areos.kb.router import resolve, THRESHOLD_PRIMARY, THRESHOLD_ENRICHMENT
from areos.auditors.scoring import LAYER_DEDUCTIONS, compute_layered_score
from areos.kb.build_kb import build as build_kb


class TestR2RAGCandidatesPool:
    """Tests for dual-threshold RAG candidate retrieval (min_similarity=0.70)."""

    def test_rag_retains_enrichment_at_070_threshold(self, tmp_path):
        """Verify candidate with similarity 0.75 is retained in resolution.enrichment."""
        db_path = tmp_path / "rag_test1.db"
        build_kb(db_path=str(db_path))

        mock_candidates = [
            {"kid": "KT-124", "similarity": 0.85, "statement": "Primary"},
            {"kid": "KT-125", "similarity": 0.75, "statement": "Enrichment"}
        ]
        with patch("areos.kb.router._rag_search", return_value=mock_candidates) as mock_search:
            res = resolve("NOVEL_FINDING", "Novel description", db_path=str(db_path))
            mock_search.assert_called_once()
            _, kwargs = mock_search.call_args
            assert kwargs["threshold"] == THRESHOLD_ENRICHMENT
            assert res.path == "SEMANTIC"
            assert res.primary_kid == "KT-124"
            assert len(res.enrichment) == 1
            assert res.enrichment[0]["kid"] == "KT-125"

    def test_rag_promotes_top_candidate_at_082_threshold(self, tmp_path):
        """Verify candidate >= 0.82 is promoted to primary."""
        db_path = tmp_path / "rag_test2.db"
        build_kb(db_path=str(db_path))

        mock_candidates = [{"kid": "KT-124", "similarity": 0.90, "statement": "Primary"}]
        with patch("areos.kb.router._rag_search", return_value=mock_candidates):
            res = resolve("NOVEL_FINDING", "Novel", db_path=str(db_path))
            assert res.path == "SEMANTIC"
            assert res.primary_kid == "KT-124"

    def test_rag_discards_candidate_below_070(self, tmp_path):
        """Verify candidate < 0.82 does not become primary."""
        db_path = tmp_path / "rag_test3.db"
        build_kb(db_path=str(db_path))

        mock_candidates = [{"kid": "KT-124", "similarity": 0.75, "statement": "Medium"}]
        with patch("areos.kb.router._rag_search", return_value=mock_candidates):
            res = resolve("UNKNOWN_FINDING", "Desc", db_path=str(db_path))
            assert res.path == "INSUFFICIENT"


class TestR2BindingsAndScoring:
    """Tests for backing records, SAMEAS_DEAD_LINK, and duplicates."""

    def test_build_kb_inserts_backing_records(self, tmp_path):
        """Verify build_kb inserts backing records into kb_check_code_map."""
        db_path = tmp_path / "kb_build_test.db"
        build_kb(db_path=str(db_path))
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT * FROM kb_check_code_map WHERE check_code = 'CRAWLER_FULLY_BLOCKED'").fetchall()
        conn.close()
        kids = [r[1] for r in rows]
        assert "KT-124" in kids
        assert "KT-033" in kids

    def test_resolve_check_code_returns_backing_records(self, tmp_path):
        """Verify deterministic resolution returns primary guidance."""
        db_path = tmp_path / "kb_res_test.db"
        build_kb(db_path=str(db_path))
        res = resolve("CRAWLER_FULLY_BLOCKED", db_path=str(db_path))
        assert res.path == "DETERMINISTIC"
        assert res.primary_kid == "KT-124"

    def test_sameas_dead_link_mapped_in_kb(self):
        """Verify SAMEAS_DEAD_LINK exists in check_code_to_knowledge_map.json."""
        map_path = Path("areos/kb/check_code_to_knowledge_map.json")
        check_map = json.loads(map_path.read_text(encoding="utf-8"))
        assert "SAMEAS_DEAD_LINK" in check_map
        assert check_map["SAMEAS_DEAD_LINK"]["guidance_record"] == "KG-003"

    def test_sameas_dead_link_deducts_points(self):
        """Verify SAMEAS_DEAD_LINK has deduction in Layer 3."""
        assert "SAMEAS_DEAD_LINK" in LAYER_DEDUCTIONS
        layer, pts = LAYER_DEDUCTIONS["SAMEAS_DEAD_LINK"]
        assert layer == "schema"
        assert pts > 0
        res = compute_layered_score([{"code": "SAMEAS_DEAD_LINK"}])
        assert res.sub_scores["schema"].score < res.sub_scores["schema"].max_points

    def test_build_kb_logs_duplicate_kid_warning(self, tmp_path, caplog):
        """Verify build_kb logs warning on duplicate KID in corpus."""
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        k_line = json.dumps({"kid": "KT-999", "type": "FACT", "statement": "Test Fact", "scope": "general", "status": "active"})
        (corpus_dir / "knowledge.jsonl").write_text(f"{k_line}\n{k_line}\n", encoding="utf-8")
        (corpus_dir / "sources.jsonl").write_text("", encoding="utf-8")
        (corpus_dir / "evidence.jsonl").write_text("", encoding="utf-8")

        db_path = tmp_path / "kb_dup_test.db"
        import logging
        with caplog.at_level(logging.WARNING):
            build_kb(db_path=str(db_path), corpus_dir=corpus_dir)
        assert any("Duplicate KID" in msg for msg in caplog.messages)
