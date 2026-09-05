---
last_verified: 2026-09-02
verified_against: HEAD
owner: system
status: current
---
# Repository / Code Map

## Annotated File Tree

```text
areos/
├── api/
│   └── routers/
├── auditors/
├── cli/
├── db/
│   └── schema/
├── kb/
│   └── corpus/
├── llm/
│   └── providers/
├── services/
├── ui/
│   └── docs/
│       └── internal/
└── util/
```

### `areos/api`
- **Purpose**: REST API and Routers
- **Responsibilities**: Exposes HTTP endpoints for all services.
- **Dependencies**: areos/services, areos/db
- **Related tests**: `tests/test_api*.py`
- **Related API routes**: N/A

### `areos/auditors`
- **Purpose**: Audit and Scoring Logic
- **Responsibilities**: Contains deterministic, hybrid, and AI auditors.
- **Dependencies**: areos/llm, areos/db, areos/services
- **Related tests**: `tests/test_auditors*.py`
- **Related API routes**: /api/audit/*

### `areos/cli`
- **Purpose**: Command Line Interfaces
- **Responsibilities**: CLI tools for administrative and local tasks.
- **Dependencies**: areos/services, areos/util
- **Related tests**: `tests/test_cli*.py`
- **Related API routes**: N/A

### `areos/db`
- **Purpose**: Database Models and Access
- **Responsibilities**: SQLAlchemy models and database connection utilities.
- **Dependencies**: None
- **Related tests**: `tests/test_db*.py`
- **Related API routes**: N/A

### `areos/kb`
- **Purpose**: Knowledge Base
- **Responsibilities**: Stores and manages domain knowledge and corpora.
- **Dependencies**: areos/util
- **Related tests**: `tests/test_kb*.py`
- **Related API routes**: /api/knowledge/*

### `areos/llm`
- **Purpose**: LLM Integrations
- **Responsibilities**: Wraps external LLM APIs and prompt management.
- **Dependencies**: areos/util
- **Related tests**: `tests/test_llm*.py`
- **Related API routes**: N/A

### `areos/services`
- **Purpose**: Business Logic Layer
- **Responsibilities**: Core services coordinating models, auditors, and LLMs.
- **Dependencies**: areos/db, areos/auditors, areos/llm
- **Related tests**: `tests/test_services*.py`
- **Related API routes**: Called by API routers

### `areos/ui`
- **Purpose**: Frontend UI
- **Responsibilities**: Static assets, templates, and UI logic.
- **Dependencies**: areos/api
- **Related tests**: `tests/test_ui*.py`
- **Related API routes**: N/A

### `areos/util`
- **Purpose**: Utilities
- **Responsibilities**: Shared helper functions.
- **Dependencies**: None
- **Related tests**: `tests/test_util*.py`
- **Related API routes**: N/A

## Directory Deep Dives
### areos/api
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `dependencies.py` | 2328 | Exports: get_db, verify_admin, get_client_keys... | def get_db(), def verify_admin(), def get_client_keys() |
| `error_codes.py` | 850 | Exports: ErrorCode, Severity... | class ErrorCode, class Severity |
| `main.py` | 10312 | Exports: _PayloadTooLarge, BodySizeLimitMiddleware... | class _PayloadTooLarge, class BodySizeLimitMiddleware |
| `__init__.py` | 0 | Utility script or missing docstring |  |
| `routers/approvals.py` | 6216 | Exports: ApprovalAction, PendingApprovalsResponse, get_pending_approvals... | class ApprovalAction, class PendingApprovalsResponse, def get_pending_approvals(), def process_approval() |
| `routers/audit.py` | 34060 | Exports: AuditRunPayload, OrchestratedAuditPayload, AuditRunModel... | class AuditRunPayload, class OrchestratedAuditPayload, class AuditRunModel, class AuditRunListResponse, class FindingModel |
| `routers/byok.py` | 8921 | byok.py — Standalone BYOK Diagnostic & Verification Router (Domain Isolation) | def check_byok_rate_limit(), class ByokVerifyRequest, def verify_api_key(), def _verify_api_key_cached() |
| `routers/claims.py` | 5498 | Exports: ClaimModel, ClaimResponse, IngestionPayload... | class ClaimModel, class ClaimResponse, class IngestionPayload, def get_claims(), def ingest_claim() |
| `routers/knowledge.py` | 8753 | Exports: KnowledgeItem, EvidenceItem, SourceItem... | class KnowledgeItem, class EvidenceItem, class SourceItem, class KnowledgeDetail, class KnowledgeListResponse |
| `routers/prompts.py` | 2966 | Exports: PromptSetPayload, PromptListResponse, list_prompts... | class PromptSetPayload, class PromptListResponse, def list_prompts(), def create_prompt(), def delete_prompt() |
| `routers/reports.py` | 5403 | Exports: ReportResponse, RemediationPlanResponse, get_final_report... | class ReportResponse, class RemediationPlanResponse, def get_final_report(), def get_remediation_plan() |
| `routers/synthesis.py` | 3396 | Exports: PromptUpdate, get_synthesis_prompts, update_synthesis_prompt... | class PromptUpdate, def get_synthesis_prompts(), def update_synthesis_prompt(), def reset_synthesis_prompt() |
| `routers/verdicts.py` | 1853 | Exports: ManualVerdictPayload, submit_verdict... | class ManualVerdictPayload, def submit_verdict() |
| `routers/__init__.py` | 0 | Utility script or missing docstring |  |

### areos/auditors
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `audit_orchestrator.py` | 44904 | [AI] Exports: _fetch_robots_txt, _fetch_page, _extract_json_ld_blocks... | def _fetch_robots_txt(), def _fetch_page(), def _extract_json_ld_blocks(), def _validate_schema_from_html(), def run_orchestrated_audit() |
| `authority_auditor.py` | 10297 | [AI] Exports: AuthorityIssue, AuthorityAuditResult, fetch_open_pagerank... | class AuthorityIssue, class AuthorityAuditResult, def fetch_open_pagerank(), def fetch_moz_metrics(), def fetch_ahrefs_metrics() |
| `citation_sampler.py` | 14730 | [AI] Exports: CitationObservation, CitationSampleResult, _query_perplexity... | class CitationObservation, class CitationSampleResult, def _query_perplexity(), def _query_gemini_grounded(), def load_active_prompt_set() |
| `cloaking_detector.py` | 9781 | [AI] Exports: CloakingIssue, CloakingResult, _extract_text... | class CloakingIssue, class CloakingResult, def _extract_text(), def _find_missing_elements(), def audit_cloaking() |
| `competitor_analyzer.py` | 5640 | [AI] Exports: CompetitorIssue, CompetitorAnalysisResult, _extract_schema_types_from_html... | class CompetitorIssue, class CompetitorAnalysisResult, def _extract_schema_types_from_html(), def analyze_competitors() |
| `content_format_auditor.py` | 8204 | [AI] Exports: FormatIssue, FormatAuditResult, extract_text_blocks... | class FormatIssue, class FormatAuditResult, def extract_text_blocks(), def audit_page_format() |
| `entity_verifier.py` | 16453 | [AI] Exports: EntityIssue, EntityAuditResult, _extract_name... | class EntityIssue, class EntityAuditResult, def _extract_name(), def _extract_same_as(), def _extract_types() |
| `extractability_judge.py` | 9669 | [AI] Exports: ExtractabilityResult, build_signals, _heuristic_check... | class ExtractabilityResult, def build_signals(), def _heuristic_check(), def _call_llm_judge(), def judge_page() |
| `findings_to_claims.py` | 8502 | [AI] Exports: _default_db_path, get_check_code_mappings, WiredFinding... | def _default_db_path(), def get_check_code_mappings(), class WiredFinding, def _lookup_claim(), def wire_finding() |
| `freshness_auditor.py` | 9994 | [AI] Exports: FreshnessIssue, FreshnessAuditResult, parse_date_string... | class FreshnessIssue, class FreshnessAuditResult, def parse_date_string(), def extract_dates_from_json_ld(), def extract_dates_from_html() |
| `manual_findings_template.py` | 7321 | [AI] Exports: ParseError, ManualFinding, generate_template... | class ParseError, class ManualFinding, def generate_template(), def parse_manual_findings(), def parse_from_db() |
| `media_blindness_auditor.py` | 6951 | [AI] Exports: MediaIssue, MediaAuditResult, _count_body_words_outside_media... | class MediaIssue, class MediaAuditResult, def _count_body_words_outside_media(), def audit_media_blindness() |
| `multipage_auditor.py` | 6101 | [AI] Exports: MultiPageIssue, MultiPageAuditResult, _extract_page_text... | class MultiPageIssue, class MultiPageAuditResult, def _extract_page_text(), def audit_multi_page() |
| `qa_gate.py` | 4438 | [AI] Exports: QAResult, _lookup_claim_status, run_qa_gate... | class QAResult, def _lookup_claim_status(), def run_qa_gate(), def validate_plan() |
| `redirect_auditor.py` | 8687 | [AI] Exports: RedirectIssue, RedirectAuditResult, _has_meta_noindex... | class RedirectIssue, class RedirectAuditResult, def _has_meta_noindex(), def _extract_canonical_href(), def _normalize_for_comparison() |
| `rendering_auditor.py` | 6175 | [AI] Exports: RenderingIssue, RenderingAuditResult, _strip_html... | class RenderingIssue, class RenderingAuditResult, def _strip_html(), def audit_js_rendering() |
| `robots_checker.py` | 12847 | [AI] Exports: CrawlerDirective, RobotsIssue, RobotsResult... | class CrawlerDirective, class RobotsIssue, class RobotsResult, class LlmsTxtSection, class LlmsTxtResult |
| `schema_validator.py` | 16159 | [AI] Exports: SchemaIssue, ValidationResult, _extract_schema_claims... | class SchemaIssue, class ValidationResult, def _extract_schema_claims(), def _is_empty(), def validate_single() |
| `scoring.py` | 15035 | [AI] areos/auditors/scoring.py | class LayerScore, class ScorecardResult, def compute_layered_score(), def count_severity() |
| `sitemap_auditor.py` | 14372 | [AI] Exports: SitemapIssue, SitemapAuditResult, _local_tag... | class SitemapIssue, class SitemapAuditResult, def _local_tag(), def _extract_sitemaps_from_robots(), def _parse_sitemap_xml() |
| `synthesis_engine.py` | 20422 | [AI] Exports: _load_priority_scores, _load_remediation_text, Recommendation... | def _load_priority_scores(), def _load_remediation_text(), class Recommendation, class RemediationPlan, def _build_automated_recommendations() |
| `__init__.py` | 0 | [Deterministic] Utility script or missing docstring |  |

### areos/cli
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `approve.py` | 7537 | Exports: apply_insert, apply_update, apply_flag_for_review... | def apply_insert(), def apply_update(), def apply_flag_for_review(), def main() |
| `critique.py` | 1894 | Exports: main... | def main() |
| `critique_changelog.py` | 2760 | Exports: main... | def main() |
| `diff.py` | 3307 | Exports: main... | def main() |
| `report.py` | 16213 | Exports: AuditRunSummary, TriggeredCard, select_triggered_cards... | class AuditRunSummary, class TriggeredCard, def select_triggered_cards(), def generate_gap_report(), def main() |
| `research.py` | 6086 | Exports: main, _dry_run, _info... | def main(), def _dry_run(), def _info(), def _err() |
| `__init__.py` | 0 | Utility script or missing docstring |  |

### areos/db
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `connection.py` | 6078 | Exports: get_db_path, get_connection, _open_connection... | def get_db_path(), def get_connection(), def _open_connection(), def close_all_connections(), def apply_schema() |
| `context.py` | 2453 | Exports: write_as... | def write_as() |
| `ingest_claims.py` | 9576 | Exports: _load_source_rows, _build_row, ingest... | def _load_source_rows(), def _build_row(), def ingest(), def _print_summary() |
| `kb_version.py` | 1657 | Exports: increment_kb_version, get_kb_version... | def increment_kb_version(), def get_kb_version() |
| `lint.py` | 6968 | Exports: lint_claim... | def lint_claim() |
| `migrate_audit_tables.py` | 8569 | Exports: _split_sql_statements, migrate... | def _split_sql_statements(), def migrate() |
| `schema.sql` | 22719 | Non-python file |  |
| `stage_normalization.py` | 2582 | Exports: _load_aliases, normalize_stage_id, reset_cache... | def _load_aliases(), def normalize_stage_id(), def reset_cache() |
| `__init__.py` | 0 | Utility script or missing docstring |  |
| `schema/artifacts.py` | 15981 | Utility script or missing docstring |  |
| `schema/__init__.py` | 0 | Utility script or missing docstring |  |

### areos/kb
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `build_kb.py` | 17785 | Exports: handle_claims_view, parse_jsonl, build... | def handle_claims_view(), def parse_jsonl(), def build(), def embed_corpus() |
| `CHECK_CODE_REGISTRY.md` | 4732 | Non-python file |  |
| `check_code_to_knowledge_map.json` | 9155 | Data/Config file |  |
| `DECISIONS.md` | 27944 | Non-python file |  |
| `embeddings.py` | 6177 | Exports: EmbeddingUnavailable, embed, get_active_model... | class EmbeddingUnavailable, def embed(), def get_active_model(), def cosine_similarity(), def _build_embed_waterfall() |
| `GOVERNANCE_RULES.md` | 5660 | Non-python file |  |
| `models.py` | 2788 | Exports: GuidanceDetail, KnowledgeRecord, EvidenceRecord... | class GuidanceDetail, class KnowledgeRecord, class EvidenceRecord, class SourceRecord, class CheckCodeMapping |
| `README.md` | 3411 | Non-python file |  |
| `router.py` | 12973 | Exports: get_thresholds_for_model, resolve, cross_phase_search... | def get_thresholds_for_model(), def resolve(), def cross_phase_search(), def _load_record(), def _build_resolution() |
| `__init__.py` | 200 | areos.kb — Citeable Hybrid Knowledge Architecture |  |
| `corpus/changelog.jsonl` | 96929 | Data/Config file |  |
| `corpus/evidence.jsonl` | 65601 | Data/Config file |  |
| `corpus/governance_backlog.jsonl` | 5542 | Data/Config file |  |
| `corpus/knowledge.jsonl` | 410084 | Data/Config file |  |
| `corpus/relationships.jsonl` | 34278 | Data/Config file |  |
| `corpus/sources.jsonl` | 77995 | Data/Config file |  |

### areos/llm
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `synthesis_pipeline.py` | 14828 | Exports: _load_prompts, _build_synthesizer_input, _parse_flags... | def _load_prompts(), def _build_synthesizer_input(), def _parse_flags(), def _count_serious_flags(), def run_llm_synthesis() |
| `__init__.py` | 0 | Utility script or missing docstring |  |
| `providers/__init__.py` | 31045 | Exports: _NotConfigured, _RateLimit, _AuthFailure... | class _NotConfigured, class _RateLimit, class _AuthFailure, class _ProviderUnavailable, def complete() |

### areos/services
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `adversarial_service.py` | 2803 | Exports: generate_critique... | def generate_critique() |
| `auto_apply.py` | 1634 | Exports: is_auto_apply_eligible, record_approval, record_rejection... | def is_auto_apply_eligible(), def record_approval(), def record_rejection() |
| `cache.py` | 1888 | Exports: TTLCache, ttl_cache... | class TTLCache, def ttl_cache() |
| `diff_service.py` | 6867 | Exports: generate_changelog, _fetch_existing_claims, _classify_candidate... | def generate_changelog(), def _fetch_existing_claims(), def _classify_candidate() |
| `report_generator.py` | 14107 | report_generator.py | def get_report_data(), def build_html_report(), def build_markdown_report(), def assemble_markdown_report() |
| `research_service.py` | 15502 | Exports: run_research, _load_sources_yaml, _fetch_text... | def run_research(), def _load_sources_yaml(), def _fetch_text(), def _fetch_via_jina(), def _fetch_via_requests() |
| `run_state.py` | 5785 | Exports: get_wizard_cards_for_run, get_run_completeness, get_persisted_synthesis... | def get_wizard_cards_for_run(), def get_run_completeness(), def get_persisted_synthesis(), def persist_synthesis() |
| `sources.py` | 45138 | Exports: load_all_sources, get_sources_for_claim, get_ranked_sources... | def load_all_sources(), def get_sources_for_claim(), def get_ranked_sources() |
| `verdict_service.py` | 590 | Exports: get_verdicts_by_card... | def get_verdicts_by_card() |
| `__init__.py` | 0 | Utility script or missing docstring |  |

### areos/ui
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `api.js` | 3362 | Frontend Asset | N/A |
| `app.js` | 18879 | Frontend Asset | N/A |
| `approvals.html` | 10204 | Frontend Asset | N/A |
| `approvals.js` | 23131 | Frontend Asset | N/A |
| `auth.js` | 2422 | Frontend Asset | N/A |
| `byok.html` | 3581 | Frontend Asset | N/A |
| `byok.js` | 20670 | Frontend Asset | N/A |
| `case_study.html` | 5771 | Frontend Asset | N/A |
| `CHANGELOG.md` | 7236 | Non-python file |  |
| `claims_browser.html` | 9380 | Frontend Asset | N/A |
| `context.js` | 1178 | Frontend Asset | N/A |
| `docs.html` | 2925 | Frontend Asset | N/A |
| `docs.js` | 33199 | Frontend Asset | N/A |
| `dom.js` | 5453 | Frontend Asset | N/A |
| `favicon.svg` | 1352 | Non-python file |  |
| `guided_review.js` | 32385 | Frontend Asset | N/A |
| `help.js` | 11929 | Frontend Asset | N/A |
| `identity.js` | 5466 | Frontend Asset | N/A |
| `index.css` | 34596 | Frontend Asset | N/A |
| `index.html` | 36079 | Frontend Asset | N/A |
| `knowledge_explorer.html` | 13040 | Frontend Asset | N/A |
| `knowledge_explorer.js` | 15829 | Frontend Asset | N/A |
| `manual_review.html` | 758 | Frontend Asset | N/A |
| `manual_review.js` | 15022 | Frontend Asset | N/A |
| `nav.js` | 19805 | Frontend Asset | N/A |
| `outcome.html` | 759 | Frontend Asset | N/A |
| `outcome.js` | 6538 | Frontend Asset | N/A |
| `prompts.html` | 5484 | Frontend Asset | N/A |
| `prompts.js` | 4650 | Frontend Asset | N/A |
| `remediation.html` | 759 | Frontend Asset | N/A |
| `remediation.js` | 12702 | Frontend Asset | N/A |
| `studio.js` | 64966 | Frontend Asset | N/A |
| `synthesis_prompts.html` | 4526 | Frontend Asset | N/A |
| `synthesis_prompts.js` | 4982 | Frontend Asset | N/A |
| `assets/help-byok.png` | 108054 | Binary or unreadable |  |
| `assets/help-dashboard.png` | 79954 | Binary or unreadable |  |
| `assets/help-report-fallback.png` | 79673 | Binary or unreadable |  |
| `assets/help-report.png` | 78953 | Binary or unreadable |  |
| `assets/help-running.png` | 79620 | Binary or unreadable |  |
| `docs/ai-architecture.md` | 8162 | Non-python file |  |
| `docs/api.md` | 8368 | Non-python file |  |
| `docs/changelog.md` | 7073 | Non-python file |  |
| `docs/external_legacy.md` | 63560 | Non-python file |  |
| `docs/index.md` | 5905 | Non-python file |  |
| `docs/internal_legacy.md` | 61240 | Non-python file |  |
| `docs/knowledge.md` | 6657 | Non-python file |  |
| `docs/lifecycle.md` | 10344 | Non-python file |  |
| `docs/limitations.md` | 6660 | Non-python file |  |
| `docs/review.md` | 6503 | Non-python file |  |
| `docs/scoring.md` | 9420 | Non-python file |  |
| `docs/security.md` | 7507 | Non-python file |  |
| `docs/testing.md` | 6019 | Non-python file |  |
| `docs/internal/00-orientation.md` | 6113 | Non-python file |  |
| `docs/internal/02-repository-map.md` | 32725 | Non-python file |  |
| `docs/internal/04-data-model.md` | 10995 | Non-python file |  |
| `docs/internal/05-evidence-findings.md` | 10386 | Non-python file |  |
| `vendor/marked.min.js` | 43821 | Frontend Asset | N/A |
| `vendor/mermaid.min.js` | 3566058 | Frontend Asset | N/A |

### areos/util
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `clock.py` | 443 | Exports: utc_now_iso, utc_today_iso... | def utc_now_iso(), def utc_today_iso() |
| `html_cleaner.py` | 1046 | Exports: clean_html_text... | def clean_html_text() |
| `idempotency.py` | 2324 | Exports: with_idempotency... | def with_idempotency() |
| `logging_config.py` | 1122 | Exports: JsonFormatter, setup_logging... | class JsonFormatter, def setup_logging() |
| `sanitize.py` | 368 | Exports: sanitize_text... | def sanitize_text() |
| `ssrf.py` | 5968 | Exports: TargetIPAdapter, _validate_ip, resolve_and_validate... | class TargetIPAdapter, def _validate_ip(), def resolve_and_validate(), def validate_domain_ssrf(), def safe_get() |
| `__init__.py` | 13 | Utility script or missing docstring |  |

### scripts
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `backup_db.py` | 2372 | scripts/backup_db.py — Online SQLite Backup Utility (TASK-10 / DEC-10) | def backup_database() |
| `verify_kb_semantic_parity.py` | 3380 | scripts/verify_kb_semantic_parity.py | def verify_parity() |

### tests
| File | Size (B) | Purpose | Exports/Provides |
|---|---|---|---|
| `conftest.py` | 1051 | Exports: _isolate_test_db... | def _isolate_test_db() |
| `test_adversarial_stream_fuzzing.py` | 2653 | Exports: test_streaming_chunked_boundary_exceeded, test_malformed_json_returns_422_or_400, test_special_characters_in_query_params... | def test_streaming_chunked_boundary_exceeded(), def test_malformed_json_returns_422_or_400(), def test_special_characters_in_query_params(), def test_provider_waterfall_global_time_budget_enforcement() |
| `test_ci_semantic_parity.py` | 259 | Exports: test_ci_semantic_parity_gate_passes... | def test_ci_semantic_parity_gate_passes() |
| `test_cloaking_detector.py` | 3647 | Exports: test_cloaking_detected, test_cloaking_suspected, test_bot_blocked_http... | def test_cloaking_detected(), def test_cloaking_suspected(), def test_bot_blocked_http(), def test_cloaking_pass(), def test_cloaking_fetch_failed() |
| `test_competitor_analyzer.py` | 5025 | Exports: TestT701CompetitorAnalyzer... | class TestT701CompetitorAnalyzer |
| `test_db_concurrency_stress.py` | 2506 | Exports: test_concurrent_txn_context_isolation_multithreaded, test_concurrent_reads_during_writes_wal_mode... | def test_concurrent_txn_context_isolation_multithreaded(), def test_concurrent_reads_during_writes_wal_mode() |
| `test_entity_verifier.py` | 5622 | Exports: test_no_entities_found, test_entity_name_missing, test_sameas_missing... | def test_no_entities_found(), def test_entity_name_missing(), def test_sameas_missing(), def test_sameas_incomplete(), def test_wikidata_missing() |
| `test_freshness_auditor.py` | 2798 | Exports: test_date_missing, test_freshness_ok_json_ld, test_content_aging... | def test_date_missing(), def test_freshness_ok_json_ld(), def test_content_aging(), def test_content_stale(), def test_html_meta_and_time_tags() |
| `test_kb_build_schema_integrity.py` | 936 | Exports: test_kb_build_preserves_kb_meta_check_constraint... | def test_kb_build_preserves_kb_meta_check_constraint() |
| `test_kb_parity.py` | 6390 | Exports: db_path, conn, TestCheckCodeParity... | def db_path(), def conn(), class TestCheckCodeParity, class TestClaimsView, class TestWireFinding |
| `test_kb_parity_gate.py` | 1584 | Failed to parse python file |  |
| `test_knowledge_api.py` | 1506 | Exports: client, test_knowledge_list, test_knowledge_stats... | def client(), def test_knowledge_list(), def test_knowledge_stats(), def test_knowledge_detail() |
| `test_media_blindness.py` | 2497 | Exports: test_iframe_heavy, test_images_missing_alt, test_images_with_alt... | def test_iframe_heavy(), def test_images_missing_alt(), def test_images_with_alt(), def test_video_no_transcript(), def test_video_with_transcript() |
| `test_multipage_auditor.py` | 5455 | Exports: TestT601MultiPageAuditor... | class TestT601MultiPageAuditor |
| `test_phase0_fixes.py` | 14247 | Exports: TestT001ManualRemediationText, TestT002RemediationTextNameError, TestT003PriorityScoresFallback... | class TestT001ManualRemediationText, class TestT002RemediationTextNameError, class TestT003PriorityScoresFallback, class TestT004HardcodedToken, class TestT005ClaimsLegacyIdempotency |
| `test_phase1_fetch.py` | 9048 | Exports: TestT101FetchPage, TestT102ExtractSchemaClaims, TestT103SingleFetchFlow... | class TestT101FetchPage, class TestT102ExtractSchemaClaims, class TestT103SingleFetchFlow, class TestT104FormatAuditResultField |
| `test_phase2_auditors.py` | 11458 | Exports: TestT201FreshnessAuditor, TestT202RedirectAuditor, TestT203CloakingDetector... | class TestT201FreshnessAuditor, class TestT202RedirectAuditor, class TestT203CloakingDetector, class TestT204EntityVerifier, class TestT205MediaBlindness |
| `test_phase3_kb_scoring.py` | 8536 | Exports: TestT301LayerDeductions, TestT302AccessGate, TestT303KnowledgeMap... | class TestT301LayerDeductions, class TestT302AccessGate, class TestT303KnowledgeMap, class TestT304ActionSnippets |
| `test_phase4_enhancements.py` | 5686 | Exports: TestT401ContentFormatAuditor, TestT402RobotsSitemapExtraction... | class TestT401ContentFormatAuditor, class TestT402RobotsSitemapExtraction |
| `test_qa2_phase_r1.py` | 3863 | Phase R1 Regression Suite: Security and Boundary Hardening (TR-101 to TR-105). | class TestR1SSRFAndSecurity, class TestR1SitemapBounds, class TestR1FrontendXSSProtection |
| `test_qa2_phase_r2.py` | 5294 | Phase R2 Regression Suite: Knowledge Base and RAG Optimization (TR-201 to TR-205). | class TestR2RAGCandidatesPool, class TestR2BindingsAndScoring |
| `test_qa2_phase_r3.py` | 6524 | Phase R3 Regression Suite: API, Database & Concurrency Safety (TR-301 to TR-305). | class TestR3DBAndDependencies, class TestR3MigrationAndSchema, class TestR3PayloadValidationAndRateLimit, class TestR3SeedAuditContext |
| `test_qa2_phase_r4.py` | 5280 | Phase R4 Regression Suite: Auditor Resilience, Bounds & Parsing (TR-401 to TR-405). | class TestR4MultiPageAuditor, class TestR4CompetitorAnalyzer, class TestR4RobotsAndLLMResilience |
| `test_qa2_phase_r5.py` | 3412 | Phase R5 Regression Suite: Frontend UX, State & Error Recovery (TR-501 to TR-505). | class TestR5FrontendJSStaticIntegrity |
| `test_qa3_phase_r1.py` | 3549 | Exports: test_ssrf_history_chain_populated, test_ssrf_history_empty_on_direct_fetch, test_dom_escape_html_quotes... | def test_ssrf_history_chain_populated(), def test_ssrf_history_empty_on_direct_fetch(), def test_dom_escape_html_quotes(), def test_dom_safe_url_quote_injection(), def test_nav_cmdk_single_quote_kid_xss() |
| `test_qa3_phase_r2.py` | 5100 | Exports: test_missing_check_codes_mapped_in_json, test_no_dangling_kt_records_in_map, test_layer_deductions_coverage_complete... | def test_missing_check_codes_mapped_in_json(), def test_no_dangling_kt_records_in_map(), def test_layer_deductions_coverage_complete(), def test_action_snippets_coverage_complete(), def test_kb_meta_schema_unification() |
| `test_qa3_phase_r3.py` | 3951 | Exports: test_streaming_body_size_enforcement_chunked, test_streaming_body_size_normal_payload_passes, test_rate_limiter_thread_safe_locking... | def test_streaming_body_size_enforcement_chunked(), def test_streaming_body_size_normal_payload_passes(), def test_rate_limiter_thread_safe_locking(), def test_temp_txn_context_connection_isolation(), def test_stage_normalization_mtime_invalidation() |
| `test_qa3_phase_r4.py` | 3815 | Exports: test_circuit_breaker_triggers_on_http_500, test_circuit_breaker_resets_on_success, test_circuit_breaker_open_skips_call... | def test_circuit_breaker_triggers_on_http_500(), def test_circuit_breaker_resets_on_success(), def test_circuit_breaker_open_skips_call(), def test_schema_validator_caps_json_ld_blocks_at_100(), def test_render_yaml_has_disk_block() |
| `test_qa3_phase_r5.py` | 2406 | Exports: test_identity_js_cancels_auto_dismiss_timer, test_knowledge_explorer_format_text_escapes_html, test_app_js_awaits_json_res_run_id... | def test_identity_js_cancels_auto_dismiss_timer(), def test_knowledge_explorer_format_text_escapes_html(), def test_app_js_awaits_json_res_run_id(), def test_approvals_js_rejects_non_ok_in_allsettled(), def test_nav_js_cmdk_toggle_on_repeat_keypress() |
| `test_qa_phase_q1.py` | 9048 | Exports: reset_rate_limits, client, TestQ1SynthesizeEndpoint... | def reset_rate_limits(), def client(), class TestQ1SynthesizeEndpoint, class TestQ1FullReportEndpoint, class TestQ1FrontendSanityGuards |
| `test_qa_phase_q2.py` | 6783 | Exports: TestQ2MigrationAndBoot... | class TestQ2MigrationAndBoot |
| `test_qa_phase_q3.py` | 7495 | Exports: TestQ3AuditorCrashRecovery, TestQ3SafeGetSizeLimit, TestQ3AuthorityAuditorImports... | class TestQ3AuditorCrashRecovery, class TestQ3SafeGetSizeLimit, class TestQ3AuthorityAuditorImports, class TestQ3SchemaValidatorEdgeCases, class TestQ3KnowledgeMapParity |
| `test_qa_phase_q4.py` | 9291 | Exports: reset_rate_limits, client, TestQ4ObservationsAndValidation... | def reset_rate_limits(), def client(), class TestQ4ObservationsAndValidation, class TestQ4RateLimiterAndRouter, class TestQ4ContentFormatAndSnippets |
| `test_qa_phase_q5.py` | 2276 | Exports: TestQ5RobotsCheckerComments, TestQ5AuditorConstants... | class TestQ5RobotsCheckerComments, class TestQ5AuditorConstants |
| `test_qa_regression_suite.py` | 16360 | Exports: TestTask01XSSSourceUrl, TestTask02MobileFocusNavigation, TestTask03HelpOverlayDismiss... | class TestTask01XSSSourceUrl, class TestTask02MobileFocusNavigation, class TestTask03HelpOverlayDismiss, class TestTask04BodySizeLimit413, class TestTask05TargetDomainValidation422 |
| `test_rag.py` | 7741 | Exports: TestCosineDistance, TestEmbeddingWaterfall, TestConfidenceGates... | class TestCosineDistance, class TestEmbeddingWaterfall, class TestConfidenceGates, class TestRouterGracefulDegradation, class TestEmbedCorpus |
| `test_rendering_auditor.py` | 6227 | Exports: TestT501RenderingAuditor... | class TestT501RenderingAuditor |
| `test_security_dom_sweeps.py` | 1579 | Exports: test_no_raw_single_quotes_in_inline_onclick_attributes, test_safe_url_always_escapes_output, test_command_palette_uses_delegated_event_listeners... | def test_no_raw_single_quotes_in_inline_onclick_attributes(), def test_safe_url_always_escapes_output(), def test_command_palette_uses_delegated_event_listeners(), def test_claims_explorer_uses_event_listeners() |
| `test_ssrf_byok_llm_endpoints.py` | 1043 | Exports: test_azure_call_blocks_private_ip, test_azure_call_blocks_localhost, test_custom_call_blocks_private_cidr... | def test_azure_call_blocks_private_ip(), def test_azure_call_blocks_localhost(), def test_custom_call_blocks_private_cidr(), def test_custom_call_blocks_metadata() |
| `test_synthesis_enrichment.py` | 1520 | Exports: test_synthesizer_input_includes_v2_evidence... | def test_synthesizer_input_includes_v2_evidence() |
| `test_track_b_manual_review.py` | 13011 | Exports: TestTB01ManualObservationsSchema, TestTB02ObservationPayload, TestTB03SubmitObservation... | class TestTB01ManualObservationsSchema, class TestTB02ObservationPayload, class TestTB03SubmitObservation, class TestTB04FullReport, class TestTB05SynthesisUpdate |

## File Naming Conventions
- `*_auditor.py`: Auditor modules for specific checks.
- `*_service.py`: Service modules containing business logic.
- `test_*.py`: Pytest files matching the implementation name.
- `*.html` & `*.js`: Frontend components in `areos/ui/`.

## Module Import Patterns
Internal modules typically use absolute imports based on the `areos` package root.
```python
from areos.api.dependencies import get_db
from areos.services.audit_service import AuditService
```

## Where to Add New Things
- **New auditor**: `areos/auditors/`
- **New API route**: `areos/api/routers/`
- **New service**: `areos/services/`
- **New test**: `tests/`
- **New knowledge**: `areos/kb/corpus/`
- **New UI page**: `areos/ui/`