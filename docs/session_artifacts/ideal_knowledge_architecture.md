# Ideal Knowledge Architecture for Citeable
**Document Status:** Stage 3A Architectural Recommendation
**Target Audience:** Senior Engineering Team
**Objective:** Define the ideal knowledge architecture that decouples logic from data, ensures traceability, and provides highly reusable, evidence-backed knowledge components.

---

## 1. Design Principles

The following principles must constrain every architectural decision moving forward. They are derived from the pain points identified in the Stage 1 and Stage 2 audits of the Citeable codebase.

*   **Principle 1: Atomicity of Knowledge**
    *   **CONFIRMED**: Current claims are "MIXED" monoliths containing principle, rationale, process note, and implementation hint.
    *   **Rule**: Knowledge must be broken down into atomic entities. A principle is just a principle. Evidence is just evidence. Remediation is just remediation. They are linked, not conflated.
*   **Principle 2: Separation of Knowledge and Behavior**
    *   **CONFIRMED**: `REMEDIATION_TEXT` and `ACTION_SNIPPETS` are hardcoded in Python.
    *   **Rule**: Application logic (Python) must never contain knowledge. The application should only contain the *engine* that retrieves and applies knowledge from the database.
*   **Principle 3: Unambiguous Traceability**
    *   **STRONGLY INFERRED**: The current system cannot easily prove *why* a specific code snippet was recommended for a specific check.
    *   **Rule**: The system must provide a deterministic graph path: `Audit Finding → Check Rule → Principle → Evidence → Source → Remediation Guidance → Implementation Technique`.
*   **Principle 4: Reuse Over Duplication**
    *   **CONFIRMED**: Multiple check codes map to similar underlying concepts, but knowledge is siloed or duplicated.
    *   **Rule**: A `Principle` or `Remediation` must exist exactly once. Many `Check Rules` can map to the same `Principle`. Many `Principles` can map to the same `Remediation`.
*   **Principle 5: Immutable Provenance**
    *   **CONFIRMED**: The origin of claims (LLM vs. Human vs. Authoritative) is currently tracked loosely or lost.
    *   **Rule**: Every assertion in the system must point to its origin, and that origin must have an explicit confidence/authority tier.
*   **Principle 6: Strict LLM Boundaries**
    *   **STRONGLY INFERRED**: The LLM is currently trusted to synthesize raw check data with overloaded claim strings, risking hallucination.
    *   **Rule**: The LLM is a reasoning and formatting engine, not a database. It must only synthesize explicitly provided context and must be prohibited from inventing citations, URLs, or technical parameters.

---

## 2. What Citeable Actually Needs to Know

Working backwards from the desired product output—a trustworthy, cited remediation plan—Citeable needs a highly specific graph of information.

To produce **one** trustworthy remediation with citations, the system must know:

1.  **The Trigger**: What specific technical condition was detected in the audit? (e.g., "robots.txt contains Disallow: / for Googlebot-News")
2.  **The Standard**: What is the authoritative rule being violated? (e.g., "AI crawlers must be explicitly allowed or handled via specific directives.")
3.  **The Rationale (The "Why")**: Why does this standard matter to the user's business? (e.g., "Blocking AI crawlers prevents inclusion in generative search summaries, reducing organic visibility.")
4.  **The Evidence**: What exact text from what exact authoritative source proves this standard and rationale? (e.g., Quote from Google Search Central documentation).
5.  **The Source**: Where did this evidence come from? (e.g., URL, Author, Date).
6.  **The Strategy (The "What")**: What is the general approach to fixing this? (e.g., "Update robots.txt to allow the specific user-agent.")
7.  **The Tactics (The "How")**: What is the exact implementation for the user's tech stack? (e.g., Nginx config snippet, Next.js `robots.txt` generation code).

**CONFIRMED**: The current system attempts to jam 2, 3, 4, 6, and 7 into a single `claims` table record and a handful of Python dictionaries. This must end.

---

## 3. Ideal Conceptual Knowledge Model

We must replace the overloaded "Claim" with a precise, relational entity model.

### 3.1 Entities to KEEP and REFINE

#### **Entity: Principle** (Replaces the concept of "Claim")
*   **Represents**: A single, immutable, vendor-agnostic truth about the domain (e.g., Search, AI extraction).
*   **Why distinct**: Principles are universal. They apply regardless of the specific technology stack or the specific tool used to audit the site.
*   **Inside**: `id`, `statement` (short, atomic truth), `rationale` (business impact explanation).
*   **Not inside**: Remediation instructions, code snippets, specific tool check codes, URLs.

#### **Entity: Source**
*   **Represents**: An external authoritative document or entity.
*   **Why distinct**: Multiple pieces of evidence can be drawn from a single source. Updating a source's status (e.g., deprecated by Google) should flag all related evidence.
*   **Inside**: `id`, `url`, `title`, `author_type` (e.g., Search Engine, Industry Standard), `authority_tier` (1-5), `last_verified_date`.

#### **Entity: Evidence**
*   **Represents**: A specific extraction (quote) from a Source that grounds a Principle.
*   **Why distinct**: A Principle might be backed by Google (Source A) and Bing (Source B). We need exact quotes to prove the Principle.
*   **Inside**: `id`, `source_id`, `principle_id`, `exact_quote`, `page_section`.

#### **Entity: Check Rule**
*   **Represents**: The deterministic signature detected by the auditing engine.
*   **Why distinct**: The audit engine's vocabulary changes. A crawler might detect "CRAWLER_BLOCKED_ROBOTS" today and "ROBOTS_TXT_DISALLOW" tomorrow. The knowledge graph should not care.
*   **Inside**: `id`, `check_code`, `engine_version`.

#### **Entity: Remediation Guidance**
*   **Represents**: The strategic approach to fixing a violation of a Principle.
*   **Why distinct**: The strategy (e.g., "Implement Schema.org JSON-LD") is different from the tactic (e.g., "Here is the React component for it").
*   **Inside**: `id`, `strategy_description`.

#### **Entity: Implementation Technique**
*   **Represents**: The tactical, code-level execution of a Remediation Guidance for a specific context.
*   **Why distinct**: Keeps the knowledge base DRY. One Remediation can have techniques for React, Vue, WordPress, Nginx, etc.
*   **Inside**: `id`, `remediation_guidance_id`, `context_tags` (e.g., ['react', 'nextjs']), `code_snippet`.

### 3.2 Entities to REJECT

*   **Entity: Finding (Rejected)**
    *   *Reason*: A finding is an *event* (Audit X found Issue Y on Site Z). It belongs in the transactional database, not the knowledge base.
*   **Entity: Priority/Risk (Rejected as an Entity)**
    *   *Reason*: Priority is a calculation (`Severity x Impact x Confidence`), not a static piece of knowledge. It should be computed at runtime based on the finding context and the Principle's severity attribute.
*   **Entity: Process Notes (Rejected)**
    *   *Reason*: Items like M001-M006 are internal methodology notes, not domain knowledge. They belong in developer documentation or a separate `system_meta` table, never in the knowledge retrieval path.

---

## 4. Ideal Knowledge Graph

The following ASCII diagram illustrates the core entity relationships and cardinalities.

```ascii
+------------------+       +-------------------+       +-----------------------+
|  Audit Engine    |       |  Knowledge Base   |       |  External Authority   |
+------------------+       +-------------------+       +-----------------------+
        |                            |                             |
        v                            v                             v
+------------------+       +-------------------+       +-----------------------+
|   Check Rule     |       |    Principle      |<------|      Evidence         |
| (e.g., CRAWLER_  |*-----*| (Atomic domain    |1     *| (Exact quote backing  |
|  BLOCKED)        |       |  truth)           |       |  the principle)       |
+------------------+       +-------------------+       +-----------------------+
                                     |                             |*
                                     |                             |1
                                     |                     +-------------------+
                                     |                     |      Source       |
                                     |                     | (URL, tier, date) |
                                     |                     +-------------------+
                                     v
                           +-------------------+
                           | Remediation       |
                           | Guidance          |
                           | (Strategic fix)   |
                           +-------------------+
                                     |1
                                     |
                                     |*
                           +-------------------+
                           | Implementation    |
                           | Technique         |
                           | (Code, Context)   |
                           +-------------------+
```

**Cardinalities Defined:**
*   `Check Rule` to `Principle`: **Many-to-Many (0..*)**. Multiple checks (e.g., missing canonical, wrong canonical) map to one Principle (Canonicalization). One complex check might violate multiple Principles.
*   `Principle` to `Evidence`: **One-to-Many (1..*)**. A Principle MUST have at least one Evidence record to be VERIFIED.
*   `Evidence` to `Source`: **Many-to-One (*..1)**. A Source can provide many pieces of Evidence.
*   `Principle` to `Remediation Guidance`: **Many-to-Many (0..*)**. A Principle can have multiple valid fix strategies.
*   `Remediation Guidance` to `Implementation Technique`: **One-to-Many (1..*)**. A strategy has multiple platform-specific executions.

---

## 5. Claims: Keep, Redefine, or Replace?

**Recommendation: REPLACE the current "Claim" concept with "Principle".**

**CONFIRMED**: The current corpus of 213 claims is fundamentally broken. They are "MIXED" entities. For example, a single claim currently holds: "Google prioritizes fast sites (Principle) because users bounce (Rationale), so you should use a CDN (Guidance) and here is how to configure Cloudflare (Implementation)."

This structure is anti-architectural. It prevents reusing the Cloudflare implementation for a different performance check. It prevents citing the exact Google documentation for just the principle.

*   The word "Claim" implies something unverified. Citeable needs a foundation of "Principles."
*   We must systematically dismantle the 213 claims. The declarative part becomes a `Principle`. The "how-to" part becomes `Remediation Guidance`. The code snippets become `Implementation Techniques`.

---

## 6. Evidence & Provenance Architecture

To guarantee trust and answer "Why does Citeable believe this?", we must institute a rigorous provenance model.

**The Source Record:**
*   `authority_tier`:
    *   Tier 1: Primary Engine Docs (Google Search Central, OpenAI crawler docs).
    *   Tier 2: Recognized Industry Standards (Schema.org, W3C).
    *   Tier 3: Highly trusted secondary research (Ahrefs, Moz data studies).
    *   Tier 4: LLM Synthesized / Heuristic (must be flagged clearly to users).

**The Evidence Record:**
*   `extraction_method`: Was this quote pulled by a human (`MANUAL`), a deterministic script (`SCRAPER`), or an LLM (`LLM_EXTRACTED`)?
*   `confidence_score`: 0.0 to 1.0 based on the tier of the source and the extraction method.

**Provenance Preservation:**
When the system generates a report, it does not just say "Google says X." It traverses the graph:
`Principle (ID: 12) ← Evidence (ID: 45) ← Source (ID: 8, Tier 1, URL)`.
The citations presented to the user are deterministically generated from this graph, never hallucinated by the LLM.

---

## 7. Remediation Architecture

**CONFIRMED**: Currently, `REMEDIATION_TEXT` (guidance) and `ACTION_SNIPPETS` (technique) are hardcoded in `synthesis_engine.py` and `audit_orchestrator.py`.

**The Ideal Architecture separates the "What" from the "How".**

1.  **Remediation Guidance (The "What"):** Lives in the database. Connected to Principles. Examples: "Implement comprehensive Schema.org markup," "Configure robots.txt to allow AI bots."
2.  **Implementation Technique (The "How"):** Lives in the database, linked to Guidance. Contains:
    *   `context_tags`: `['wordpress', 'yoast']` or `['nextjs', 'app-router']`.
    *   `snippet_type`: `code`, `config`, `ui_instruction`.
    *   `content`: The actual payload (e.g., the JSON-LD template).

**How it works at runtime:**
If a Principle has multiple Remediations, the system selects the Remediation based on the audit's findings (e.g., if the audit detected WordPress, it filters techniques where `context_tags` includes `wordpress`).

---

## 8. Finding → Knowledge Architecture

**The Mapping:**
The mapping from `Check Rule` (the audit finding) to `Principle` MUST remain deterministic at its core, utilizing a mapping table (e.g., `check_principle_mapping`).

*   **Why 1:Many?**: A single check code like `MISSING_AUTHOR_SCHEMA` might map to Principle A ("E-E-A-T requires authorship transparency") and Principle B ("AI Overviews favor attributed content").
*   **Check Codes are Data:** Check codes must NOT be hardcoded in Python routing logic. They are keys in the database. The audit engine passes `['MISSING_AUTHOR_SCHEMA']` to the knowledge API. The API executes a simple SQL JOIN to retrieve the Principles.

---

## 9. Knowledge → Remediation Architecture

**Selection Mechanism:**
Remediation selection must be **Deterministic with Semantic Context fallback**.

1.  **Deterministic Filtering**: The audit payload includes tech stack metadata (e.g., `tech_stack: ['react', 'nextjs']`). The Knowledge API filters `Implementation Techniques` matching these tags.
2.  **Ranking (If multiple remain)**: Ranked by an `efficacy_score` stored on the Implementation Technique (e.g., a native framework feature outranks a hacky middleware workaround).
3.  **LLM Assembly (Not Selection)**: The LLM does NOT select the remediation. The deterministic engine passes the exact `Remediation Guidance` and `Implementation Technique` to the LLM. The LLM's only job is to weave this payload into a coherent, personalized narrative for the user.

---

## 10. Deterministic vs Semantic Retrieval

**Recommendation: HYBRID (Deterministic for Known Checks, Semantic for Context/Fallback).**

*   **Pure Deterministic (Current)**: Fails when new checks are added without manual mapping updates. Hard to scale.
*   **Full RAG (Semantic)**: Too risky for a compliance/audit tool. If an audit flags `ROBOTS_TXT_ERROR`, we cannot rely on vector math to *hopefully* retrieve the robots.txt principle. We need a 100% guarantee.

**The Hybrid Approach:**
1.  **Primary Pathway (Deterministic)**: `Audit Finding → check_principle_mapping table → Principle`. This covers the 36 known mappings with 100% precision and zero latency.
2.  **Fallback Pathway (Semantic)**: If the audit engine emits a novel check code or a raw text finding (e.g., "Found weird canonical tag loop"), the system creates an embedding of the finding and does a vector search against `Principle.statement`.
3.  **The QA Gate**: Any knowledge retrieved via the Semantic Fallback MUST be explicitly flagged to the user as "Inferred via AI" and requires a lower confidence score.

Given the corpus size (~213 claims, likely collapsing to ~80 core Principles), full RAG is overkill for the primary path, but embeddings are necessary to handle the 177 currently unreachable/orphaned claims.

---

## 11. LLM Boundary

To prevent hallucinations, the LLM boundary must be strictly enforced.

**The LLM MUST Receive:**
*   The raw audit finding data.
*   The deterministically retrieved `Principle` statements.
*   The exact `Evidence` quotes and `Source` titles/URLs.
*   The deterministically selected `Implementation Technique` code snippet.

**The LLM MUST NOT Invent:**
*   URLs, Citations, or Source Names.
*   Technical specifications, configuration parameters, or code syntax (unless instructed to adapt a provided snippet to a specific variable name).
*   Claim IDs or Principle IDs.

**The LLM SHOULD Decide:**
*   The narrative flow of the final report.
*   Tone and empathy (explaining the problem clearly to a non-technical stakeholder).
*   Synthesizing the provided rationale with the user's specific site context.

**The Deterministic Logic (Python/DB) MUST Decide:**
*   Which Principles apply.
*   Which Evidence is active/verified.
*   Which Remediation technique matches the tech stack.
*   The final Priority score.

---

## 12. Versioning & Lifecycle

Knowledge is not static. Google updates its algorithms; frameworks change their APIs.

**Lifecycle States:**
*   `DRAFT`: Newly ingested knowledge (e.g., from an LLM research run). Not available to the audit engine.
*   `VERIFIED`: Has been reviewed by a human OR meets strict automated criteria (Tier 1 source + exact quote match). Available for retrieval.
*   `ACTIVE`: Currently in use.
*   `SUPERSEDED`: Replaced by a newer Principle or Remediation. Cannot be retrieved for new audits. If a past audit cited this, the UI displays a warning: "This guidance has been updated."
*   `DEPRECATED`: Found to be false or irrelevant (e.g., the C325-C328 outcome records).

**State Transitions:**
Moving `DRAFT → VERIFIED` requires the presence of at least one valid `Evidence` record linked to a `Source` with an `authority_tier` of 1, 2, or 3.

---

## 13. Priority / Risk Model

Priority must be stripped out of the knowledge base and Python dicts (e.g., `PRIORITY_SCORES`) and treated as a runtime calculation.

**Data (Stored in DB):**
*   `Severity`: An attribute of the `Principle` (e.g., Blocking a crawler is CRITICAL severity; missing an alt tag is LOW severity).
*   `Impact`: An attribute of the specific `Finding` (e.g., It happened on the homepage vs. an orphaned archive page).
*   `Confidence`: Derived from the `Source` authority tier.

**Calculation (Runtime Engine):**
*   `Priority Score = f(Severity, Impact, Confidence)`
*   This calculation lives in the application layer (`audit_orchestrator.py`), not the database.

---

## 14. Canonical vs Derived Data

To maintain system integrity, we must strictly separate the source of truth from computed assets.

**Canonical Data (The Single Source of Truth in Postgres/SQLite):**
*   `Principles`, `Sources`, `Evidence`, `Remediation Guidance`, `Implementation Techniques`.
*   Deterministic mapping tables (`check_principle_mapping`).
*   Lifecycle state fields.

**Derived Data (Can be destroyed and rebuilt at any time):**
*   **Embeddings**: Vector representations of Principles for semantic search (stored in a vector DB or pgvector).
*   **Search Indexes**: Full-text search indexes on Evidence quotes.
*   **LLM Narratives**: The final synthesized reports presented to the user.
*   **Priority Scores**: Computed at runtime.

---

## 15. Handling Unknown Findings

When the audit engine outputs a check code with no mapping:

1.  **Immediate Fallback**: The knowledge engine falls back to Semantic Retrieval (Section 10). It embeds the check description and queries the Vector DB for the top 3 Principles.
2.  **LLM-Assisted Assembly**: The LLM is provided the novel finding and the top 3 semantic Principles. The prompt strictly instructs: "If these Principles do not directly address the finding, state that no specific guidance is available. Do not invent guidance."
3.  **Fail-Safe / QA Gate**: If the LLM generates a recommendation that does not include the IDs of the retrieved Principles, the Python QA Gate drops the recommendation entirely. The user sees the finding, but no remediation is offered.
4.  **Telemetry**: The unknown check code is logged to an `unmapped_checks` table for human analysts to map in the next sprint, creating a continuous improvement loop.

---

## 16. Stress Test Against Current Citeable Knowledge

How does the Ideal Architecture handle the messy reality of Stages 1 & 2?

**Example 1: `CRAWLER_FULLY_BLOCKED` → C050 → Python `REMEDIATION_TEXT` & `ACTION_SNIPPETS`**
*   **Current**: Hardcoded chaos scattered across DB and Python.
*   **Ideal State**:
    *   `Check Rule`: ID `chk_01`, Code `CRAWLER_FULLY_BLOCKED`.
    *   `Principle`: ID `p_050`, "Search crawlers must have explicit access to index content."
    *   `Mapping`: `chk_01` maps to `p_050`.
    *   `Remediation Guidance`: ID `rg_10`, "Update robots.txt to allow target user-agents." (Linked to `p_050`).
    *   `Implementation Technique`: ID `it_50`, Context `[nginx, robots.txt]`, Snippet `User-agent: * \n Allow: /`. (Linked to `rg_10`).
    *   *Result*: 100% database driven. Python orchestrator just executes queries.

**Example 2: C251-C275 (Authoritative Google Docs, currently unreachable)**
*   **Current**: Dead weight in the DB because they aren't mapped in `check_code_mappings`.
*   **Ideal State**: These are parsed. Their statements become `Principles`. Their URLs become `Sources`. Their quotes become `Evidence`. Because we now have semantic fallback (Section 10), if a novel audit finding conceptually matches C251, it is dynamically retrieved via vector search. They are no longer unreachable.

**Example 3: M001-M006 (PROCESS_NOTEs about LLM methodology)**
*   **Current**: Sitting in the `claims` table alongside technical facts.
*   **Ideal State**: **DELETED** from the knowledge graph. They are not domain principles. They belong in a GitHub wiki or a `system_meta` table.

**Example 4: CLM-051 and CLM-052 (Contradicted claims about schema impact)**
*   **Current**: Both exist, potentially confusing the LLM.
*   **Ideal State**:
    *   `p_051` is marked `SUPERSEDED`.
    *   `p_052` is marked `ACTIVE` and links to the newer Evidence.
    *   The database query explicitly filters `WHERE state = 'ACTIVE'`. The contradiction is resolved before the LLM ever sees it.

**Example 5: The Python `PRIORITY_SCORES` dict**
*   **Current**: Logic mixed with configuration in `synthesis_engine.py`.
*   **Ideal State**: **DELETED** from Python. Severity becomes an ENUM column on the `Principle` table. The Orchestrator queries the Severity and calculates Priority dynamically.

---

## 17. Architecture Options Compared

| Feature / Metric | Option A: Extended Deterministic (Migrate Python to DB, No AI Search) | Option B: Hybrid (Deterministic Core + Semantic Fallback for Novel) | Option C: Full RAG (All semantic, no mappings) |
| :--- | :--- | :--- | :--- |
| **Accuracy (Knowns)** | 100% (Guaranteed mapping) | 100% (Guaranteed mapping) | ~85% (Subject to vector search variance) |
| **Accuracy (Novel)** | 0% (Fails silently) | ~80% (Semantic matching) | ~80% (Semantic matching) |
| **Citation Integrity** | Very High | Very High | Medium (Risk of misaligned retrieval) |
| **Implementation Complexity** | Low (Basic CRUD & SQL) | Medium (Requires Vector DB/pgvector setup) | High (Requires intense chunking/embedding tuning) |
| **Maintenance Burden** | High (Requires manual mapping of every new check) | Medium (Only core checks need manual mapping) | Low (Just ingest documents) |
| **Scalability** | Poor (Bottlenecked by human mapping) | Excellent (Fails gracefully to AI) | Excellent |
| **Cost** | Lowest | Medium (Embedding generation) | Highest (Continuous vector operations) |

---

## 18. Recommended Architecture

**STRONGLY RECOMMENDED: Option B - Hybrid Architecture (Deterministic Core + Semantic Fallback).**

Citeable must normalize its knowledge into atomic relational entities (Principles, Evidence, Sources, Remediation) inside a standard relational database (PostgreSQL/SQLite), mapped deterministically to known check codes. It must simultaneously generate vector embeddings of the `Principles` to allow semantic fallback for the 177 currently orphaned claims and future novel audit findings.

---

## 19. Why This Is the Right Architecture

This architecture is the only option that simultaneously satisfies all three of the user's explicit constraints:

1.  **Traceability**: Because the core path is a deterministic SQL join (`Check → Mapping → Principle → Evidence → Source`), a developer can mathematically prove exactly why a specific recommendation was made. There is no "black box" vector math in the primary pipeline.
2.  **Reusability**: By shattering the monolithic "MIXED" claims into atomic `Principles` and `Implementation Techniques`, Citeable can reuse the "Configure Cloudflare" snippet across dozens of different performance-related checks without duplicating the data.
3.  **Decoupling Logic**: Moving `REMEDIATION_TEXT` and `PRIORITY_SCORES` from Python dictionaries into the database schema ensures that updating knowledge (e.g., tweaking a code snippet) requires zero changes to application code. Content strategists can update the DB; engineers maintain the pipeline.

Furthermore, introducing the Semantic Fallback safely activates the ~177 unreachable "evidence" claims (like the C2xx series) without compromising the strict compliance needed for core checks.

---

## 20. What NOT To Do

These are tempting shortcuts that will architecturally ruin the system. Avoid them at all costs.

1.  **"Just add more columns to the `claims` table"**: Adding `remediation_text` and `code_snippet` columns to the existing table preserves the monolithic anti-pattern. It forces duplication (every claim needing a Cloudflare snippet will have a copy of it).
2.  **"Use the LLM to dynamically generate the remediation code"**: Do not do this. LLMs hallucinate syntax and configuration parameters. Remediation code (Implementation Techniques) must be canonical data stored in the DB.
3.  **"Deprecate `check_code_mappings` and use Vector Search for everything"**: Do not do this. Vector search is probabilistic. If a site fails a critical compliance check (e.g., Legal/ToS), we cannot accept an 85% chance of retrieving the right principle. Core checks demand 100% deterministic retrieval.
4.  **"Put all logic in the database (Stored Procedures)"**: Keep the database focused on relational integrity. The logic (calculating priority, constructing LLM prompts) belongs in the Python layer.

---

## 21. Future-State Architecture Diagram

```ascii
================================================================================
                          CITEABLE IDEAL KNOWLEDGE ARCHITECTURE
================================================================================

[ 1. AUDIT LAYER ]
   Raw JSON Findings 
   (e.g., check_code: 'MISSING_CANONICAL', tech_stack: ['react'])
          |
          v
[ 2. ROUTING ENGINE (Python) ]
          |-----> Is check_code mapped?
          |       YES --> [ 3A. DETERMINISTIC PATH (SQL) ]
          |               SELECT principle_id FROM mappings WHERE code = X
          |
          |       NO  --> [ 3B. SEMANTIC FALLBACK PATH (Vector) ]
          |               Embed finding -> SELECT principle_id ORDER BY distance
          v
[ 4. KNOWLEDGE RETRIEVAL (Postgres/SQLite) ]
   +------------------+    +-------------------+    +--------------------+
   |   Principles     |--->|     Evidence      |--->|      Sources       |
   | (id, statement)  |    | (quote, id)       |    | (url, tier, type)  |
   +------------------+    +-------------------+    +--------------------+
          |
          v
   +------------------+    +-------------------+
   | Remediation      |--->| Implementation    |
   | Guidance (id)    |    | Techniques (code) |  <-- Filtered by 'tech_stack'
   +------------------+    +-------------------+
          |
          v
[ 5. ASSEMBLY ENGINE (Python) ]
   Combines payload: [Principle + Evidence + Source + Guidance + Technique]
   Calculates Priority: f(Severity, Impact)
          |
          v
[ 6. LLM SYNTHESIS LAYER ]
   System Prompt: "You are a formatter. Do not invent. Use provided payload."
   Input: Assembled Payload + User Context
   Output: Coherent Markdown Report
          |
          v
[ 7. QA GATE (Python) ]
   Regex/Validation: Did the LLM cite the exact Source IDs provided?
          |
          v
[ 8. FINAL OUTPUT ] ---> To End User
================================================================================
```

---

## 22. Stage 4 Implementation Blueprint

This is the dependency-ordered plan for migrating Citeable to the ideal architecture. Do not implement this code yet; this is the roadmap.

**Phase 1: Schema Creation (The Vessel)**
1.  Create tables: `principles`, `sources`, `evidence`, `remediation_guidance`, `implementation_techniques`.
2.  Create junction tables: `check_principle_mapping`, `principle_remediation_mapping`.
3.  Add tracking columns: `lifecycle_state`, `severity`, `authority_tier`.

**Phase 2: Data Extraction & Migration (The Great Splitting)**
1.  Write a Python migration script to parse the 213 legacy `claims`.
2.  Extract URLs -> Insert to `sources`.
3.  Extract rationale/statements -> Insert to `principles`.
4.  Extract Python `REMEDIATION_TEXT` -> Insert to `remediation_guidance`.
5.  Extract Python `ACTION_SNIPPETS` -> Insert to `implementation_techniques`.
6.  Migrate `check_code_mappings` into the new `check_principle_mapping` table.

**Phase 3: Cleanup & Deprecation (Pruning the Dead Wood)**
1.  Mark M001-M006 (Process Notes) as `DELETED`.
2.  Mark C325-C328 (Legacy Outcomes) as `DELETED`.
3.  Resolve contradictions (e.g., CLM-051 vs CLM-052) by setting older ones to `SUPERSEDED`.
4.  Drop the old `claims` table entirely.

**Phase 4: Code Refactor (Decoupling)**
1.  Remove all hardcoded dicts (`REMEDIATION_TEXT`, `ACTION_SNIPPETS`, `PRIORITY_SCORES`) from `synthesis_engine.py` and `audit_orchestrator.py`.
2.  Update the ORM/Query layer to traverse the new relational schema.
3.  Rewrite the LLM prompt templates to accept the structured payload (Principle + Evidence + Guidance) rather than raw claim strings.

**Phase 5: Capabilities Expansion (Semantic Fallback)**
1.  Initialize a vector database (e.g., Chroma, or pgvector extension).
2.  Generate embeddings for all `VERIFIED` `Principle.statement` fields.
3.  Implement the semantic fallback logic in the Routing Engine for unmapped checks.

---

## FINAL ANSWER

> "If we threw away none of Citeable's useful knowledge, but were allowed to reorganize it so it became a coherent, authoritative, reusable system — what would the knowledge itself need to look like?"

The knowledge must cease being a collection of sprawling, monolithic paragraphs and hardcoded Python dictionaries. It needs to look like a highly structured, relational graph.

At the center are **Principles**—immutable, atomic truths about the domain. Beneath them is **Evidence**—exact, verified quotes anchored to specific, tiered **Sources** (like Google Docs or W3C standards). Above them are **Check Rules**—the deterministic hooks that the audit engine triggers. And branching outward is **Remediation**—split cleanly into strategic *Guidance* (the "what") and tactical, stack-specific *Implementation Techniques* (the "how").

By organizing the knowledge this way, a developer can mathematically trace exactly why a specific Nginx config was recommended for a specific audit finding, backed entirely by canonical data, without ever opening a Python file to update it.
