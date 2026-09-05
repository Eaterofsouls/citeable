# Track B: Manual Review Redesign & API Spec

## 1. Database Schema Changes

### `manual_observations` Table

```sql
CREATE TABLE IF NOT EXISTS manual_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    structured_data TEXT NOT NULL, -- JSON storing the exact answers
    severity TEXT NOT NULL,        -- error/warning/info
    diagnosis_text TEXT,           -- the human written rationale/notes
    submitted_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_manual_observations_run ON manual_observations (run_id);
```

### Migration Path & Backward Compatibility
- **Existing `manual_verdicts` table**: Retained as-is for backward compatibility.
- **Backward compatibility**: Old runs will continue to load their verdicts from `manual_verdicts`. 
- **Migration**: New runs will populate and load from `manual_observations`. The API layer (`GET /api/v1/audit/runs/{run_id}/full`) will query `manual_observations` first. If empty, it falls back to `manual_verdicts`.

## 2. API Endpoints

### 2.1 `POST /api/v1/audit/runs/{run_id}/observations` (NEW)
**Decorator:** `@router.post("/audit/runs/{run_id}/observations")`
**Function Signature:**
```python
def submit_observation(
    run_id: str,
    observation: ObservationPayload,
    conn=Depends(get_db)
)
```
**Request Schema (`ObservationPayload`):**
```python
class ObservationPayload(BaseModel):
    question_id: str
    maps_to_claims: list[str]
    structured_data: dict
    severity: str
    diagnosis_text: str = ""
```
**Behavior:** UPSERT logic based on `(run_id, question_id)` to allow users to update their answers or resolve concurrent tab issues.

### 2.2 `GET /api/v1/audit/runs/{run_id}/full-report` (NEW)
**Decorator:** `@router.get("/audit/runs/{run_id}/full-report")`
**Function Signature:**
```python
def get_unified_report(run_id: str, conn=Depends(get_db))
```
**Response Schema:** Returns a unified deliverable containing:
- `executive_diagnosis` (Human-authored from D2 + LLM narrative)
- `layer_1_access`, `layer_2_content_schema`, `layer_3_authority_citations`
- `fix_sequence` (Week-by-week action plan)
- `audit_metadata` (Transparency flags)

### 2.3 Existing Endpoints
- **`/verdicts` (POST):** Maintained strictly for older runs.
- **`/synthesize` (POST):** Updated to pull from `manual_observations`. Injects structured observation data (JSON) into `human_review_notes` instead of flat verdict strings.

## 3. UI Implementation

### 3.1 File Modifications
- Modify `areos/ui/guided_review.js`. Do not create a new file; the current architecture successfully wraps the wizard experience.
- Replace `CARD_GUIDANCE` with the 11 new expert-grade questions.

### 3.2 11 Questions & Conditional Logic
- **A1. Prompt Validation:** Pre-audit. Gates the audit findings.
- **B1. Schema Honesty:** Automation-assisted.
- **B2. Content Answerability:** Automation-assisted. (Highest value)
- **B3. Cloaking Intent:** *Conditional* (only if cloaking diff > 0).
- **C1. Brand Accuracy:** Human-only.
- **C2. Content Trustworthiness / E-E-A-T:** Human-only.
- **C3. Citation Framing:** *Conditional* (only if citations > 0).
- **C4. Citation Gap:** *Conditional* (only if citations < max prompts).
- **C5. Speakable:** *Conditional* (only if speakable markup found).
- **D1. llms.txt Content Review:** *Conditional* (only if llms.txt exists).
- **D2. Root Cause Diagnosis:** Synthesis.

### 3.3 Express vs Full Expert Mode
- **Express Mode (~8 mins):** Shows ONLY B2, C1, C2, D2. 
- **Full Expert Mode (~25 mins):** Shows all 11 (minus unsatisfied conditionals).
- State tracked via `window.AreosContext.reviewMode = 'express' | 'full'`. Lock mode upon first submission.

### 3.4 Wizard Progress Calculation
- In `studio.js` (`updateShieldProgress`), `totalWizardCards` must be dynamically computed as `shown_cards` (based on mode + satisfied conditionals), not a static total.
- Progress = `answered / shown`. 

### 3.5 Synthesis Trigger
- Triggers when `completedWizardCards == shown_cards`.
- Calls `triggerPostWizardSynthesis()`, hitting the updated `/synthesize` endpoint with V2 payload logic.

## 4. Synthesis Pipeline Changes

### 4.1 LLM Prompt Addition
In `areos/llm/synthesis_pipeline.py`, append to `_DEFAULT_SYNTHESIZER_PROMPT`:
```python
"9. If a human_diagnosis_text is provided, use it as the opening framing of your "
"narrative. Do not contradict or replace it — expand on it with supporting evidence "
"from the findings.\n"
"10. The structured remediation actions have already been determined. Your job is to "
"explain WHY each action matters, not to invent new actions.\n"
```

### 4.2 Structured Observations
In `_build_synthesizer_input`, format human findings intelligently:
```python
"human_review_notes": f"[HUMAN CONFIRMED] Question: {obs['question_id']} | Severity: {obs['severity']} | Diagnosis: {obs['diagnosis_text']} | Data: {json.dumps(obs['structured_data'])}"
```

### 4.3 Unified Report Layering
The report merges the deterministic recommendation plan (JSON) with the LLM narrative. The LLM narrates the deterministic layer; it does not invent fixes.

## 5. Regression Tests

1. **B1 Data Integrity:** Test `POST /observations` with `question_id="B1_SCHEMA_HONESTY"` stores JSON correctly in `manual_observations` and is retrievable via `GET /full-report`.
2. **Express Mode Trigger:** Verify that in Express Mode, submitting exactly 4 observations triggers `triggerPostWizardSynthesis()` and unlocks the report.
3. **Legacy Fallback:** Ensure `GET /full` on an older `run_id` (with `manual_verdicts` but no `manual_observations`) loads successfully.
4. **Unified Report Assembly:** Verify `/full-report` includes both the deterministic automated findings and the user's explicit `human_diagnosis_text` from D2.

## 6. Gap Hunt (Edge Cases Addressed)

- **Mode Switching:** UI locks the mode (Express/Full) once the first observation is submitted.
- **Incomplete Audit:** Wizard remains locked until automated checks finish (preventing premature reviews).
- **Invalid Conditionals:** If an observation is submitted for an unmet conditional, backend UPSERTs it anyway (preventing data loss) but flags it in metadata as `unexpected_conditional`.
- **Re-runs/Redos:** Handled seamlessly via `(run_id, question_id)` UPSERT logic in the new endpoint.
- **Concurrent Tabs:** UPSERT resolves race conditions (latest submission wins).
- **Zero Observations:** Handled gracefully. If `manual_observations` is empty, report appends a caveat: *"Confidence: Low. No manual qualitative verification performed."*
- **Auth:** New endpoints inherit standard `get_client_keys` and `Depends(get_db)` token auth natively. No architectural changes needed.
