# areos/services/diff_service.py
#
# Core logic for Task 2c: The Diff Step.
# Compare extracted candidate claims against live DB claims.
# 
# CONTRACT (PD-2 compliant):
#   - NEVER writes to the live DB.
#   - Returns a structured changelog of proposed changes.
#   - Uses the LLM waterfall provider for semantic classification.

from __future__ import annotations
import json
import logging
from datetime import date
from areos.db.connection import get_connection
from areos.llm import providers

logger = logging.getLogger(__name__)

DIFF_SYSTEM_PROMPT = """You are an expert fact-checker and knowledge base maintainer.
Your job is to compare a NEW CANDIDATE claim against a list of EXISTING claims.
You must output a single JSON object classifying the candidate into one of three categories:

1. "corroborating" - The candidate states the exact same underlying fact/policy as an existing claim.
2. "contradicting" - The candidate directly conflicts with an existing claim.
3. "novel" - The candidate contains new information not covered by any existing claim.

Output JSON format exactly:
{
  "classification": "corroborating|contradicting|novel",
  "target_claim_id": "ID of the existing claim (if corroborating or contradicting), else null",
  "rationale": "Brief 1-sentence explanation for your choice"
}
"""

def generate_changelog(db_path: str, candidate_bundle: dict) -> dict:
    """
    Given a DB path and a candidate bundle dictionary, return a structured
    changelog representing proposed DB operations.
    """
    run_id = candidate_bundle["run_id"]
    stage_id = candidate_bundle["stage_id"]
    candidates = candidate_bundle.get("candidates", [])
    
    # 1. Gather distinct claim_types in this bundle
    claim_types = list(set(c["claim_type"] for c in candidates if "claim_type" in c))
    
    # 2. Fetch existing active claims for this stage_id and these claim_types
    existing_claims = _fetch_existing_claims(db_path, stage_id, claim_types)
    
    proposed_changes = []
    today = date.today().isoformat()
    
    for cand in candidates:
        cand_type = cand["claim_type"]
        cand_scope = cand["claim_scope"]
        relevant_existing = existing_claims.get((cand_scope, cand_type), [])
        
        # Fast path: if no existing claims in this scope/type, it's definitely novel.
        if not relevant_existing:
            proposed_changes.append({
                "candidate_id": cand["claim_id"],
                "classification": "novel",
                "action": "INSERT",
                "claim_data": cand,
                "rationale": "No existing claims in this scope/type."
            })
            continue
            
        # 3. Ask LLM to classify against relevant existing claims
        classification_result = _classify_candidate(cand, relevant_existing)
        
        c_class = classification_result.get("classification", "novel")
        target_id = classification_result.get("target_claim_id")
        rationale = classification_result.get("rationale", "")
        
        if c_class == "corroborating" and target_id:
            proposed_changes.append({
                "candidate_id": cand["claim_id"],
                "classification": "corroborating",
                "action": "UPDATE",
                "target_claim_id": target_id,
                "changes": {"last_verified": today},
                "rationale": rationale,
                "source_data": {
                    "source_url": cand["source_url"],
                    "source_tier_vocab": cand["source_tier_vocab"],
                    "source_tier_value": cand["source_tier_value"],
                    "source_date": cand.get("source_date", today)
                }
            })
        elif c_class == "contradicting" and target_id:
            proposed_changes.append({
                "candidate_id": cand["claim_id"],
                "classification": "contradicting",
                "action": "FLAG_FOR_REVIEW",
                "target_claim_id": target_id,
                "rationale": rationale,
                "candidate_statement": cand["statement"]
            })
        else:
            proposed_changes.append({
                "candidate_id": cand["claim_id"],
                "classification": "novel",
                "action": "INSERT",
                "claim_data": cand,
                "rationale": rationale
            })

    return {
        "run_id": run_id,
        "stage_id": stage_id,
        "proposed_changes": proposed_changes
    }

def _fetch_existing_claims(db_path: str, stage_id: str, claim_types: list[str]) -> dict[tuple[str, str], list[dict]]:
    """
    Returns existing claims grouped by (claim_scope, claim_type).
    Only fetches active claims.
    """
    if not claim_types:
        return {}
        
    conn = get_connection(db_path)
    placeholders = ",".join("?" for _ in claim_types)
    query = f"""
        SELECT claim_id, claim_scope, claim_type, statement, confidence 
        FROM claims 
        WHERE stage_id = ? AND status = 'active' AND claim_type IN ({placeholders})
    """
    params = [stage_id] + claim_types
    rows = conn.execute(query, params).fetchall()
        
    grouped = {}
    for r in rows:
        key = (r["claim_scope"], r["claim_type"])
        grouped.setdefault(key, []).append(dict(r))
    return grouped

def _classify_candidate(candidate: dict, existing_claims: list[dict]) -> dict:
    """
    Use LLM to classify a single candidate against existing claims.
    Returns the parsed JSON response.
    """
    existing_text = ""
    for c in existing_claims:
        existing_text += f"- [{c['claim_id']}] {c['statement']}\n"
        
    prompt = f"""NEW CANDIDATE CLAIM:
"{candidate['statement']}"

EXISTING CLAIMS:
{existing_text}

Analyze the new candidate against the existing claims and output the JSON classification.
Make sure to respond with ONLY valid JSON, no markdown formatting.
"""

    try:
        response_text = providers.complete(prompt, system=DIFF_SYSTEM_PROMPT)
        # Clean up any potential markdown fences (e.g. ```json ... ```)
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        return json.loads(cleaned.strip())
    except Exception as e:
        logger.warning(f"Failed to classify candidate {candidate['claim_id']}: {e}")
        # Default to novel on failure so it still gets reviewed
        return {"classification": "novel", "target_claim_id": None, "rationale": f"LLM Failure: {e}"}
