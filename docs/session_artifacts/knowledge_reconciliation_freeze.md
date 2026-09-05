# CITEABLE — KNOWLEDGE RECONCILIATION & TAXONOMY FREEZE

## 1. Corpus Definition

The conceptual knowledge corpus being reconciled includes:
* **The Master Knowledge Base (MKB)**: 117 claims across Study A and B.
* **The `areos.db` Claims Table**: 213 active/deprecated domain claims (excluding 4 outcome logs).
* **The `active_claims.json` Build Manifest**: 213 claims (the bridge between MKB and DB).
* **The Python Synthesis Engine**: 36 `REMEDIATION_TEXT` entries, 36 `PRIORITY_SCORES`.
* **The Python Audit Orchestrator**: 12 `ACTION_SNIPPETS`, 6 `MANUAL_CARD_GUIDANCE` entries.
* **The Check Mappings**: 36 `check_code` to `claim_id` bindings.
* **The Latent Tables**: `tool_landscape` (8 rows), `policy_constraints` (4 rows).
* **The MKB Source Directory**: 107 primary source records.

**Excluded from Conceptual Knowledge:**
* Claims `C325–C328` (Outcome logger records) are excluded because they are operational application data (logs), not domain knowledge.
* Claims `M001–M006` are excluded because they are internal research process notes regarding how the LLMs behaved during the study, not facts about the SEO/AEO domain.

---

## 2. Number Reconciliation

The discrepancies in the previous census are resolved as follows:

* **117 vs 213 vs 217 claims:** The MKB originally contained 117 claims. During a later ingestion pass (`active_claims.json` built on 2026-08-10), an additional 96 technical explainer claims (the `C200–C324` series) were merged into the corpus, raising the true total to 213. Four operational logs were appended later, resulting in the 217 physical DB rows.
* **36 checks → 6 claims vs 12 claims:** 36 checks map to 12 *distinct* claim IDs total. However, the vast majority of checks (30 of 36) cluster around just 6 "heavyweight" claims (`C050`, `C051`, `C054`, `C057`, `C058`, `C061`). The remaining 6 checks map 1-to-1 to 6 minor claims (`C071`, `C073`, `C284`, `C292`, `C293`, `C310`).
* **~90 vs ~55–130 distinct concepts:** There are ~450 physical representations. When we collapse semantic duplicates (e.g., the 35 places crawler access is mentioned), we reach ~88 distinct, independent underlying domain ideas.

### The True Numbers
* **Raw physical representations:** ~450
* **Unique identifiers (Claims + Checks):** ~250
* **Distinct knowledge concepts:** ~88
* **Runtime-linked knowledge concepts:** 12
* **Latent knowledge concepts:** ~76

---

## 3. AEOG Taxonomy Reconstruction

We currently possess two overlapping taxonomy systems:

* **`STAGE-01` through `STAGE-22`:** The original **Technical Execution Taxonomy**. Originating from early engineering specifications (`issues_stage_01.json`), these represent discrete, linear micro-operations in a crawler pipeline (e.g., URL discovery, schema parsing, headless rendering).
* **`AP-01` through `AP-10`:** The **Business Reporting Taxonomy**. Originating from the Master Knowledge Base synthesis, these represent human-readable consulting phases presented to a client (e.g., Business Scoping, Authority & Backlinks).

**What happened:** The application was built on the `STAGE-` technical pipeline. Later, the knowledge base was migrated to the `AP-` business phases. The two were never reconciled, leaving a broken data model where `check_code_mappings` implicitly expects `STAGE-` logic, but the claims themselves declare `stage_id = 'AP-03'`. 

**Canonical Taxonomy Recommendation (Do not implement yet):**
The two systems represent different abstraction levels and should be **nested, not merged or replaced**. 
* `AP-` phases are the parent *Reporting Categories*.
* `STAGE-` items are the child *Execution Steps*.
* Example: `AP-03 (Content Extractability)` contains `STAGE-12 (Schema Parsing)` and `STAGE-14 (JS Rendering)`.

---

## 4. Master Knowledge Cluster Inventory (Example Clusters)

*A full matrix is provided in Section 16.*

**KNOWLEDGE CLUSTER K-001**
**Underlying concept:** AI crawlers must not be blocked by robots.txt or server-level directives.
**Representations:**
- MKB Study A: `CLM-019`, `CLM-023`
- MKB Study B: `C011`, `C012`, `C014`
- DB claim: `C050`
- DB claims (technical facts): `C210`, `C211`
- Check codes: `CRAWLER_FULLY_BLOCKED`, `CRAWLER_PARTIAL`, `CRAWLER_ALLOWED`, `NO_DIRECTIVE`, `GPTBOT_MISSING`, `GOOGLE_EXTENDED_MISSING`, `INVALID_CRAWL_DELAY`
- Python remediation: `REMEDIATION_TEXT` (7 distinct strings)
- Python snippet: `ACTION_SNIPPETS['CRAWLER_FULLY_BLOCKED']`

**KNOWLEDGE CLUSTER K-002**
**Underlying concept:** Well-structured JSON-LD schema is required for AI retrieval comprehension.
**Representations:**
- MKB Study A: `CLM-004`, `CLM-005`
- DB claim: `C054`
- DB claims (technical facts): `C230`, `C231`
- Check codes: `JSON_PARSE_FAILURE`, `MISSING_TYPE`, `MISSING_REQUIRED_FIELD`
- Python remediation: `REMEDIATION_TEXT` (3 strings)
- Python snippet: `ACTION_SNIPPETS['MISSING_REQUIRED_FIELD']`

---

## 5. Knowledge Type Taxonomy

The corpus naturally breaks down into these distinct categories:
1. **Factual Technical Behavior:** How an AI engine actually parses HTML/JS (e.g., `C200` series).
2. **Standard/Requirement:** A binary pass/fail condition (e.g., robots.txt must allow GPTBot).
3. **Remediation Guidance:** How to fix a violation (Python `ACTION_SNIPPETS`).
4. **Empirical Observation:** Statistical correlations (e.g., `CLM-054` ranking factors).
5. **Process/Workflow Knowledge:** How to conduct an audit (e.g., `AP-01` scoping claims).
6. **Tool/Landscape Information:** Competitor tools (`tool_landscape` table).
7. **Legal/Policy Information:** Terms of service (`policy_constraints` table).

---

## 6. Knowledge Atomicity

The DB claims are generally **atomic** (one assertion per record).
However, the Python `REMEDIATION_TEXT` strings are **compound**. 

A single Python `REMEDIATION_TEXT` string currently contains:
`[Symptom Statement] + [Underlying Principle] + [Business Impact] + [High-Level Fix]`

Because these components are physically concatenated in Python rather than relationally composed, the system cannot reuse the "Underlying Principle" text without also importing the specific "Symptom Statement."

---

## 7. Duplication Analysis

* **Level 1 (Record duplication):** Very low. The DB has no identical `statement` strings. 
* **Level 2 (Semantic duplication):** Massive. The idea that "crawlers need access" is stated in 13 slightly different ways across Study A, Study B, and the C-series explainers.
* **Level 3 (Functional duplication):** Massive. The Python `REMEDIATION_TEXT` serves the exact same product function as the DB `statement` strings — explaining to the user why an issue matters. Currently, the application ignores the DB text entirely and prints the Python text.

---

## 8. Knowledge Variants

Not all similar claims are duplicates. 
* **Distinct Technologies:** A claim about `llms.txt` and a claim about `robots.txt` both relate to "bot access," but they are distinctly different technologies requiring different clusters.
* **Distinct Confidences:** MKB `CLM-010` says structured data *does* increase citation. `CLM-015` says structured data *does not* increase citation. These are not duplicates; they are a **contradiction cluster** representing a contested frontier in the domain.

---

## 9. Master KB → Database Lineage

**Master Knowledge Base** (117 claims)
↓
*Transformation:* 96 new technical claims (`C200–C324`) added by engineers. Sources directory dropped. Status/confidence metadata flattened to "active/high" via the `active_claims.json` builder.
↓
**Database** (213 claims)
↓
*Transformation:* The application runtime completely bypasses the DB claims for remediation text.
↓
**Runtime** (0 DB claims actively printed to reports).

**Result:** The Database is a rich, latent archive. It does not power the actual product text.

---

## 10. Database → Python Lineage

For the 12 active clusters:
* **DB:** Contains the provenance, source URLs, and original LLM synthesis context.
* **Python (`synthesis_engine.py`):** Contains the actual client-facing explanation text.
* **Python (`audit_orchestrator.py`):** Contains the exact code snippets needed to implement the fix.

**Neither is complete.** To generate a perfect finding, Citeable needs the DB's provenance, the synthesis engine's explanation, and the orchestrator's code snippet.

---

## 11. Provenance Census

* **MKB:** 107 primary source definitions (Name, Tier, Context).
* **DB `claims`:** 217 raw URL strings. No titles, no tiers, no context.
* **Python:** 0 provenance.

**Provenance is attached at the representation level, not the concept level.** Because of semantic duplication, Cluster K-001 (Crawlers) has 14 different URLs attached to 14 different representations of the exact same concept. 

---

## 12. AEOG Coverage

* **AP-01 (Scoping):** ~10 concepts. All latent.
* **AP-02 (Schema):** ~15 concepts. 2 runtime-linked.
* **AP-03 (Extractability):** ~30 concepts. 5 runtime-linked. Heavy semantic duplication.
* **AP-04 (Authority):** ~5 concepts. 3 runtime-linked. Weak knowledge base.
* **AP-05 (Citation):** ~10 concepts. 2 runtime-linked. 
* **AP-08, 09, 10 (Legal, Tools, Planning):** ~15 concepts. All latent.

---

## 13. Runtime vs Latent Knowledge

* **Knowledge that exists:** ~88 distinct concepts.
* **Knowledge Citeable actually uses:** 12 distinct concepts (powering 36 checks).
* **Knowledge that exists but is not productized:** ~76 distinct concepts.

---

## 14. Knowledge Boundary

**Inside the Domain Knowledge boundary:**
* Technical facts (how bots parse JS).
* Standards (robots.txt syntax).
* Empirical correlations (schema vs citation rates).
* Remediation tactics.

**Outside the Domain Knowledge boundary:**
* Audit workflow steps (AP-01 stakeholder interviews).
* Internal process notes (M001-M006).
* Tool vendor pricing (`tool_landscape`).
* Outcome logs (`C325`).

---

## 15. Knowledge Maturity

* **A — Strong Candidate:** The 12 active clusters (Crawlers, Schema, Extractability, Authority).
* **B — Needs Verification:** The `llms.txt` claims (contradicted internally).
* **C — Requires Reconciliation:** `CLM-050` / `CLM-052` (does schema actually improve rank?).
* **D — Historical:** Outcome logs.
* **F — Duplicate:** The vast majority of the `C200` series overlaps with the MKB.

---

## 16. Master Knowledge Matrix (Top 10 Active Clusters)

| Cluster ID | Underlying Knowledge | Knowledge Type | AEOG | Representations | Runtime Status | Duplication | Maturity |
|---|---|---|---|---|---|---|---|
| **K-01** | AI crawler access | Standard | AP-03 | 14 DB, 9 Py | **Active** (9 checks) | Severe | A |
| **K-02** | `llms.txt` presence | Standard | AP-03 | 3 DB, 6 Py | **Active** (5 checks) | Moderate | B |
| **K-03** | JSON-LD syntax | Standard | AP-02 | 8 DB, 6 Py | **Active** (6 checks) | Moderate | A |
| **K-04** | HTML list/table formatting | Tech Fact | AP-03 | 3 DB, 1 Py | **Active** (1 check) | Low | A |
| **K-05** | JS/Iframe blocking | Tech Fact | AP-03 | 6 DB, 3 Py | **Active** (3 checks) | Moderate | A |
| **K-06** | Answer near top (Inverted pyramid) | Rec | AP-03 | 2 DB, 1 Py | **Active** (1 check) | Low | A |
| **K-07** | Citation generation triggers | Empirical | AP-05 | 12 DB, 2 Py | **Active** (2 checks) | Severe | C |
| **K-08** | Wikipedia entity presence | Empirical | AP-04 | 2 DB, 1 Py | **Active** (1 check) | Low | A |
| **K-09** | Domain Authority / Links | Empirical | AP-04 | 4 DB, 2 Py | **Active** (2 checks) | Moderate | A |
| **K-10** | `nosnippet` directives | Standard | AP-03 | 2 DB, 1 Py | **Active** (1 check) | Low | A |

---

## 17. Knowledge Lineage Map

```text
ORIGIN (LLM Synthesis & Engineering Specs)
 ↓
MASTER KB (117 claims, 107 sources)
 ↓
JSON BUILD PROCESS (Adds 96 C-series claims, drops sources, flattens metadata)
 ↓
DATABASE CLAIMS (213 rows, latent archive, acts as ID anchors)
 ↓
CHECK CODE MAPPINGS (Binds 36 checks to 12 DB claim IDs)
 ↓
PYTHON DICTIONARIES (Provides the actual text and code snippets bypassing DB)
 ↓
RUNTIME USE (Final PDF/UI reports driven strictly by Python strings)
```

---

## 18. Duplication Map (Example: The Crawler Redundancy)

```text
Underlying concept: "Bots need access"
├── Master KB representation: CLM-019, CLM-023, C011, C012
├── DB claim representation: C050 (anchor), C210, C211, C214
├── Python Remediation: 
│   ├── REMEDIATION_TEXT['CRAWLER_FULLY_BLOCKED']
│   ├── REMEDIATION_TEXT['CRAWLER_PARTIAL']
│   ├── REMEDIATION_TEXT['NO_DIRECTIVE']
│   └── (6 others)
└── Runtime outcome: All point back to C050 in reports, but use 9 different Python strings.
```
*Estimated Representational Duplication:* **60-70% of the corpus.**

---

## 19. Knowledge Gap Map

* **Missing completely:** Any runtime checks for JavaScript rendering timeout failures, multi-engine citation disparity, or canonicalization chains.
* **Weakly represented:** Domain authority link-building tactics.
* **Contradicted/Unverified:** `llms.txt` efficacy; Google Terms of Service enforcement teeth; Structured data's direct impact on citation volume vs entity disambiguation.
* **Missing provenance:** The entire `C200–C324` technical explainer series lacks specific passage quotes or identified origin documents. 

---

## 20. Final Known-Universe Estimate

**How many genuinely distinct domain knowledge concepts does Citeable currently possess?**

* **Conservative count: ~45.** (The 12 active concepts, plus the highly verified crawler/schema technical standards in the DB).
* **Best estimate: ~88.** (Collapsing all semantic duplication across the MKB and C-series, excluding pure operational logs and tool pricing data).
* **Upper bound: ~120.** (If every nuanced variant of a crawler behavior or semantic markup claim is treated as a distinct concept).

*The variance is entirely driven by how granularly we define a "concept" (e.g., is "missing @type" a separate concept from "missing required field", or are they both "schema validity"?).*

---

## 21. Future Web Research Queue
*(Do not act on this yet)*
1. Verify the current industry consensus on `llms.txt` efficacy (resolving C016 contradiction).
2. Retrieve the July 2026 court ruling on SerpApi vs Google regarding consumer ToS.
3. Validate the `C200` series technical claims against current Google Search Central docs.

## 22. Remaining Unknowns
* The physical origin document for the `C200–C324` series before it was merged into `active_claims.json`.
* Whether any client has ever seen the `AP-01` through `AP-10` phase descriptions, given they are not printed in standard reports.
