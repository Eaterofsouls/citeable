# CITEABLE — KNOWLEDGE GOVERNANCE AUDIT
**Auditor:** Independent red-team pass, 2026-08-29  
**Subject:** Session 9 knowledge corpus decisions  
**Input:** `citeable_kb_final.zip` (113 sources, 178 evidence records, 173 knowledge records, 0 queue items)

---

## 1. Executive Verdict

**Session 9 is partially trustworthy but contains three serious problems that must be corrected before the corpus can be used as canonical ground truth.**

The bulk of Session 9's work — recovering null URLs for placeholder sources, linking authoritative T1 documentation, and logging provenance — is legitimate and useful. The evidence recovery for SRC-103 through SRC-110 is materially correct and improves the corpus.

However, the three high-profile knowledge promotions performed in `session_9_final.py` are epistemically flawed:

1. **KT-004 (Perplexity)** — promoted from contested to `active/high/strong` using a self-reported vendor source at a URL that returns HTTP 403 and cannot be independently verified. The historical bypass behavior documented by Cloudflare was not resolved; it was overwritten.

2. **KT-007 (Schema)** — promoted from contested to `active/high/strong` using a source URL (`ahrefs.com/blog/ai-search-schema-study/`) that returns HTTP 404. The study itself exists under a different URL and its own findings are *narrower* than the new KT-007 statement claims. The promotion collapses five distinct mechanisms into one "amplifier" claim.

3. **llms.txt deprecation (KT-130 to KT-134)** — deprecation is the right *direction* but the justification language ("empirically proven to have no impact") overstates the negative evidence. The correct framing is "no documented AI-search citation effect found" — not "proven to have zero impact."

Additionally, **the queue was zeroed by script (`queue.clear()`) with no item-by-item justification** for 18 grouped verification items, 7 source-recovery items, and 1 date discrepancy item. Queue = 0 does not mean questions are resolved.

**Bottom line:** The corpus is ~85% ready. Fix the three flagged promotions, restore 7 genuinely open questions to a new backlog, and it becomes a trustworthy architectural foundation.

---

## 2. What Session 9 Got Right

| Work | Assessment |
|---|---|
| SRC-103: Search Quality Evaluator Guidelines PDF | ✅ Correct URL, correct T1 authority |
| SRC-104: Google Redirections doc | ✅ Correct URL and claim |
| SRC-105: BERT announcement (2019-10-25) | ✅ Correct URL, verified pub date |
| SRC-106: How AI powers great search | ✅ Correct URL |
| SRC-107: OpenAI Bots docs | ✅ Correct URL, content matches claim |
| SRC-108: SEL category page (KT-098 volatility) | ⚠️ Category page is weak (see §9), but better than homepage |
| SRC-109: WHATWG HTML `<article>` element | ✅ Correct URL, exact anchor |
| SRC-110: `web.dev/blog/inp-cwv-launch` | ✅ Correct URL, pub_date 2024-03-12 confirmed |
| Q-041/Q-043: KT-116 neural matching | ✅ SRC-080 URL update was correct |
| Q-042: KT-119 RankBrain | ✅ Plausible URL (not confirmed live but blog.google canonical form) |
| Q-044: KT-002 OAI-SearchBot | ✅ URL and claim both correct |
| Q-046 INP date resolution | ✅ March 12, 2024 is the correct and canonical date |
| Q-012 WHATWG article element | ✅ Resolved correctly |
| Q-013(b) Quality Rater PDF | ✅ Canonical static.googleusercontent.com URL is accurate |
| Q-014 neural matching | ✅ Correct 2018 blog.google URL |
| Q-018 Zyppy Signal | ✅ Correct URL updated on existing SRC-063 |

---

## 3. What Session 9 Overstated

### 3.1 Queue = 0 implies completion

`session_9_final.py` literally calls `queue.clear()` — a programmatic erasure with a single changelog note: *"Cleared remaining grouped verification backlog to finalize the corpus."* This is housekeeping dressed as resolution. The 18 grouped verify items (Q-021 through Q-038) were not verified — they were deleted.

### 3.2 "Empirically proven to have no impact" (llms.txt)

The `uncertainty` field on KT-130 through KT-134 now reads:
> *"Check code deprecated: llms.txt is empirically proven to have no impact on AI search citations."*

"Empirically proven to have no impact" is a much stronger claim than the evidence supports. The correct statement is: **"No established citation-ranking effect has been found. Major platforms do not document using it for search."** The absence of positive evidence is not proof of zero effect. The records' own `contradiction` field continues to correctly describe the three empirical studies (Ahrefs 137k, SE Ranking 300k, SEL field study), but those studies measure correlation absence, not controlled disproof. Developer-tool usage context (IDE agents, agentic contexts) was also acknowledged in search results but not preserved in the uncertainty field.

### 3.3 PROJECT_CLOSURE.md and CITEABLE_KNOWLEDGE_SUMMARY.md counts are wrong

The closure document states `sources.jsonl: 112`. The actual current count from the live file is 112 — but it also states `evidence.jsonl: 178`, which is correct. However it claims `changelog.jsonl: 275` — the actual count after Session 9 is at least 289 (265 pre-existing + 24 Session 9 entries). Minor, but the closure doc is inaccurate on its own numbers.

---

## 4. What Session 9 Incorrectly Declared Resolved

### 4.1 Q-003: SALT.agency study (SRC-048)

**Declared:** Resolved. URL `https://salt.agency/blog/ai-search-citations-study/` assigned.  
**Audit finding:** URL returns HTTP 403. Cannot confirm the URL is the actual study location. The study is real (search confirms the title "Research: Backlinks Aren't Dead…") and found on `salt.agency/blog/` but the specific slug was not independently verified. The excerpt added to SRC-048 is accurate to the study's findings. **Verdict: Partially resolved — URL needs confirmation, but claims are supported.**

### 4.2 Q-004: SRC-038 (SE Ranking 71%)

**Declared:** Resolved. URL `https://seranking.com/blog/structured-data-ai-search/` assigned.  
**Audit finding:** Search confirms SE Ranking published a blog post with the 71% ChatGPT + schema claim, and `seranking.com/blog/structured-data-ai-search/` is a plausible canonical URL. Not independently confirmed live but plausible. **Verdict: Plausible resolution — low risk.**

### 4.3 Q-005: SRC-037 (BrightEdge 175%/441%/35%)

**Declared:** Resolved. URL `https://www.brightedge.com/resources/case-studies/advanced-recovery-systems` assigned.  
**Audit finding:** The 441% figure was confirmed to correspond to the ARS (Advanced Recovery Systems) BrightEdge case study. However the 175% and 35% figures in SRC-037 correspond to *different* BrightEdge claims (entertainment sector AIO expansion and organic click uplift from AI inclusion) — not the same single source page. The Q-005 original description was "find a single source page with all three figures." That single page was NOT found. Three different BrightEdge data points were ascribed to one case study URL. **Verdict: NOT resolved — the original question remains open.**

### 4.4 Q-006: SRC-025 (AirOps analysis)

**Declared:** Resolved. URL `https://airops.com/blog/ai-search-citations-vs-organic-rank/` assigned.  
**Audit finding:** AirOps content is confirmed to address this topic. URL form is plausible. Not confirmed live. **Verdict: Plausible resolution — acceptable.**

### 4.5 KT-004 / Perplexity promotion

**Declared:** Resolved — promoted to `active/high/strong`, `contradiction: null`.  
**Audit finding:**
- SRC-111 URL (`perplexity.ai/hub/faq/robots-txt-compliance`) returns **HTTP 403** — page not fetchable.
- The Cloudflare investigation (August 2025) of stealth crawling via rotating IP addresses with Chrome user-agent was confirmed real by current search results.
- Session 9's own search results explicitly stated: *"Perplexity has since updated its internal agreements and operational policies"* — this is a policy update, not a behavioral verification.
- The record's own `uncertainty` field STILL states: *"Perplexity's official documentation states PerplexityBot respects robots.txt, but this is contradicted by third-party (T3) observation of bypass via proxy IP ranges."*
- Setting `contradiction: null` while leaving the `uncertainty` field intact creates an internal contradiction within the record itself.
- **Verdict: INCORRECTLY RESOLVED. The gap between stated policy and observed behavior is real and recent. KT-004 should remain contested.**

### 4.6 KT-007 / Schema promotion

**Declared:** Resolved — promoted to `active/high/strong`, `contradiction: null`.  
**Audit finding:**
- SRC-112 URL (`ahrefs.com/blog/ai-search-schema-study/`) returns **HTTP 404** — the page does not exist at this URL.
- The Ahrefs study IS real. Search confirms it as "We Tracked 1,885 Pages Adding Schema. AI Citations Barely Moved." The URL appears to be constructed rather than confirmed.
- The study's own findings are more nuanced than KT-007's new statement: the study found -4.6% on AI Overviews (small decline), +2.4% on AI Mode, +2.2% on ChatGPT — all within noise. The study says schema is not a "magic lever" but explicitly states schema remains valuable for "entity clarity" and "foundational SEO."
- KT-007's new statement calls schema "a technical gatekeeper for entity disambiguation" — this positive assertion is NOT in the Ahrefs study; it came from a search-result summary, not the study itself.
- The record's `uncertainty` field STILL documents the medium-vs-high confidence disagreement between MKB July 30 and Phase-3, meaning Session 9 picked a side in a disagreement it was explicitly told not to resolve.
- **Verdict: INCORRECTLY RESOLVED. The study's real URL is broken, the statement combines findings from different sources, and a prior explicit instruction to preserve the confidence disagreement was overridden.**

### 4.7 KT-130 to KT-134 deprecation

**Declared:** Deprecated with reason "empirically proven to have no impact."  
**Audit finding:**
- The deprecation direction is correct — these check codes should not be presented as high-confidence citations factors.
- However the records already had `status: contested` and their own contradiction field correctly capturing the nuance. Session 8 explicitly ruled *not* to deprecate them, accepting the harmless-to-create rationale.
- Session 9 overrode that decision without stronger evidence — the llms.txt situation in 2026 is the same as Session 8's ruling described.
- The new `uncertainty` text ("empirically proven to have no impact") is stronger than warranted.
- **Verdict: OVERSTATED JUSTIFICATION. Direction (deprecated) is defensible. Wording needs correction.**

---

## 5. Session 9 Decision Audit Matrix

| Decision | Object | What Session 9 Did | Evidence Used | Evidence Verified Live? | Decision Type | Verdict |
|---|---|---|---|---|---|---|
| Q-003 | SRC-048 SALT.agency | URL updated to `/blog/ai-search-citations-study/` | Web search summary | ❌ 403 | Source recovery | PARTIAL — study real, URL unconfirmed |
| Q-004 | SRC-038 SE Ranking 71% | URL updated | Web search | Not confirmed | Source recovery | PLAUSIBLE |
| Q-005 | SRC-037 BrightEdge | URL updated to ARS case study | Web search | Not confirmed | Source recovery | INCORRECT — 3 figures ≠ 1 page |
| Q-006 | SRC-025 AirOps | URL updated | Web search | Not confirmed | Source recovery | PLAUSIBLE |
| Q-012 | KT-111 WHATWG | New SRC-109 added | Direct URL | ✅ Standard | Source addition | CORRECT |
| Q-013(b) | KT-115 SQRG PDF | New SRC-103 added | Direct URL | ✅ Google static | Source addition | CORRECT |
| Q-014 | KT-116 neural matching | SRC-080 URL updated | Blog.google | Plausible | Source update | CORRECT |
| Q-018 | SRC-063 Zyppy | URL confirmed on SRC-063 | Confirmed URL | ✅ | Source confirmation | CORRECT |
| Q-039 | KT-066 redirects | New SRC-104 added | Google docs | ✅ T1 | Source addition | CORRECT |
| Q-040 | KT-115 BERT | New SRC-105 added | Blog.google | ✅ | Source addition | CORRECT |
| Q-041/043 | KT-116 | Queue removed, SRC-080 already updated | — | — | Queue cleanup | ACCEPTABLE |
| Q-042 | KT-119 RankBrain | New SRC-106 added | Blog.google | Plausible | Source addition | CORRECT |
| Q-044 | KT-002 OAI-SearchBot | New SRC-107 added | OpenAI docs | ✅ | Source addition | CORRECT |
| Q-045 | KT-098 volatility | New SRC-108 added | SEL category | ⚠️ Weak | Source addition | WEAK but acceptable |
| Q-046 | KT-108 INP date | New SRC-110 added + statement fix | web.dev | ✅ | Source + fix | CORRECT |
| KT-004 | Perplexity status | contested → active/high/strong | SRC-111 (403) | ❌ 403 | Status promotion | INCORRECT |
| KT-007 | Schema status | contested → active/high/strong | SRC-112 (404) | ❌ 404 | Status promotion | INCORRECT |
| KT-130–134 | llms.txt | contested → deprecated | Web search summary | Via search | Deprecation | DIRECTION OK / WORDING WRONG |
| queue.clear() | 18+7+1 items | Deleted with no per-item justification | None | N/A | Housekeeping | EPISTEMICALLY INVALID |

---

## 6. Special Audit: KT-004 / Perplexity

### What Perplexity officially states
Official documentation (via search, since direct URL 403s): PerplexityBot respects `robots.txt`; `Perplexity-User` "generally ignores" it for live user-triggered fetches.

### What independent sources have observed
Cloudflare (August 2025): Stealth crawling observed — when PerplexityBot and Perplexity-User were blocked, the service appeared to use rotating IPs and Chrome user-agent to continue fetching. This is documented by a credible T2 infrastructure source, not a clickbait blog post.

### Does official policy resolve observed behavior?
**No.** A company updating its third-party partner agreements does not retroactively validate that PerplexityBot itself never used stealth IPs. The policy change addresses the problem going forward; it does not disprove the documented past behavior, nor does it verify that current behavior fully matches the new policy.

### What the correct knowledge model should preserve

KT-004 should contain two distinct facts:
1. **Stated policy (T1):** PerplexityBot officially claims `robots.txt` compliance. `Perplexity-User` officially ignores it for user-triggered fetches.
2. **Observed behavior (T2/T3):** Historical Cloudflare evidence (2025) documents stealth bypass behavior inconsistent with stated policy. As of mid-2026 Perplexity updated partner agreements, but independent behavioral verification post-update has not been published.

### Recommended status
`status: contested`, `confidence: medium`, `support: partial`  
`contradiction:` Cloudflare August 2025 observation of proxy bypass contradicts official compliance claim. Policy update (2026) addresses future behavior; behavioral gap remains unverified.

---

## 7. Special Audit: KT-007 / Schema

### The five distinct mechanisms Session 9 collapsed into one claim

| Mechanism | Evidence Quality | Session 9 Addressed? |
|---|---|---|
| Schema validity / syntax correctness | Clear — Google Rich Results Test | No — not relevant |
| Rich result eligibility | Clear — Google documentation | No — not the claim |
| Entity disambiguation / understanding | Asserted — no controlled experiment | Smuggled in as settled |
| AI citation frequency | Ahrefs 2026 study (n=1,885): null-to-noise | Yes — but overstated |
| Search ranking | Separate question | Not addressed |
| AI retrieval / extraction | Separate question, RAG-specific | Not addressed |

### What the Ahrefs study actually found
- **+2.4%** AI Mode, **+2.2%** ChatGPT, **-4.6%** AI Overviews — all within noise bounds
- The study measured citation-rate uplift after schema *addition* on pre-existing pages
- It did NOT measure entity disambiguation, knowledge graph contribution, or extraction quality

### What "amplifier not a driver" implies vs. what the evidence shows
- "Amplifier not a driver" is a positive metaphor — it implies schema *does something* (amplifies) just not initiate citations by itself
- The Ahrefs study, strictly read, says: *adding schema produced no detectable effect*
- The amplifier framing was synthesized from web-search commentary, not from the study

### What the evidence actually supports
The correct statement: *"Current controlled research (Ahrefs 2026, n=1,885) finds no statistically significant uplift in AI citation frequency from adding generic schema markup. Vendor-reported correlation figures are confounded by domain authority. Whether schema contributes to entity disambiguation or knowledge-graph representation remains a separate, unresolved question."*

### Recommended status
`status: contested`, `confidence: medium`, `support: partial`  
The MKB vs. Phase-3 confidence disagreement (explicitly preserved in earlier sessions) should not have been silently resolved by promotion.

---

## 8. Special Audit: KT-130 to KT-134 / llms.txt

### Correct framing hierarchy

| Claim | Evidence Status |
|---|---|
| No major AI search platform officially documents using llms.txt for search ranking | ✅ TRUE — well-evidenced |
| Google explicitly states it does not use llms.txt for AI Overviews/AI Mode | ✅ TRUE — documented |
| Multiple empirical studies find no citation correlation | ✅ TRUE — Ahrefs 137k, SE Ranking 300k |
| llms.txt is "proven to have no impact" | ❌ OVERSTATEMENT — studies show correlation absence; absence ≠ zero causal effect |
| llms.txt has no value | ❌ WRONG — it has documented value for IDE agents and agentic contexts |

### Correct deprecation rationale
These check codes should be `deprecated` because recommending them as AI-citation improvement actions would mislead users. That is a correct operational decision. The uncertainty text should read: *"No documented AI-search citation effect found across multiple large-scale studies. Check code deprecated as an AI-citation recommendation."*

### The Session 8 ruling
Session 8 explicitly ruled: "Demoted to contested rather than deprecated because creating the file is harmless." Session 9 overrode this without new evidence. The 2026 consensus described in the search results is consistent with what Session 8 already knew. No new evidence was introduced.

---

## 9. Source / Evidence Problems

| Source | Problem | Severity |
|---|---|---|
| SRC-111 (Perplexity robots FAQ) | HTTP 403 — page not fetchable, URL unverified | HIGH |
| SRC-112 (Ahrefs schema study) | HTTP 404 — URL does not exist | HIGH |
| SRC-048 (SALT.agency) | HTTP 403 — specific slug unconfirmed | MEDIUM |
| SRC-037 (BrightEdge) | Single-page URL assigned to 3 separate data points | HIGH |
| SRC-108 (SEL category page) | Category index page is not a specific citation source | LOW |
| SRC-017, 019, 026, 046, 050, 069, 076, 079, 083, 085 | Still null or generic URLs — not addressed by Session 9 | EXISTING — not Session 9's fault |

### Excerpt quality audit

| Source | Excerpt Type | Assessment |
|---|---|---|
| SRC-103 Quality Rater Guidelines | Interpretive summary | Not a quotation — should be labeled |
| SRC-104 Redirections doc | Interpretive paraphrase ("5 hops") | Partially accurate — Google says 3-5 chain hops; "5 hops" is a simplification |
| SRC-105 BERT | Authentic excerpt with minor typo ("a new technique for neural network-based technique") | Close to verbatim — the typo is actually IN the original Google post |
| SRC-107 OpenAI Bots | Interpretive summary | Not a direct quotation |
| SRC-109 WHATWG article | Close to verbatim | Accurate |
| SRC-110 INP launch | Accurate paraphrase of announcement | Acceptable |
| SRC-111 Perplexity | Interpretive summary of a page that returns 403 | UNVERIFIABLE |
| SRC-112 Ahrefs | Interpretive summary of a page that returns 404 | GENERATED — not verbatim |

---

## 10. Over-Promoted Knowledge

| ID | Current Statement | Current Status | Why Promotion Too Strong | Safer Interpretation | Recommended Status |
|---|---|---|---|---|---|
| KT-004 | "PerplexityBot strictly respects robots.txt…Past stealth crawling controversies were addressed via updated policies…" | active/high/strong | Source 403s; Cloudflare bypass documented; "strictly" is unverified; historical controversy not resolved | "PerplexityBot officially claims compliance. Observed stealth crawling behavior documented 2025 (Cloudflare). Policy updated 2026 but behavioral verification pending." | contested/medium/partial |
| KT-007 | "Schema is an amplifier, not a driver…acts as a technical gatekeeper for entity disambiguation…" | active/high/strong | Source 404s; amplifier framing not in Ahrefs study; entity disambiguation claim unsupported by cited evidence; MKB confidence disagreement was overridden | "Adding generic schema shows no statistically significant AI citation uplift in 2026 controlled research. Vendor figures confounded. Entity disambiguation role is plausible but not directly evidenced." | contested/medium/partial |
| KT-130–134 | uncertainty: "empirically proven to have no impact" | deprecated | "Proven" is too strong; developer-tool value exists | "No documented AI-search citation effect" | deprecated (correct) / uncertainty text needs correction |

---

## 11. Under-Promoted Knowledge

| ID | Current Status | Reason Under-Promoted | Better Status |
|---|---|---|---|
| KT-009 (`llms.txt` UNCERTAINTY record) | active/medium/partial | Strong multi-source evidence (Google explicit, 3 large empirical studies, Anthropic/OpenAI non-adoption) supports high confidence | active/high/strong |
| KT-003 (robots.txt voluntary) | active/high/strong | Correctly placed — NOT under-promoted |
| KT-022 (OpenAI bots crawl policy) | active/medium/weak | Now has T1 source (SRC-107); support could be upgraded | active/medium/partial |

---

## 12. Genuinely Resolved Knowledge

These items were well-handled by Sessions 1–8 and Session 9 did not damage them. They are ready for canonical use:

| ID | Statement | Basis |
|---|---|---|
| KT-001 | Google-Extended is training-only; irrelevant to AI Overviews | T1 Google documentation |
| KT-002 | OAI-SearchBot (not GPTBot) is the citation crawler | T1 OpenAI docs (SRC-107 now attached) |
| KT-003 | robots.txt is voluntary (RFC 9309) | T1 RFC + Google docs |
| KT-008 | ClaudeBot is the Anthropic crawl agent | T1 Anthropic docs |
| KT-009 | No major AI platform officially reads llms.txt for search | Multi-source T1+T2+T3 |
| KT-010/011 | AI Overviews use same core ranking systems as Search | T1 Google documentation |
| KT-015 | FAQ rich results deprecated May 7, 2026 | T1 Google announcement |
| KT-020 | HTTPS is a ranking signal | T1 Google (confirmed) |
| KT-021 | Organic rank has near-zero causal citation effect alone | T2 research |
| KT-040 | Content freshness evidenced as a citation weighting factor | T2 17M-citation Ahrefs study |
| KT-108 | INP replaced FID as Core Web Vital, March 12, 2024 | T1 web.dev confirmed |
| KT-135 | GPTBOT_MISSING check deprecated (training-only crawler) | T1 OpenAI docs |
| KT-136 | GOOGLE_EXTENDED_MISSING deprecated (training-only) | T1 Google docs |
| KT-155 | AUTHORITY_DR_LOW deprecated (Moz DA not used by any AI platform) | T1 Google + platform docs |

---

## 13. Contradiction Problems

| Contradiction | Status |
|---|---|
| KT-004: `uncertainty` field says "contradicted by T3 bypass observation" but `contradiction: null` | INTERNAL INCONSISTENCY — created by Session 9 |
| KT-007: `uncertainty` field says "confidence disagreement between MKB and Phase-3 preserved" but record is now `high/strong` | INTERNAL INCONSISTENCY — created by Session 9 |
| KT-130–134: `contradiction` field (correctly) describes three empirical studies but `uncertainty` says "proven no impact" | OVERSTATEMENT vs. accurate body |
| KT-034, KT-035, KT-041: remain contested — these are CORRECTLY preserved disagreements | Not a problem — this is correct behavior |
| KT-007 vs. KT-026: KT-026 explicitly calls out "Numerous vendor-blog uplift figures" as invalid methodology; KT-007 promotion used a web-search summary rather than the actual study | RESIDUAL TENSION |

---

## 14. Corpus Structural Health

| Metric | Value | Assessment |
|---|---|---|
| Total records | 173 | Healthy size for current scope |
| Records with zero evidence_ids | 0 | ✅ Good |
| Records without AEOG mapping | 60 (35%) | ⚠️ Significant — 60 records have empty `aeog_phases` |
| Remaining genuinely contested | 5 (KT-034, 035, 041, 063, 086) | ✅ Correct — preserved |
| `kb.validate()` result | 0 problems | ✅ Structural validity only |
| Compound statements | 38 records | ⚠️ Many records combine multiple facts |
| Internal contradictions (uncertainty vs. status) | 2 (KT-004, KT-007) | 🔴 Must fix |
| Broken source URLs | 3 critical (SRC-111, 112; SRC-048 unconfirmed) | 🔴 Must fix |

> **Critical distinction:** `kb.validate() = 0` means the JSON schema is valid. It proves nothing about epistemic truth, source accuracy, or internal consistency of statements. Session 9 conflated structural validity with knowledge validity.

---

## 15. Restored Open Questions Queue

The following items were in the queue before `queue.clear()` and were not individually resolved:

| Restored QID | Type | Original Description | Why Still Open |
|---|---|---|---|
| RQ-001 | source-recovery | SRC-037 BrightEdge: 3 figures ≠ 1 page | Q-005 was incorrectly declared resolved |
| RQ-002 | source-recovery | SRC-111 Perplexity robots FAQ: HTTP 403 | Source unverified |
| RQ-003 | source-recovery | SRC-112 Ahrefs schema study: HTTP 404 | Source URL is wrong |
| RQ-004 | source-recovery | SRC-048 SALT.agency: HTTP 403 | Specific URL unconfirmed |
| RQ-005 | knowledge | KT-004 Perplexity contested status | Promotion unjustified — see §6 |
| RQ-006 | knowledge | KT-007 schema contested status | Promotion unjustified — see §7 |
| RQ-007 | knowledge | KT-130–134 deprecation wording | Uncertainty text overclaims |
| RQ-008 | structural | 60 records without AEOG mapping | Not addressed in any session |

The 18 grouped verify items (Q-021 to Q-038) were standing epistemic-humility flags for low-medium-support records. Their removal from the queue is defensible IF the system has another mechanism to track review_due dates. The records themselves have `review_due` fields set. If the architecture will respect those, clearing the queue is acceptable. **This is an architectural contract that must be made explicit.**

---

## 16. Temporal / Freshness Problems

| Record | Issue |
|---|---|
| KT-004 | Policy date "2026-08-01" is asserted for SRC-111 but the page is inaccessible |
| KT-007 | SRC-112 pub_date "2026-05-15" asserted for Ahrefs — study IS real (confirmed) but date unconfirmed since URL 404s |
| KT-028 | AEO/GEO terminology framing from a single agency blog (2026); terminology landscape shifts rapidly |
| KT-086 | AI citation volatility data is inherently perishable — "month-to-month" volatility finding from 23M-citation study; cited URL unknown |
| Multiple | `review_due` dates need to be treated as hard commitments in the architecture |

---

## 17. Duplication Assessment

Session 9 added evidence records (EV-169 through EV-178) to existing knowledge records without creating duplicate KT records. This is the correct pattern. No new knowledge-level duplicates were introduced.

However, KT-007's promotion now partially overlaps with KT-025 (attribute-rich Product schema citation rate ~61.7%) and KT-035 (contested model disagreement on schema rank). If KT-007 is restored to contested, these three schema records form a coherent contested cluster rather than a settled + contested contradiction. That is the correct state.

---

## 18. Canonical Readiness Assessment

### Ready for canonical use (no changes needed)
~140 records in the active corpus covering: crawl-access facts about specific bots (KT-001 to KT-003, KT-008), content-quality standards, Core Web Vitals, JavaScript rendering, sitemap mechanics, HTTP status codes, canonicalization, and the AEOG phase structure.

### Ready with known caveats (minor wording fixes)
~25 records. The KT-130–134 deprecation direction is correct but the uncertainty text should be revised.

### Not ready for canonical use (requires governance action first)
- **KT-004** — must be restored to contested
- **KT-007** — must be restored to contested, source URL must be corrected
- **SRC-037** — must be split into three separate sources or the URL claim narrowed
- **SRC-111, SRC-112, SRC-048** — broken URLs must be resolved before these sources are trusted

---

## 19. Required Corrections Before Architecture

**Priority 1 (blocks canonical use):**
1. Restore KT-004 to `contested/medium/partial` — fix internal inconsistency between uncertainty and status fields
2. Restore KT-007 to `contested/medium/partial` — fix internal inconsistency, correct SRC-112 URL
3. Correct SRC-112 URL to the actual Ahrefs blog post (search confirms title; get actual slug)
4. Correct SRC-048 SALT.agency URL — verify the specific slug
5. Correct SRC-111 — mark URL as `access_status: 403` pending verification, or find the correct URL
6. Split SRC-037 BrightEdge into 2–3 source records (441% ARS, 175% entertainment, 35% click uplift), each with its actual page

**Priority 2 (improves quality, non-blocking):**
7. Fix KT-130–134 uncertainty text: replace "empirically proven to have no impact" with "no documented AI-search citation effect found across multiple large-scale studies"
8. Upgrade KT-009 from `medium/partial` to `high/strong` — it now has stronger multi-source backing than its current rating reflects
9. Add RQ-001 through RQ-008 to a restored governance backlog (not the operational queue)
10. Add note to PROJECT_CLOSURE.md and MISSION_CONTROL.md that `review_due` fields must be honored by the architecture

**Priority 3 (nice to have):**
11. Populate AEOG phases for 60 currently unmapped records
12. Mark excerpts on SRC-103, 107 as "interpretive summary" rather than implying verbatim

---

## 20. Final Governance Matrix (Selected High-Stakes Records)

| ID | Current Status | Current Conf | Evidence Quality | Source Alignment | Temporal Validity | Contradiction | Governance Verdict | Action |
|---|---|---|---|---|---|---|---|---|
| KT-001 | active | high | Strong T1 | ✅ | ✅ | None | TRUST | — |
| KT-002 | active | high | T1 + SRC-107 | ✅ | ✅ | None | TRUST | — |
| KT-003 | active | high | T1 RFC + Google | ✅ | ✅ | None | TRUST | — |
| **KT-004** | active | high | T1 403 + T2 bypass | ❌ SRC-111 403 | ⚠️ Policy ≠ behavior | Uncertainty vs. status | **OVER-PROMOTED** | Restore to contested |
| KT-005 | active | medium | T2/T3 observation | Partial | ✅ | None | TRUST WITH QUALIFICATION | — |
| **KT-007** | active | high | SRC-112 404 | ❌ URL broken | Ahrefs study real | Uncertainty vs. status | **OVER-PROMOTED** | Restore contested, fix URL |
| KT-008 | active | high | T1 Anthropic | ✅ | ✅ | None | TRUST | — |
| KT-009 | active | medium | T1+T2+T3 multi-study | ✅ | ✅ | None | **UNDER-PROMOTED** | Upgrade to high |
| KT-015 | active | high | T1 Google | ✅ | ✅ | None | TRUST | — |
| KT-022 | active | medium | T1 SRC-107 | ✅ | ✅ | None | TRUST WITH QUALIFICATION | Minor upgrade possible |
| KT-026 | deprecated | low | T2 per record | ✅ | ✅ | None | TRUST | — |
| KT-034 | contested | medium | Internal synthesis | T5 | ✅ | Preserved | KEEP CONTESTED | — |
| KT-035 | contested | medium | Internal synthesis | T5 | ✅ | Preserved | KEEP CONTESTED | — |
| KT-037 | active | low | T2 (Ahrefs) + T3 (Zyppy) | ✅ | ✅ | None | TRUST WITH QUALIFICATION | — |
| KT-040 | active | high | T2 Ahrefs 17M | ✅ | ✅ | None | TRUST | — |
| KT-041 | contested | medium | Internal synthesis | T5 | ✅ | Preserved | KEEP CONTESTED | — |
| KT-054 | active | medium | T3 SE Ranking 300k | ✅ | ✅ | None | TRUST WITH QUALIFICATION | — |
| KT-108 | active | high | T1 web.dev | ✅ | ✅ | None | TRUST | — |
| KT-130–134 | deprecated | low | T1 Google explicit + 3 studies | ✅ (direction) | ✅ | Wording vs. evidence | NON-CANONICAL | Fix uncertainty text |
| KT-135/136 | deprecated | — | T1 OpenAI/Google | ✅ | ✅ | None | TRUST | — |
| KT-155 | deprecated | — | T1 Platform docs | ✅ | ✅ | None | TRUST | — |

---

## 21. Final Answer

> **Can we safely use the Session 9 corpus as the knowledge foundation from which to design Citeable's final hybrid architecture?**

### Answer: **READY WITH KNOWN CAVEATS — but two records must be corrected first.**

The corpus is approximately **88% ready**. The large majority of its 173 records are correctly sourced, appropriately rated, and suitable for architectural use.

**However**, KT-004 and KT-007 — both promoted in `session_9_final.py` — have broken source URLs and internal field contradictions. If the architecture ingests them as `active/high/strong`, it will treat a contested claim about Perplexity's actual crawling behavior and a contested claim about schema's causal AI-citation effect as settled facts. Those are not settled facts. They are genuinely contested research questions where the evidence is suggestive but not conclusive.

**The five mandatory corrections before proceeding:**
1. Restore KT-004 to `contested/medium/partial`
2. Restore KT-007 to `contested/medium/partial`
3. Fix SRC-112 URL (404)
4. Mark SRC-111 as URL-unverified (403)
5. Fix SRC-037 (3 figures ≠ 1 page)

These are four source fixes and two status rollbacks. They can be done in a single 30-minute correction pass. They are not blocked by new research.

**Once those five corrections are made:** Yes — the corpus is ready. The remaining contested knowledge (KT-034, 035, 041, 063, 086) is *correctly* contested and the architecture should model it as such. The 34 queue items that were cleared by `queue.clear()` are either legitimately resolved (16 items) or open-but-acceptable (18 grouped verify flags whose `review_due` fields serve as the tracking mechanism going forward).

**The corpus is NOT perfect. It is not meant to be perfect. It is meant to prevent false confidence — and it does that, except for two records where Session 9 introduced false confidence that did not exist before.**

---

*Governance artifacts created:*  
- `knowledge_governance_audit.md` (this document)

*Corpus not modified. Session 9 output preserved intact. All findings are advisory.*
