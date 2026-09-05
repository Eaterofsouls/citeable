# Knowledge Architecture Forensic Investigation

## 1. Executive Summary
*   **[CONFIRMED] No Embeddings or Semantic Search:** The system does not utilize vector databases, embeddings, or semantic search. Claims are retrieved deterministically.
*   **[CONFIRMED] Hardcoded Retrieval Map:** Findings are linked to claims entirely via a relational database mapping (`check_code_mappings` table) bridging programmatic error codes (e.g., `JSON_PARSE_FAILURE`) to a specific `claim_id`.
*   **[CONFIRMED] Shadow Knowledge / Decoupled Remediation:** Actual remediation instructions (what to do) and action snippets (how to code it) are hardcoded in Python dictionaries, bypassing the claims database. The database claims serve purely as authoritative citations/justifications for the hardcoded advice.
*   **[CONFIRMED] Deterministic LLM Context:** The LLMs (in Phase 2) do not query the knowledge base. They only see the specific claims passed to them by the deterministic enrichment layer, guaranteeing traceability.

## 2. Architecture Map (ASCII flow diagram of what actually exists)
```text
[ active_claims.json ] --( ingest_claims.py )--> [ SQLite: claims ]
                                                        |
                                                        v (FOREIGN KEY)
[ check_code_mappings.sql ] <------------------ [ check_code_mappings table ]
        |
        v
[ Automated Auditors (Layer 1-5) ]
  |-> Emit check_codes (e.g., CRAWLER_FULLY_BLOCKED)
  |
  v
[ findings_to_claims.py::wire_finding ]
  |-> Maps check_code -> claim_id (via check_code_mappings)
  |-> Looks up claim status/statement from `claims` table
  |-> Returns WiredFinding
  |
  v
[ synthesis_engine.py & audit_orchestrator.py ]
  |-> Appends hardcoded `REMEDIATION_TEXT` and `ACTION_SNIPPETS`
  |-> Prioritizes by hardcoded `PRIORITY_SCORES`
  |-> Outputs RemediationPlan
  |
  v
[ qa_gate.py ]
  |-> Rejects recommendations if claim_id is missing/deprecated/superseded
  |
  v
[ LLM Synthesis Pipeline (synthesis_pipeline.py) ]
  |-> Step 1: Synthesizer (Draft narrative from enriched findings)
  |-> Step 2: Red Teamer (Flags hallucinations/unsupported leaps)
  |-> Step 3: Grounder (Corrects flags against wired claims)
  |
  v
[ Final Report ]
```

## 3. Claim Lifecycle
1.  **Seed:** Claims are defined in `active_claims.json`.
2.  **Ingest:** `areos/db/ingest_claims.py` validates claims via `areos/db/lint.py` and inserts them into the `claims` SQLite table. It also populates the `check_code_mappings` table.
3.  **Retrieval:** The claim waits passively. There is no active retrieval mechanism that scans the knowledge base.
4.  **Trigger:** An auditor encounters a failure and emits a specific string `check_code`.
5.  **Wiring:** `findings_to_claims.py` matches the `check_code` to a `claim_id` using the `check_code_mappings` DB table.
6.  **Use:** The `claim_statement` is attached to a `Recommendation` alongside hardcoded remediation text. The `qa_gate.py` ensures the claim is valid, and the LLM uses the statement as grounding context for narrative synthesis.

## 4. Claim ID Lifecycle
*   **`active_claims.json`**: Initial source of `claim_id`.
*   **`claims` table**: Serves as the Primary Key.
*   **`check_code_mappings`**: Serves as a Foreign Key to link a programmatic `check_code` to a `claim_id`.
*   **`WiredFinding` / `Recommendation`**: Carried as an attribute in memory.
*   **`qa_gate.py`**: Checks if the `claim_id` exists in the DB and has an `active` status. Rejects otherwise.
*   **`synthesis_pipeline.py`**: The Red Teamer LLM checks for `HALLUCINATED_CLAIM` violations by verifying if any `claim_id` in the generated text was not present in the input list.

## 5. Embedding Architecture
*   **[CONFIRMED]** Embedding architecture **does not exist**.
*   A `grep_search` across the codebase for `embedding`, `vector`, `cosine`, `similarity`, `faiss`, `chroma`, `pinecone`, `weaviate`, `pgvector`, and `sentence_transformer` returned zero results.
*   The system uses a purely relational, deterministic lookup.

## 6. Retrieval Architecture
*   **[CONFIRMED]** Retrieval is completely deterministic and relational.
*   Claims are "retrieved" strictly by joining an auditor's `check_code` to `check_code_mappings.claim_id`, and then to `claims.claim_id`.
*   There is no semantic search, keyword search, or dynamic relevancy scoring.

## 7. Claim → Finding
*   **[CONFIRMED]** Mechanism resides in `areos/auditors/findings_to_claims.py` via `wire_finding()`.
*   The function queries the `check_code_mappings` table using the `check_code`.
*   It takes the candidate `claim_id`, looks it up in the `claims` table to get the `status`, `confidence`, `statement`, and `claim_scope`, and packages it into a `WiredFinding`.

## 8. Claim → Remediation
*   **[CONFIRMED]** Actual remediation advice is decoupled from the claim statement.
*   `areos/auditors/synthesis_engine.py` builds recommendations by mapping the `check_code` to a hardcoded Python dictionary `REMEDIATION_TEXT`.
*   `areos/auditors/audit_orchestrator.py` further maps the `check_code` to a hardcoded dictionary `ACTION_SNIPPETS` for code-level advice.
*   The `claim_statement` from the DB is appended strictly as the "Governing claim" to act as an authoritative citation, but the system doesn't "derive" the fix from the claim.

## 9. LLM Context Flow
*   **[CONFIRMED]** The LLMs do not query the database.
*   **Step 1 (Synthesizer):** Receives a JSON dump of `enriched_recs` containing the triggered `check_code`, `claim_id`, `claim_statement`, `evidence_label`, and hardcoded `description`. It drafts a narrative based *only* on this JSON.
*   **Step 2 (Red Teamer):** Receives the Draft Narrative and the exact list of `claim_ids`. It flags unsupported leaps, fabricated stats, or hallucinated claims.
*   **Step 3 (Grounder):** Receives the Draft Narrative, the original `enriched_recs` context, and the Red Teamer flags. It rewrites the narrative to resolve flags.

## 10. Data Model
*   **`claims`**: `claim_id` (PK), `stage_id`, `claim_scope`, `claim_type`, `statement`, `status`, `confidence`, `source_url`, `source_tier_vocab`, `source_tier_value`, `source_date`, `last_verified`, `superseded_by`, `is_client_evidence` (computed).
*   **`check_code_mappings`**: `mapping_id` (PK), `check_code`, `claim_id` (FK to claims).
*   **Other key tables**: `audit_runs`, `findings`, `sources`, `claim_sources`.

## 11. Retrieval Logic
*   **[CONFIRMED]** No dynamic retrieval logic (no scoring, thresholds, filters, or top-K).
*   A `check_code` maps deterministically to a `claim_id`. If mapped, it is fetched. If not mapped, it's marked `UNMAPPED` and subsequently rejected by the QA gate.

## 12. Synchronization / Consistency
*   **[CONFIRMED]** There is a high risk of inconsistency (drift) between claims and remediations.
*   Because the actual advice is hardcoded in Python dictionaries (`REMEDIATION_TEXT`, `ACTION_SNIPPETS`), updating a claim in the database will not update the practical advice given to the user unless the codebase is also modified.

## 13. Shadow / Bypass Knowledge
*   **[CONFIRMED]** The system heavily relies on shadow knowledge that bypasses the claims DB.
*   `areos/auditors/synthesis_engine.py`: Contains `PRIORITY_SCORES`, `REMEDIATION_TEXT`, and `MANUAL_REMEDIATION_TEXT`.
*   `areos/auditors/audit_orchestrator.py`: Contains `ACTION_SNIPPETS` and `MANUAL_CARD_GUIDANCE`.
*   This hardcoded logic is responsible for prioritizing, formatting, and dictating the fix, meaning the system's true intelligence is largely in these Python files rather than the knowledge base.

## 14. Real Claim Traces
A live query was executed on `areos.db` for the requested claims:
*   **C001, C016, C019**: `[CONFIRMED]` These exist in the `claims` table as active `automatability_rating` claims. However, they are **not present** in `check_code_mappings`. Consequently, they can never be triggered or cited by an automated finding.
*   **CLM-001**: `[CONFIRMED]` Exists in the `claims` table as an active `serp-feature` claim. It is **not mapped** in `check_code_mappings`, meaning it is unreachable by the automated auditing pipeline.
*   **M002**: `[CONFIRMED]` Exists in the `claims` table, but its status is **deprecated**. It is **not mapped** in `check_code_mappings`. Even if it were manually triggered, `qa_gate.py` would instantly reject it because of its deprecated status.

## 15. Technical Control Points
*   **[CONFIRMED] What uses claims:** `findings_to_claims.py` (reads the DB for citations), `synthesis_engine.py` (adds the statement to the recommendation plan), `qa_gate.py` (validates existence/status), `synthesis_pipeline.py` (passes statements to LLM).
*   **[CONFIRMED] What doesn't use claims:** Core audit logic (auditor scripts), Remediation instructions (`REMEDIATION_TEXT`), Code snippets (`ACTION_SNIPPETS`), Prioritization logic (`PRIORITY_SCORES`).

## 16. Unknowns
*   **[UNKNOWN]** What is the intended purpose of unmapped claims (like `C001`, `C016`, `C019`, `CLM-001`)? Since there's no semantic search and they aren't mapped to check codes, they currently serve no functional purpose in the audit pipeline.
*   **[UNKNOWN]** Are manual findings (`MANUAL_REMEDIATION_TEXT` in `C052`-`C090`) supposed to be backed by corresponding DB claims? Currently, they use their card IDs (e.g. `C052`) as the `claim_id` proxy.

## 17. Stage 2 Investigation Candidates
*   **Refactor Shadow Knowledge:** Migrate `REMEDIATION_TEXT` and `ACTION_SNIPPETS` out of Python dictionaries and into the SQLite database (perhaps a new `remediation_guidance` table linked to `claims`), enforcing a single source of truth.
*   **Investigate Unmapped Claims:** Determine whether unmapped claims should be tied to new check codes, or if a different retrieval mechanism (like semantic search) was intended for general knowledge queries outside the audit pipeline.
