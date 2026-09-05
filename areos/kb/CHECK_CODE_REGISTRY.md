# CHECK CODE REGISTRY

All check codes in the Citeable runtime, with their current knowledge status.

**Deprecated check codes must not be presented as actionable findings to users.**

| Priority | Check Code | Status | GUIDANCE Record | Notes |
|---|---|---|---|---|
| 1 | `CRAWLER_FULLY_BLOCKED` | ✅ Has GUIDANCE | KT-124 |  |
| 2 | `LLMS_TXT_MISSING` | ⛔ DEPRECATED | KT-130 | Deprecated: no documented AI-search citation effect found |
| 2 | `NOSNIPPET_BLOCKING_AI` | ✅ Has GUIDANCE | KT-149 |  |
| 3 | `JSON_PARSE_FAILURE` | ✅ Has GUIDANCE | KT-125 |  |
| 3 | `MISSING_TYPE` | ✅ Has GUIDANCE | KT-126 |  |
| 4 | `MISSING_REQUIRED_FIELD` | ✅ Has GUIDANCE | KT-127 |  |
| 4 | `EXTRACTABILITY_NONE` | ✅ Has GUIDANCE | KT-128 |  |
| 4 | `ANSWER_NOT_NEAR_TOP` | ✅ Has GUIDANCE | KT-150 |  |
| 4 | `AUTHORITY_DR_LOW` | ⛔ DEPRECATED | KT-155 | Deprecated: references Moz DR, not used by any AI platform |
| 5 | `EXTRACTABILITY_LOW` | ✅ Has GUIDANCE | KT-129 |  |
| 5 | `REFERRING_DOMAINS_CRITICAL` | ✅ Has GUIDANCE | KT-156 |  |
| 6 | `CITATION_NOT_OBSERVED` | ✅ Has GUIDANCE | KT-137 |  |
| 6 | `ANSWER_NOT_SELF_CONTAINED` | ✅ Has GUIDANCE | KT-151 |  |
| 7 | `MISSING_RECOMMENDED_FIELD` | ✅ Has GUIDANCE | KT-140 |  |
| 7 | `ANSWER_NOT_FACTUALLY_SPECIFIC` | ✅ Has GUIDANCE | KT-152 |  |
| 7 | `WIKIPEDIA_ENTITY_MISSING` | ✅ Has GUIDANCE | KT-157 |  |
| 8 | `UNKNOWN_FIELD` | ✅ Has GUIDANCE | KT-141 |  |
| 8 | `UNKNOWN_SCHEMA_TYPE` | ✅ Has GUIDANCE | KT-142 |  |
| 8 | `GOOGLE_EXTENDED_MISSING` | ⛔ DEPRECATED | KT-135 | Deprecated: conflates training crawler with search crawler |
| 8 | `GPTBOT_MISSING` | ⛔ DEPRECATED | KT-136 | Deprecated: conflates training crawler with search crawler |
| 8 | `INVALID_CRAWL_DELAY` | ✅ Has GUIDANCE | KT-146 |  |
| 8 | `NO_LIST_OR_TABLE` | ✅ Has GUIDANCE | KT-153 |  |
| 8 | `BRAND_MENTIONS_STAGNANT` | ✅ Has GUIDANCE | KT-158 |  |
| 9 | `LLMS_TXT_MISSING_SECTION` | ⛔ DEPRECATED | KT-132 | Deprecated: no documented AI-search citation effect found |
| 9 | `LLMS_TXT_NO_LINKS` | ⛔ DEPRECATED | KT-133 | Deprecated: no documented AI-search citation effect found |
| 9 | `LLMS_TXT_EMPTY_CONTENT` | ⛔ DEPRECATED | KT-134 | Deprecated: no documented AI-search citation effect found |
| 9 | `CRAWLER_PARTIAL` | ✅ Has GUIDANCE | KT-143 |  |
| 10 | `EXTRACTABILITY_MEDIUM` | ✅ Has GUIDANCE | KT-147 |  |
| 11 | `CITATION_OBSERVED` | ✅ Has GUIDANCE | KT-138 |  |
| 12 | `ANSWER_FORMAT_GOOD` | ✅ Has GUIDANCE | KT-154 |  |
| 12 | `AUTHORITY_PROFILE_GOOD` | ✅ Has GUIDANCE | KT-159 |  |
| 12 | `CRAWLER_ALLOWED` | ✅ Has GUIDANCE | KT-144 |  |
| 12 | `EXTRACTABILITY_HIGH` | ✅ Has GUIDANCE | KT-148 |  |
| 12 | `CITATION_WHY_UNKNOWN` | ✅ Has GUIDANCE | KT-139 |  |
| 13 | `NO_DIRECTIVE` | ✅ Has GUIDANCE | KT-145 |  |

## Check codes in the DB (check_code_mappings) but missing from PRIORITY_SCORES

- `LLMS_TXT_MISSING_H1` — in DB but no priority score assigned

## Legacy numeric check codes (C0NN series)

These are an older internal check-code naming scheme, distinct from the human-readable codes
above. They are still actively referenced via `check_links` on 14 GUIDANCE records
(KT-160 through KT-173) and are present in `context/check_code_to_knowledge_map.json`. Added
here 2026-08-30 (Session 14 validation pass) — they were previously undocumented in this
registry, which caused the map's total code count (50) to appear inconsistent with this
table's count (35) during audit. Both counts are correct; this table was simply incomplete.

| Legacy Code | Status | GUIDANCE Record | Notes |
|---|---|---|---|
| `C052` | ✅ Has GUIDANCE | KT-160 | Fix Confirmed Asset Blocking |
| `C053` | ✅ Has GUIDANCE | KT-161 | Fix Schema Semantic Honesty Issues |
| `C056` | ✅ Has GUIDANCE | KT-162 | Resolve Entity Disambiguation |
| `C058` | ✅ Has GUIDANCE | KT-163 | Add HTML Fallbacks for Embedded Content |
| `C061` | ✅ Has GUIDANCE | KT-164 | Restructure Page Layout for AI Extraction |
| `C062` | ✅ Has GUIDANCE | KT-165 | Strengthen E-E-A-T Signals |
| `C072` | ✅ Has GUIDANCE | KT-166 | Refine Citation Prompt Set |
| `C073` | ✅ Has GUIDANCE | KT-167 | Write Root Cause Diagnosis |
| `C074` | ✅ Has GUIDANCE | KT-168 | Correct AI Hallucinations About Brand |
| `C077` | ✅ Has GUIDANCE | KT-169 | Address Brand Framing Issues |
| `C078` | ✅ Has GUIDANCE | KT-170 | Assess and Respond to Zero-Click Threat |
| `C079` | ✅ Has GUIDANCE | KT-171 | Implement or Fix Speakable Schema |
| `C082` | ✅ Has GUIDANCE | KT-172 | Execute Digital-PR Gap Strategy |
| `C090` | ✅ Has GUIDANCE | KT-173 | Write Root Cause Diagnosis Narrative |
