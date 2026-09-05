import json
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AREOS_API_TOKEN", "test-token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test-token")

from areos.api.main import app
from areos.db.connection import get_connection, get_db_path, apply_schema
from areos.db.context import write_as
from areos.kb.build_kb import build as build_kb_func, parse_jsonl
from scripts.verify_kb_semantic_parity import verify_parity

client = TestClient(app)
UI_DIR = Path(__file__).resolve().parents[1] / "areos" / "ui"


# ==============================================================================
# TASK-01: Verify XSS injection vectors in claim.source_url are rendered as escaped
# ==============================================================================
class TestTask01XSSSourceUrl:
    """Verify XSS vectors in claim.source_url / src.url are safely handled across UI files."""

    XSS_VECTORS = [
        "<script>alert('xss')</script>",
        "javascript:alert(1)",
        "https://example.com/\" onmouseover=\"alert(1)",
        "internal://case-study-ref<script>alert(1)</script>",
        "\"><svg onload=alert(1)>",
        "data:text/html,<script>alert(1)</script>",
    ]

    def test_dom_safe_url_sanitizes_javascript_and_data_schemes(self):
        """safeUrl in dom.js must neutralize javascript: and data: protocols and escape HTML."""
        dom_js = (UI_DIR / "dom.js").read_text(encoding="utf-8")
        assert "parsed.protocol === 'javascript:'" in dom_js
        assert "parsed.protocol === 'data:'" in dom_js
        assert "return escapeHtml(url);" in dom_js

    def test_app_js_escapes_claim_source_url_in_all_templates(self):
        """app.js must escape claim.source_url in both internal and external link contexts."""
        app_js = (UI_DIR / "app.js").read_text(encoding="utf-8")
        # Assert no raw unescaped ${claim.source_url} without escapeHtml or safeUrl
        raw_interpolations = re.findall(r"\$\{\s*claim\.source_url\s*\}", app_js)
        assert len(raw_interpolations) == 0, f"Found unescaped claim.source_url: {raw_interpolations}"
        assert "${escapeHtml(claim.source_url)}" in app_js
        assert "safeUrl(claim.source_url)" in app_js

    def test_remediation_js_escapes_claim_source_url(self):
        """remediation.js citation and modal rendering must escape source URLs."""
        rem_js = (UI_DIR / "remediation.js").read_text(encoding="utf-8")
        # Check citation rendering uses safeUrl and escapeHtml
        assert "safeUrl(sourceUrl)" in rem_js
        assert "escapeHtml(sourceUrl)" in rem_js
        assert "escapeHtml(statement)" in rem_js

    def test_knowledge_explorer_js_escapes_source_url(self):
        """knowledge_explorer.js must escape src.url, src.title, src.publisher."""
        ke_js = (UI_DIR / "knowledge_explorer.js").read_text(encoding="utf-8")
        assert "${escapeHtml(src.url)}" in ke_js
        assert "${escapeHtml(src.title)}" in ke_js
        assert "safeUrl(src.url)" in ke_js


# ==============================================================================
# TASK-02: Verify keyboard focus navigation on mobile viewports (<768px) is not trapped
# ==============================================================================
class TestTask02MobileFocusNavigation:
    """Verify makeDialogAccessible skips focus-trapping on mobile (<768px) and static drawers."""

    def test_dom_js_skips_focus_trap_on_mobile_and_static_position(self):
        """dom.js must check window.innerWidth < 768 and static positioning before trapping Tab."""
        dom_js = (UI_DIR / "dom.js").read_text(encoding="utf-8")
        assert "window.innerWidth < 768" in dom_js
        assert "window.getComputedStyle(container).position === 'static'" in dom_js
        assert "if (isStatic || isMobile) return;" in dom_js

    def test_css_defines_static_drawer_on_mobile_breakpoint(self):
        """index.css @media (max-width: 768px) must style .claim-drawer as position: static."""
        css = (UI_DIR / "index.css").read_text(encoding="utf-8")
        mobile_block = css[css.find("@media (max-width: 768px)"):]
        assert ".claim-drawer" in mobile_block
        assert "position: static" in mobile_block


# ==============================================================================
# TASK-03: Verify backdrop clicks and Esc key dismiss #help-overlay
# ==============================================================================
class TestTask03HelpOverlayDismiss:
    """Verify #help-overlay is dismissed by backdrop clicks and Escape key."""

    def test_help_js_has_backdrop_click_handler(self):
        """help.js must dismiss when click event target is the overlay backdrop."""
        help_js = (UI_DIR / "help.js").read_text(encoding="utf-8")
        assert "this.overlay.addEventListener('click'" in help_js
        assert "if (e.target === this.overlay) this.close();" in help_js

    def test_help_js_has_escape_key_listener(self):
        """help.js must listen for Escape keydown and close active overlay."""
        help_js = (UI_DIR / "help.js").read_text(encoding="utf-8")
        assert "e.key === 'Escape'" in help_js
        assert "this.overlay.classList.contains('active')" in help_js
        assert "this.close()" in help_js


# ==============================================================================
# TASK-04: Verify uploading a request body > 5MB returns HTTP 413 without ASGI exception
# ==============================================================================
class TestTask04BodySizeLimit413:
    """Verify request bodies exceeding 5MB are rejected with 413 without server crashes."""

    def test_content_length_exceeding_5mb_returns_413(self):
        """POST with Content-Length > 5MB immediately returns HTTP 413."""
        oversized_len = 5_000_000 + 1024
        response = client.post(
            "/api/v1/audit/runs",
            content=b"X" * 100,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(oversized_len),
                "Authorization": "Bearer test-token",
            },
        )
        assert response.status_code == 413
        data = response.json()
        assert "Payload too large" in data.get("detail", "")

    def test_chunked_stream_exceeding_5mb_returns_413(self):
        """POST with body bytes exceeding 5MB returns HTTP 413 without raising ASGI exception."""
        oversized_body = b"{\"target_domain\": \"example.com\", \"blob\": \"" + (b"A" * 5_000_100) + b"\"}"
        response = client.post(
            "/api/v1/audit/orchestrate",
            content=oversized_body,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413
        assert "Payload too large" in response.json().get("detail", "")

    def test_normal_payload_under_5mb_not_rejected_by_size_limit(self):
        """POST with body well under 5MB is not blocked by 413 middleware."""
        normal_payload = json.dumps({"target_domain": "example.com"}).encode("utf-8")
        response = client.post(
            "/api/v1/audit/runs",
            content=normal_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token",
            },
        )
        # Should be 200 (created) or 400/409, NOT 413
        assert response.status_code != 413


# ==============================================================================
# TASK-05: Verify invalid target_domain values return HTTP 422 Unprocessable Entity
# ==============================================================================
class TestTask05TargetDomainValidation422:
    """Verify invalid target_domain inputs are rejected with 422 Unprocessable Entity."""

    INVALID_DOMAINS = [
        "http://foo",
        "https://example.com",
        "invalid domain!",
        "example..com",
        "foo/bar",
        "domain with spaces.com",
        "ftp://test.org",
        "",
        "justwords",
        "http://valid-looking.com/path",
    ]

    VALID_DOMAINS = [
        "example.com",
        "sub.domain.org",
        "my-site.co.uk",
        "deep.nested.subdomain.io",
    ]

    def test_invalid_target_domains_in_audit_runs_return_422(self):
        """POST /api/v1/audit/runs rejects invalid domains with 422."""
        from areos.api.routers.audit import _ip_buckets
        for i, bad_domain in enumerate(self.INVALID_DOMAINS):
            _ip_buckets.clear()
            response = client.post(
                "/api/v1/audit/runs",
                json={"target_domain": bad_domain},
                headers={"Authorization": "Bearer test-token", "X-Forwarded-For": f"192.168.1.{i+1}"},
            )
            assert response.status_code == 422, f"Expected 422 for '{bad_domain}', got {response.status_code}"

    def test_invalid_target_domains_in_audit_orchestrate_return_422(self):
        """POST /api/v1/audit/orchestrate rejects invalid domains with 422."""
        from areos.api.routers.audit import _ip_buckets
        for i, bad_domain in enumerate(self.INVALID_DOMAINS):
            _ip_buckets.clear()
            response = client.post(
                "/api/v1/audit/orchestrate",
                json={"target_domain": bad_domain, "sample_content": ""},
                headers={"X-Forwarded-For": f"192.168.2.{i+1}"},
            )
            assert response.status_code == 422, f"Expected 422 for '{bad_domain}', got {response.status_code}"

    def test_valid_target_domains_pass_pydantic_validation(self):
        """Valid domain names pass payload schema validation."""
        from areos.api.routers.audit import _ip_buckets
        for i, good_domain in enumerate(self.VALID_DOMAINS):
            _ip_buckets.clear()
            response = client.post(
                "/api/v1/audit/runs",
                json={"target_domain": good_domain},
                headers={"Authorization": "Bearer test-token", "X-Forwarded-For": f"192.168.3.{i+1}"},
            )
            # Response must not be 422
            assert response.status_code != 422, f"Valid domain '{good_domain}' erroneously got 422: {response.text}"


# ==============================================================================
# TASK-06: Verify concurrent multi-threaded writes via write_as execute with 0 WAL busy
# ==============================================================================
class TestTask06ConcurrentWriteAsStress:
    """Verify concurrent multi-threaded writes via write_as execute with 0 WAL busy errors."""

    def test_multithreaded_concurrent_write_as_stress_zero_busy_exceptions(self):
        """16 worker threads concurrently performing write_as transactions with zero WAL busy errors."""
        db_path = get_db_path()
        errors = []
        num_threads = 16
        iterations_per_thread = 15

        def worker(thread_idx: int):
            try:
                conn = get_connection(db_path)
                for i in range(iterations_per_thread):
                    actor = f"thread_{thread_idx}_op_{i}"
                    reason = f"stress_test_txn_{thread_idx}_{i}"
                    with write_as(conn, actor=actor, reason=reason):
                        # Verify transaction context isolation
                        row = conn.execute("SELECT actor, reason FROM _txn_context WHERE id = 1").fetchone()
                        if not row or row["actor"] != actor or row["reason"] != reason:
                            errors.append(f"Context crosstalk in thread {thread_idx}: got {row}")
                    time.sleep(0.001)
            except sqlite3.OperationalError as e:
                errors.append(f"WAL busy/locked OperationalError in thread {thread_idx}: {e}")
            except Exception as e:
                errors.append(f"Unexpected exception in thread {thread_idx}: {e}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered concurrency errors during write_as stress: {errors}"


# ==============================================================================
# TASK-07: Verify 100% parity across all 77 check codes using verify_kb_semantic_parity.py
# ==============================================================================
class TestTask07SemanticParity77Codes:
    """Verify 100% parity across all 77 check codes via scripts/verify_kb_semantic_parity.py."""

    def test_verify_kb_semantic_parity_gate_all_77_codes_passed(self):
        """verify_parity() must verify 77 check codes across KB map, scoring, and action snippets."""
        map_path = Path(__file__).resolve().parents[1] / "areos" / "kb" / "check_code_to_knowledge_map.json"
        with open(map_path, "r", encoding="utf-8") as f:
            cc_map = json.load(f)

        assert len(cc_map) == 77, f"Expected exactly 77 check codes in map, found {len(cc_map)}"
        assert verify_parity() is True


# ==============================================================================
# TASK-08: Verify simulated crash during KB rebuild leaves the live database uncorrupted
# ==============================================================================
class TestTask08KBCrashToleranceUncorruptedDB:
    """Verify simulated crash/exception during KB rebuild leaves the live database uncorrupted."""

    def test_simulated_crash_during_kb_rebuild_leaves_live_db_uncorrupted(self):
        """If build_kb raises midway, the live DB retains all original records and passes integrity check."""
        from areos.db.connection import close_all_connections
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_db_path = Path(tmp_dir) / "test_areos.db"

            try:
                # Initial successful build
                conn = build_kb_func(db_path=test_db_path)

                initial_knowledge_count = conn.execute("SELECT count(*) FROM knowledge").fetchone()[0]
                initial_sources_count = conn.execute("SELECT count(*) FROM kb_sources").fetchone()[0]
                initial_evidence_count = conn.execute("SELECT count(*) FROM kb_evidence").fetchone()[0]

                assert initial_knowledge_count > 0
                assert initial_sources_count > 0
                assert initial_evidence_count > 0

                # Verify integrity
                integrity_before = conn.execute("PRAGMA integrity_check").fetchone()[0]
                assert integrity_before == "ok"

                # Simulate crash midway during evidence insertion
                original_parse = parse_jsonl

                def crashing_parse(file_path):
                    if "evidence.jsonl" in str(file_path):
                        raise RuntimeError("Simulated sudden crash/power loss during evidence ingestion")
                    return original_parse(file_path)

                with patch("areos.kb.build_kb.parse_jsonl", side_effect=crashing_parse):
                    with pytest.raises(RuntimeError, match="Simulated sudden crash"):
                        build_kb_func(db_path=test_db_path)

                # Verify live database is 100% uncorrupted and rollback restored all tables
                post_crash_conn = get_connection(test_db_path)
                integrity_after = post_crash_conn.execute("PRAGMA integrity_check").fetchone()[0]
                assert integrity_after == "ok", f"Database corrupted after crash: {integrity_after}"

                post_knowledge_count = post_crash_conn.execute("SELECT count(*) FROM knowledge").fetchone()[0]
                post_sources_count = post_crash_conn.execute("SELECT count(*) FROM kb_sources").fetchone()[0]
                post_evidence_count = post_crash_conn.execute("SELECT count(*) FROM kb_evidence").fetchone()[0]

                assert post_knowledge_count == initial_knowledge_count
                assert post_sources_count == initial_sources_count
                assert post_evidence_count == initial_evidence_count
            finally:
                close_all_connections()
