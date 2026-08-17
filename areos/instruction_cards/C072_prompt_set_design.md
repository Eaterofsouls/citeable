---
card_id: C072
stage: STAGE-22 (upstream)
automatability: Not
check_name: "Citation Prompt Set Design"
claim_statement: "Designing the actual prompt set — phrasing questions the way real users actually ask at the right specificity and funnel stage — is not-automatable and the highest-leverage judgment call in the whole citation-measurement phase."
---

# C072 — Citation Prompt Set Design

## What AREOS Does Automatically
- Executes prompts against AI engines and records citation frequency.
- Produces `citation_rate_str` (e.g., "3/5 runs").
- Aggregates results across multiple runs.

## What You Must Do Manually

**This is the single highest-leverage step in the entire AEO audit.** A bad prompt set invalidates all citation data downstream.

### Step 1 — Understand the user's actual intent
Before writing any prompts, interview the client or study their analytics:
- What questions do their customers type into Google or ChatGPT?
- What stage of the funnel are they in? (awareness / consideration / decision)
- What does the client want to *be cited for*? (their product category, a specific service, a named condition they treat)

### Step 2 — Write prompts at 3 specificity levels per topic
For each key topic, write at least one prompt at each level:

1. **Broad / awareness**: *"What is [industry category]?"* or *"How does [process] work?"*
2. **Mid-funnel / consideration**: *"What are the best [product category] options for [use case]?"*
3. **Bottom-funnel / decision**: *"Is [Brand Name] good for [specific use case]?"* or *"[Brand Name] vs [Competitor Name]"*

### Step 3 — Validate the prompt set with the client
Share the proposed prompt set with the client before running it.
- Do these match how their real customers ask questions?
- Are there obvious questions missing that they hear from sales calls?
- Are any prompts leading or biased in a way that inflates citation likelihood?

### Step 4 — Record the rationale
Document **why** each prompt was chosen. This is essential because when the report shows "cited in 2/5 runs for prompt X," the reader needs to understand what user intent that prompt represents.

### Deliverable
A signed-off `prompt_set.yaml` file, stored alongside the `3d_label_set.yaml`, listing each prompt with its topic, funnel stage, and rationale. This file is the input to `citation_sampler.py`.
