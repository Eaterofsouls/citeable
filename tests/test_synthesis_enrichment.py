import json
from areos.llm.synthesis_pipeline import _build_synthesizer_input

def test_synthesizer_input_includes_v2_evidence():
    """Verify that the V2 knowledge evidence fields are correctly passed to the LLM."""
    enriched_recs = [
        {
            "check_code": "ROBOTS_MISSING",
            "claim_id": "KT-124",
            "claim_statement": "Robots.txt is crucial.",
            "evidence_chain": [
                {"eid": "EV-001", "sid": "SRC-001", "relationship": "supports", "weight": "strong"}
            ],
            "source_citations": [
                {"sid": "SRC-001", "url": "https://example.com/docs", "title": "Docs", "authority": "high"}
            ],
            "backing_facts": [
                {"kid": "KF-001", "statement": "Googlebot respects robots.txt"}
            ],
            "is_contested": True,
            "is_stale": False,
        }
    ]
    
    prompt = _build_synthesizer_input(enriched_recs, "example.com")
    
    assert "example.com" in prompt
    assert "ROBOTS_MISSING" in prompt
    assert "KT-124" in prompt
    assert "Robots.txt is crucial." in prompt
    
    # Check that V2 fields are serialized in the JSON portion
    # The JSON string is embedded in the prompt
    assert "evidence_chain" in prompt
    assert "EV-001" in prompt
    assert "source_citations" in prompt
    assert "https://example.com/docs" in prompt
    assert "backing_facts" in prompt
    assert "Googlebot respects robots.txt" in prompt
    assert "is_contested" in prompt
