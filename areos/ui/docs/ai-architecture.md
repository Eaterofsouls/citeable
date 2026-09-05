This page details the structural boundaries and architectural safeguards surrounding Citeable's LLM integrations, explaining how the platform manages probabilistic operations alongside deterministic auditing.

## The AI Boundary Principle

Citeable uses LLMs at specific execution paths across the entire codebase. Every other operation — scoring, schema validation, robots parsing, knowledge wiring, QA gating — is deterministic. This is a deliberate architectural choice, not a limitation.

This boundary exists because deterministic operations produce reproducible, auditable results, whereas LLM outputs are inherently probabilistic and non-deterministic. Mixing them creates systems where you can't tell which results are reliable. By design, Citeable keeps them separate: the deterministic pipeline produces structured findings, and AI synthesizes human-readable narrative from those findings.

## Complete LLM Usage Inventory

The following table details every LLM call site within Citeable:

| Call Site | Classification | When Called | Could It Be Deterministic? |
|---|---|---|---|
| Citation frequency sampling | Empirical measurement | Every audit | No — requires querying live AI search engines |
| Extractability judgment | Content evaluation | Only when heuristic is ambiguous | Partially — heuristic fast-path handles clear cases |
| Synthesis draft (Step 1) | Linguistic synthesis | After human review | No — requires language generation |
| Adversarial red-teaming (Step 2) | Verification | After Step 1 | No — requires semantic analysis |
| Narrative grounding (Step 3) | Correction | After Step 2 | No — requires language rewriting |
| Claim extraction from docs | Knowledge discovery | Out-of-band research | No — requires understanding documents |
| Candidate classification | Semantic comparison | KB governance workflow | Partially — but semantic similarity is needed |
| Vector embeddings | Similarity search | RAG fallback (uncommon) | No — requires embedding models |

## Zero-SDK Provider Architecture

All frontier foundation models in Citeable are accessed via a unified, direct HTTP orchestration layer with zero vendor SDKs installed. This eliminates SDK version conflicts, reduces container size, minimizes supply chain attack surface, and completely avoids vendor lock-in. Every provider uses the same HTTP dispatch mechanism with consistent timeout, retry, and error handling.

Citeable orchestrates across multiple frontier foundation models using a priority-weighted failover cascade. If the primary model is unavailable, the system transparently routes to the next available model.

## Forward vs Reverse Sequence — Cognitive Diversity

To prevent same-model self-review failures, Citeable employs a structural invariant based on directional model resolution:

- The drafting phase evaluates models from highest to lowest priority (forward sequence).
- The adversarial red-teaming phase evaluates models from lowest to highest priority (reverse sequence).

The drafting model and the red-team model are structurally guaranteed to be different, preventing self-validation bias. Different model architectures catch different failure modes, ensuring genuine cognitive diversity.

```mermaid
sequenceDiagram
    autonumber
    participant Orch as Orchestrator
    participant M1 as Primary Model
    participant M2 as Fallback Model A
    participant M3 as Fallback Model B
    participant M4 as Secondary Model
    
    rect rgb(239, 246, 255)
    note right of Orch: [STEP 1] Forward Sequence<br/>Drafting: Primary to Fallback
    Orch->>M1: 1. Try Primary Model
    M1-->>Orch: Rate Limit Exceeded
    Orch->>M2: 2. Try Fallback Model A
    M2-->>Orch: Success (Draft Narrative Generated)
    end
    
    rect rgb(254, 242, 242)
    note right of Orch: [STEP 2] Reverse Sequence<br/>Adversarial Red-Team Critique
    Orch->>M3: 3. Try Fallback Model B
    M3-->>Orch: Service Unavailable
    Orch->>M4: 4. Try Secondary Model
    M4-->>Orch: Success (Violation Types Audited)
    end
```

## The Three-Step Synthesis Pipeline

The narrative synthesis generation utilizes a robust three-step pipeline to ensure quality and factual accuracy.

```mermaid
flowchart TD
    classDef draft fill:#EFF6FF,stroke:#2563EB,stroke-width:2px,color:#1E3A8A,rx:8px,ry:8px;
    classDef critic fill:#FEF2F2,stroke:#DC2626,stroke-width:2px,color:#991B1B,rx:8px,ry:8px;
    classDef ground fill:#ECFDF5,stroke:#059669,stroke-width:2px,color:#065F46,rx:8px,ry:8px;
    classDef card fill:#FFFFFF,stroke:#CBD5E1,stroke-width:1.5px,color:#0F172A,rx:8px,ry:8px;
    classDef zone fill:#F8FAFC,stroke:#94A3B8,stroke-width:2px,stroke-dasharray:5 5,color:#0F172A;

    subgraph STEP1["[STEP 01] Synthesizer (Forward Sequence)"]
        direction TB
        S1["<b>[DRAFTING] Generates Remediation Narrative</b><br/>───────────────<br/>Inputs: Wired Claims &amp; Analyst Notes"]:::draft
    end
    class STEP1 zone

    subgraph STEP2["[STEP 02] Red Teamer (Reverse Sequence)"]
        direction TB
        V1["<b>Hallucinated Claim:</b> Claim not in input data"]:::card
        V2["<b>Unsupported Leap:</b> Recommendation lacks logical premise"]:::card
        V3["<b>Fabricated Stat:</b> Metric not observed in crawl"]:::card
        V4["<b>Vague:</b> Generic non-actionable advice"]:::card
    end
    class STEP2 zone

    subgraph STEP3["[STEP 03] Evidence Grounder (Forward Sequence)"]
        direction TB
        G1["<b>[PREFIX: PRINCIPLE]</b> Knowledge Base Principle"]:::ground
        G2["<b>[PREFIX: EVIDENCE]</b> Site-Specific Crawl Evidence"]:::ground
    end
    class STEP3 zone

    FinalOutput(["<b>[FINAL] Grounded Remediation Report</b><br/>───────────────<br/>Invariant-Verified &amp; Red-Team Approved"]):::ground

    S1 -->|"1. Passes Draft"| STEP2
    STEP2 -->|"2. Violation Flags"| STEP3
    STEP3 -->|"3. Enforces Prefixes"| FinalOutput
```

The red-team model audits for hallucinated claims, unsupported logical leaps, fabricated statistics, and vague non-actionable advice.

The Grounder prefixes resolutions with strict evidence markers:
- `[Knowledge Base Principle]`: Recommendation based on general domain knowledge
- `[Site-Specific Evidence]`: Recommendation based on specific observations from this audit

> **Note:** To prevent prompt injection, all crawled content is strictly sandboxed.

```mermaid
flowchart LR
    classDef input fill:#EFF6FF,stroke:#2563EB,stroke-width:2px,color:#1E3A8A,rx:8px,ry:8px;
    classDef fence fill:#FFFBEB,stroke:#D97706,stroke-width:2px,color:#92400E,rx:8px,ry:8px;
    classDef asm fill:#FAF5FF,stroke:#7C3AED,stroke-width:2px,color:#5B21B6,rx:8px,ry:8px;
    classDef llm fill:#ECFDF5,stroke:#059669,stroke-width:2px,color:#065F46,rx:8px,ry:8px;
    classDef zone fill:#F8FAFC,stroke:#94A3B8,stroke-width:2px,stroke-dasharray:5 5,color:#0F172A;

    subgraph SOURCES["Input Channels"]
        direction TB
        Sys["<b>System Prompt</b><br/>(Trusted Template)"]:::input
        Findings["<b>Findings JSON</b><br/>(System Generated)"]:::input
        Crawled["<b>Crawled HTML</b><br/>(Untrusted Web Data)"]:::fence
    end
    class SOURCES zone

    subgraph FENCING["Prompt Fencing Engine"]
        direction TB
        Clean["<b>HTML Cleaner</b><br/>Strip scripts, styles &amp; tags"]:::fence
        Escape["<b>XML Escaper</b><br/>Convert &lt;, &gt;, &amp; entities"]:::fence
        Fenced["<b>Fenced Content</b><br/>Sandboxed Markup"]:::fence
    end
    class FENCING zone

    Assembler["<b>Prompt Assembler</b><br/>Strict system instructions"]:::asm
    LLMCall["<b>LLM Inference</b><br/>Priority-Weighted Cascade"]:::llm

    Sys --> Assembler
    Findings --> Assembler
    Crawled --> Clean
    Clean --> Escape
    Escape --> Fenced
    Fenced --> Assembler
    Assembler --> LLMCall
```

## Graceful Degradation

Citeable handles API failures transparently without crashing the deterministic audit pipeline.

| Failure | Handling |
|---|---|
| Step 1 fails (all providers) | No synthesis generated; returns deterministic results only |
| Step 2 fails | Proceeds without flags; Grounder receives unaudited draft |
| Step 3 fails | Falls back to Step 1 draft |
| No BYOK keys configured | Synthesis skipped; deterministic results still available |
| Provider returns rate limit | Exponential backoff with limits, then routes to next provider |
| Provider returns authentication error | Instant skip to next provider |
| Provider returns server error | Limited retries, then routes to next provider |
| Execution time budget exhausted | Cascade terminates cleanly |

## BYOK (Bring Your Own Key)

Citeable allows users to supply their own API keys via a secure, zero-persistence lifecycle:

```mermaid
flowchart TD
    classDef client fill:#EFF6FF,stroke:#2563EB,stroke-width:2px,color:#1E3A8A,rx:8px,ry:8px;
    classDef proc fill:#FFFFFF,stroke:#3B82F6,stroke-width:1.5px,color:#0F172A,rx:8px,ry:8px;
    classDef gc fill:#ECFDF5,stroke:#059669,stroke-width:2px,color:#065F46,rx:8px,ry:8px;
    classDef zero fill:#FEF2F2,stroke:#DC2626,stroke-width:2px,color:#991B1B,rx:8px,ry:8px;
    classDef zone fill:#F8FAFC,stroke:#94A3B8,stroke-width:2px,stroke-dasharray:5 5,color:#0F172A;

    Client["<b>[CLIENT] BYOK Vault (Browser)</b><br/>───────────────<br/>Secure Transport"]:::client

    subgraph Server_Memory["[EPHEMERAL SERVER MEMORY]"]
        direction TB
        Extraction["<b>[01] Key Extraction</b><br/>In-Memory Only"]:::proc
        Dispatch["<b>[02] Model Dispatch</b><br/>Direct HTTPS Orchestration"]:::proc
    end
    class Server_Memory zone

    Result["<b>[OUTPUT] Model Response</b><br/>───────────────<br/>Parsed Structure"]:::proc
    GC["<b>[CLEANUP] Memory Cleared</b><br/>───────────────<br/>Request Terminated"]:::gc
    ZeroPersistence(["<b>[INVARIANT] Zero Retention</b><br/>───────────────<br/>No DB / No Disk / No Log Leaks"]):::zero

    Client -->|"1. Secure Transmission"| Extraction
    Extraction --> Dispatch
    Dispatch -->|"2. Return Data"| Result
    Result -->|"3. Terminate Request"| GC
    GC -.-> ZeroPersistence
```

1. User stores API keys in a browser-side BYOK vault
2. Keys are securely transmitted during requests
3. Keys are processed in-memory only during your request and are never written to any persistent storage
4. Keys are securely passed through to the model orchestration layer
5. After the request completes, memory is immediately cleared
6. **Keys are NEVER written to disk, database, logs, or telemetry**

Client keys natively take priority over server configuration. Custom base URLs are validated against Server-Side Request Forgery (SSRF) before use, SSL verification is never disabled, and users can test configurations securely.

> *Users bear sole responsibility for their third-party API accounts, usage costs, and compliance with each provider's Acceptable Use Policy. See [Legal](legal.md) for details.*

## Citation Sampling Methodology

Citation frequency sampling queries live AI search engines using domain-specific prompt sets.

The process computes:
- Citation frequency
- Share of voice
- Competitor domain presence

A circuit breaker trips after consecutive errors per engine to preserve stability.

> **Note:** These citation results represent OBSERVED FREQUENCY only, not a guaranteed or reproducible measurement. AI engine outputs are probabilistic and vary across runs.

Certain engines are intentionally excluded due to lack of programmatic APIs, Terms of Service restrictions, or absence of structured citation grounding.

## What AI Does NOT Do in Citeable

The negative space of Citeable's AI boundaries is critical. The system deliberately refrains from using AI for tasks that demand precision.

- AI does **NOT** compute scores (deterministic arithmetic)
- AI does **NOT** validate schemas (rule engine)
- AI does **NOT** parse robots.txt (state machine)
- AI does **NOT** wire findings to claims (DB lookup + RAG fallback)
- AI does **NOT** approve knowledge changes (human-only)
- AI does **NOT** determine what wizard questions to show (conditional logic based on fired check codes)
- AI does **NOT** store or log user credentials (ephemeral lifecycle)
