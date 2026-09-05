# areos/auditors/rendering_auditor.py
#
# Phase 5: JS-Rendering Diff Auditor (C030 / C031 / C033)
#
# Evaluates difference between raw HTML and client-rendered DOM using headless browser.
# Gracefully degrades to a no-op skipped result if Playwright is not installed.

from __future__ import annotations

import os
import re
import difflib
from dataclasses import dataclass, field
from typing import Optional, Any

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except (ImportError, Exception):
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class RenderingIssue:
    severity: str        # "error" | "warning" | "info"
    code: str            # machine-readable check code
    message: str


@dataclass
class RenderingAuditResult:
    url: str = ""
    passed: bool = True
    issues: list[RenderingIssue] = field(default_factory=list)
    skipped: bool = False
    reason: str = ""
    diff_ratio: float = 1.0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def as_finding_dicts(self) -> list[dict]:
        """Convert issues to finding dictionaries suitable for findings_to_claims wiring."""
        return [
            {
                "code": issue.code,
                "check_code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "url": self.url,
                "check_type": "rendering",
            }
            for issue in self.issues
        ]


def _strip_html(html: str) -> str:
    """Fast plain text extraction from raw HTML."""
    if not html:
        return ""
    from areos.util.html_cleaner import clean_html_text
    return clean_html_text(html)


def audit_js_rendering(page_url: str, raw_html: str, timeout_ms: int = 4000) -> RenderingAuditResult:
    """
    Audit JS-rendering differences between raw HTML and fully-rendered DOM.
    If Playwright is not available, returns a skipped result safely.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return RenderingAuditResult(
            url=page_url,
            skipped=True,
            reason="playwright not installed",
        )

    # If env var is explicitly set to 0/false, skip
    if os.environ.get("AREOS_ENABLE_PLAYWRIGHT", "0").lower() in ("0", "false", "no"):
        return RenderingAuditResult(
            url=page_url,
            skipped=True,
            reason="AREOS_ENABLE_PLAYWRIGHT is disabled",
        )

    raw_text = _strip_html(raw_html)
    issues: list[RenderingIssue] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(page_url, wait_until="domcontentloaded", timeout=timeout_ms)
            
            # Extract rendered text
            rendered_text = page.evaluate("() => document.body ? document.body.innerText : ''")
            rendered_text = re.sub(r"\s+", " ", rendered_text or "").strip()

            # Check lazy-loaded elements
            lazy_count = page.evaluate("""() => {
                return document.querySelectorAll('[data-src], [loading="lazy"], img[data-lazy]').length;
            }""")

            # Check hidden accordion/tab elements
            hidden_count = page.evaluate("""() => {
                return document.querySelectorAll('[aria-expanded="false"], details:not([open]), [style*="display: none"], [style*="display:none"]').length;
            }""")

            browser.close()

        # Compute text diff similarity
        if raw_text and rendered_text:
            matcher = difflib.SequenceMatcher(None, raw_text, rendered_text)
            diff_ratio = matcher.quick_ratio()
        elif not raw_text and rendered_text:
            diff_ratio = 0.0  # 100% JS rendered SPA
        else:
            diff_ratio = 1.0

        if diff_ratio < 0.5:
            issues.append(RenderingIssue(
                severity="error",
                code="JS_CRITICAL_CONTENT_GATED",
                message=f"Critical content is gated behind JavaScript rendering (similarity {diff_ratio:.2f} < 0.50). Raw HTML crawlers cannot see majority of content.",
            ))
        elif diff_ratio < 0.8:
            issues.append(RenderingIssue(
                severity="warning",
                code="JS_CONTENT_DEPENDENCY",
                message=f"Significant content depends on JavaScript execution (similarity {diff_ratio:.2f} < 0.80). Some AI crawlers may miss text.",
            ))

        if lazy_count > 5:
            issues.append(RenderingIssue(
                severity="info",
                code="LAZY_LOAD_HIDDEN",
                message=f"Found {lazy_count} lazy-loaded elements that require scroll or JS execution to populate.",
            ))

        if hidden_count > 5:
            issues.append(RenderingIssue(
                severity="warning",
                code="HIDDEN_CONTENT_DEFAULT",
                message=f"Found {hidden_count} accordion or tab sections hidden by default. Text inside closed accordions may receive lower weight.",
            ))

        if not any(i.severity in ("error", "warning") for i in issues):
            issues.append(RenderingIssue(
                severity="info",
                code="RENDERING_OK",
                message="DOM rendering audit passed. Raw HTML and rendered text are well aligned.",
            ))

        passed = not any(i.severity == "error" for i in issues)
        return RenderingAuditResult(
            url=page_url,
            passed=passed,
            issues=issues,
            skipped=False,
            diff_ratio=diff_ratio,
        )

    except Exception as e:
        return RenderingAuditResult(
            url=page_url,
            skipped=True,
            reason=f"Playwright rendering failed: {str(e)[:150]}",
        )
