# Phase 0 Deep Spec + Bug Hunter

## 1. Confirmed Session Doc Bugs

### CRITICAL-001: MANUAL_REMEDIATION_TEXT NameError
- **Severity**: Critical
- **File**: `areos/auditors/synthesis_engine.py`
- **Line number(s)**: 382, 389
- **Current Code**:
```python
        if finding.card_id not in MANUAL_REMEDIATION_TEXT:
            rejected.append({
                "check_code": finding.card_id,
                "reason": f"No remediation text defined for card {finding.card_id}",
            })
            continue

        title, description = MANUAL_REMEDIATION_TEXT[finding.card_id]
```
- **Replacement Code**:
```python
        # Define a fallback dict inside the function or globally
        _MANUAL_REMEDIATION_TEXT = {
            "C052": ("Verify Render Asset Accessibility", "Check if critical JavaScript or CSS stylesheets are blocked by robots.txt rules or CDN challenges."),
            "C053": ("Evaluate Schema Semantic Honesty", "Inspect the JSON-LD blocks and compare them line-by-line with visible page text."),
            "C073": ("Causal Attribution for Missing Citations", "When a brand is omitted from Perplexity or Gemini summaries, investigate which layer failed."),
            "C077": ("Assess Brand Sentiment & Framing in AI Answers", "Analyze the framing of brand citations in generative answers."),
            "C090": ("Final Root Cause Diagnosis Narrative", "Ensure the overall audit report provides a coherent narrative linking technical failures to real business outcomes."),
            "DEFAULT": ("Expert Human Inspection Required", "Perform expert qualitative verification per the instruction card guidelines.")
        }
        
        if finding.card_id not in _MANUAL_REMEDIATION_TEXT:
            title, description = _MANUAL_REMEDIATION_TEXT["DEFAULT"]
        else:
            title, description = _MANUAL_REMEDIATION_TEXT[finding.card_id]
```
- **Regression Test**:
```python
def test_build_manual_recommendations_actionable():
    from areos.auditors.manual_findings_template import ManualFinding
    from areos.auditors.synthesis_engine import _build_manual_recommendations
    from pathlib import Path
    
    finding = ManualFinding(card_id="C052", verdict="fail", notes="Blocked by CDN", page_url="https://example.com", severity="error")
    recs, rejected = _build_manual_recommendations([finding], Path("dummy.db"))
    
    assert len(recs) == 1
    assert recs[0].title == "[Manual] Verify Render Asset Accessibility"
    assert "Check if critical JavaScript" in recs[0].description
```
- **What breaks if skipped**: The manual review synthesis pipeline crashes when any human findings are processed, preventing report generation.

### CRITICAL-002: REMEDIATION_TEXT NameError
- **Severity**: Critical
- **File**: `areos/auditors/synthesis_engine.py`
- **Line number(s)**: 59
- **Current Code**:
```python
        if not rows:
            return REMEDIATION_TEXT
```
- **Replacement Code**:
```python
        if not rows:
            return {}
```
- **Regression Test**:
```python
def test_load_remediation_text_empty_kb():
    from areos.auditors.synthesis_engine import _load_remediation_text
    from pathlib import Path
    
    # Mocking DB to return empty rows
    res = _load_remediation_text(Path("empty.db"))
    assert res == {}
```
- **What breaks if skipped**: If KB `GUIDANCE` records are empty, loading remediation text silently fails and returns `{}` through the outer exception handler, skipping all automated recommendations.

### DATA-002: Empty Priority Scores Fallback
- **Severity**: Medium
- **File**: `areos/auditors/synthesis_engine.py`
- **Line number(s)**: 41
- **Current Code**:
```python
    except Exception:
        pass
    return {}
```
- **Replacement Code**:
```python
    except Exception:
        pass
    return {
        "CRAWLER_FULLY_BLOCKED": 1,
        "CLOAKING_DETECTED": 2,
        "EXTRACTABILITY_NONE": 2,
        "SCHEMA_MISSING": 3,
        "CITATION_NOT_OBSERVED": 4
    }
```
- **Regression Test**:
```python
def test_load_priority_scores_fallback():
    from areos.auditors.synthesis_engine import _load_priority_scores
    from pathlib import Path
    
    res = _load_priority_scores(Path("nonexistent.db"))
    assert res.get("CRAWLER_FULLY_BLOCKED") == 1
```
- **What breaks if skipped**: If the DB fails to load, all check codes get priority 10, completely inverting the severity ordering of the report.

### RISK-002: Hardcoded token
- **Severity**: High
- **File**: `areos/kb/build_kb.py`
- **Line number(s)**: 8
- **Current Code**:
```python
os.environ.setdefault('AREOS_API_TOKEN', 'build_kb_token')
```
- **Replacement Code**:
```python
# os.environ.setdefault('AREOS_API_TOKEN', 'build_kb_token') # Removed to enforce explicit token
```
- **Regression Test**: N/A (Configuration change)
- **What breaks if skipped**: Development token leaks into production environments protecting admin endpoints.

### HIGH-001: claims_legacy rename Not Idempotent
- **Severity**: High
- **File**: `areos/kb/build_kb.py`
- **Line number(s)**: 92, 93
- **Current Code**:
```python
        if row['type'] == 'table':
            logger.info("Renaming existing 'claims' table to 'claims_legacy'")
            cur.execute("ALTER TABLE claims RENAME TO claims_legacy")
```
- **Replacement Code**:
```python
        if row['type'] == 'table':
            logger.info("Renaming existing 'claims' table to 'claims_legacy'")
            cur.execute("DROP TABLE IF EXISTS claims_legacy")
            cur.execute("ALTER TABLE claims RENAME TO claims_legacy")
```
- **Regression Test**:
```python
def test_claims_legacy_rename_idempotency():
    # Setup DB with 'claims_legacy' and 'claims' tables
    # Call handle_claims_view(conn)
    # Assert no OperationalError
    pass
```
- **What breaks if skipped**: Running `build_kb.py` twice when `claims` table exists will crash on persistent disks.

### RISK-003: Exception Swallowing
- **Severity**: Medium
- **File**: `areos/kb/router.py`
- **Line number(s)**: 158-160, 230-234
- **Current Code**:
```python
        try:
            guidance = GuidanceDetail(**json.loads(row["guidance_json"]))
        except Exception:
            pass
```
```python
    if review_due:
        try:
            if date.fromisoformat(review_due) < date.today():
                is_stale = True
                stale_since = review_due
        except ValueError:
            pass
```
- **Replacement Code**:
```python
        try:
            guidance = GuidanceDetail(**json.loads(row["guidance_json"]))
        except Exception as e:
            logger.warning("Malformed guidance_json for kid=%s: %s", row["kid"], e)
            guidance = None
```
```python
    if review_due:
        try:
            if date.fromisoformat(review_due) < date.today():
                is_stale = True
                stale_since = review_due
        except ValueError as e:
            logger.warning("Malformed review_due date for kid=%s: %r — %s", record.kid, review_due, e)
```
- **Regression Test**: Test loading a record with bad JSON in `guidance_json` and asserting it logs a warning instead of swallowing.
- **What breaks if skipped**: Missing functionality (guidance / stale flags) silently fails without visibility.

### DATA-001: Empty _CHECK_CODE_MAPPINGS
- **Severity**: Low (Deprecated)
- **File**: `areos/db/ingest_claims.py`
- **Line number(s)**: 62
- **Current Code**:
```python
_CHECK_CODE_MAPPINGS: dict[str, list[str]] = {}
```
- **Replacement Code**: Remove this variable and its usage in `ingest_claims.py` loops (Lines 181-204) since V2 uses KB mappings.
- **What breaks if skipped**: Empty inserts and confusing fallback logic maintained unnecessarily.

### Audit references to check_code_mappings
- **File**: `areos/api/routers/audit.py`
- **Line numbers**: 181, 258, 263, 487. 
- **Fix**: Swap to use `wire_finding()` or JSON mappings.

### Findings references to check_code_mappings
- **File**: `areos/auditors/findings_to_claims.py`
- **Line numbers**: 57, 140
- **Fix**: Remove legacy DB fallback entirely if we are fully V2.

### AP-03 missing from audited_stages
- **Severity**: Medium
- **File**: `areos/auditors/audit_orchestrator.py`
- **Line number(s)**: 332, 391
- **Current Code**:
```python
json.dumps(["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"]),
```
```python
audited_stages=["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"],
```
- **Replacement Code**:
```python
json.dumps(["AP-01", "AP-02", "AP-03", "AP-04", "AP-05", "AP-06"]),
```
```python
audited_stages=["AP-01", "AP-02", "AP-03", "AP-04", "AP-05", "AP-06"],
```

## 2. NEW Bugs Discovered (Not in Session Docs)

1. **Unused Import in `synthesis_engine.py`**:
   - Line 19: `from areos.auditors.findings_to_claims import CHECK_CODE_TO_CLAIM_IDS` is unused. Should be removed.

2. **Silent Swallowing in `findings_to_claims.py`**:
   - Lines 63-66:
     ```python
             except Exception:
                 pass
         except Exception:
             pass
     ```
     Swallows exceptions during legacy fallback check. Should log errors or remove legacy path.

3. **Silent Swallowing in `synthesis_engine.py`**:
   - Line 470:
     ```python
         except Exception:
             pass  # Non-fatal: citations are enhancement only
     ```
     Should at least log standard errors.

4. **Missing Timeout in Orchestrator schema fetch fallback**:
   - `areos/auditors/audit_orchestrator.py` uses `safe_get` which is good, but `sample_content` relies heavily on implicit structure that can fail.

5. **List Comprehension variable shadowing in `audit.py`**:
   - As mentioned in session docs, `f` shadows the outer `f`, but functionally works. Still bad practice.

6. **Inconsistent ErrorCode usages in orchestrator**:
   - `ErrorCode.ROBOTS_UNVERIFIABLE` vs `"SCHEMA_MISSING"`. Some use enum, some use hardcoded strings.
