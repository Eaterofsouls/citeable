# areos/auditors/cloaking_detector.py
#
# Task T-203: Cloaking & AI User-Agent Content Disparity Detector
#
# CONTRACT:
#   - Fetches page content using AI crawler User-Agent (GPTBot) via safe_get.
#   - Compares bot payload against browser-rendered HTML payload.
#   - Emits structured finding objects with deterministic check codes.
#   - Zero LLM calls required; strictly deterministic diff heuristics.

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any

from areos.util.ssrf import safe_get

logger = logging.getLogger(__name__)

GPTBOT_USER_AGENT = (
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; "
    "compatible; GPTBot/1.0; +https://openai.com/gptbot)"
)


@dataclass
class CloakingIssue:
    severity: str  # "error" | "warning" | "info"
    code: str      # machine-readable check code
    message: str


@dataclass
class CloakingResult:
    url: str = ""
    passed: bool = True
    issues: list[CloakingIssue] = field(default_factory=list)
    browser_word_count: int = 0
    bot_word_count: int = 0
    missing_elements: list[str] = field(default_factory=list)
    content_diff_summary: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def as_finding_dicts(self) -> list[dict[str, Any]]:
        """Convert issues to finding dictionaries suitable for orchestrator wiring."""
        return [
            {
                "code": issue.code,
                "check_code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "url": self.url,
                "check_type": "cloaking",
            }
            for issue in self.issues
        ]


def _extract_text(html: str) -> str:
    """Extract plain text from HTML by stripping scripts, styles, comments, and markup tags."""
    if not html:
        return ""
    # Cap string length at 2MB to prevent regex CPU exhaustion on massive DOM payloads
    html = html[:2000000]
    from areos.util.html_cleaner import clean_html_text
    return clean_html_text(html)


def _find_missing_elements(browser_html: str, bot_html: str) -> list[str]:
    """Identify key structural elements and headings present in browser HTML but absent in bot HTML."""
    missing: list[str] = []
    if not browser_html or not bot_html:
        return missing

    browser_capped = browser_html[:1000000]
    bot_capped = bot_html[:1000000]

    # 1. Compare headings (h1 - h6)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(browser_capped, "html.parser")
    browser_headings = [(tag.name, tag.decode_contents()) for tag in soup.find_all(re.compile(r"^h[1-6]$", re.I))]
    bot_text_lower = _extract_text(bot_capped).lower()

    for tag, content in browser_headings:
        from areos.util.html_cleaner import clean_html_text
        heading_text = clean_html_text(content)
        if len(heading_text) >= 3 and heading_text.lower() not in bot_text_lower:
            item = f"<{tag.lower()}>: {heading_text[:60]}"
            if item not in missing:
                missing.append(item)
                if len(missing) >= 5:
                    break

    # 2. Compare major structural tags
    structural_tags = ["main", "article", "section", "table", "nav", "form"]
    for tag in structural_tags:
        has_in_browser = bool(re.search(rf"<{tag}\b[^>]*>", browser_capped, flags=re.IGNORECASE))
        has_in_bot = bool(re.search(rf"<{tag}\b[^>]*>", bot_capped, flags=re.IGNORECASE))
        if has_in_browser and not has_in_bot:
            item = f"<{tag}> element"
            if item not in missing:
                missing.append(item)
                if len(missing) >= 10:
                    break

    return missing


def audit_cloaking(clean_domain: str, page_url: str, browser_html: str) -> CloakingResult:
    """
    Audit for cloaking by fetching the URL with an AI bot User-Agent (GPTBot)
    and comparing the resulting content against normal browser-rendered HTML.

    Check Codes Emitted:
      - CLOAKING_DETECTED: error - word count diff > 50% between browser and bot versions
      - CLOAKING_SUSPECTED: warning - word count diff > 20%
      - AI_BOT_BLOCKED_HTTP: error - HTTP 401/403/429/451 when fetching as AI bot
      - CLOAKING_FETCH_FAILED: info - could not fetch bot version for comparison
      - CLOAKING_OK: info - no significant content differences
    """
    if not page_url:
        return CloakingResult(
            url=page_url,
            passed=True,
            issues=[
                CloakingIssue(
                    severity="info",
                    code="CLOAKING_FETCH_FAILED",
                    message="No page URL provided for cloaking check.",
                )
            ],
            content_diff_summary="No page URL provided.",
        )

    headers = {
        "User-Agent": GPTBOT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = safe_get(page_url, timeout=4, headers=headers)
    except Exception as exc:
        logger.warning("Failed to fetch bot version for %s: %s", page_url, exc)
        browser_words = len(_extract_text(browser_html).split())
        return CloakingResult(
            url=page_url,
            passed=True,
            issues=[
                CloakingIssue(
                    severity="info",
                    code="CLOAKING_FETCH_FAILED",
                    message=f"Could not fetch bot version for comparison: {exc}",
                )
            ],
            browser_word_count=browser_words,
            content_diff_summary=f"Bot fetch failed: {exc}",
        )

    # Check for HTTP-level blocking of AI bots
    if resp.status_code in (401, 403, 429, 451):
        browser_words = len(_extract_text(browser_html).split())
        return CloakingResult(
            url=page_url,
            passed=False,
            issues=[
                CloakingIssue(
                    severity="error",
                    code="AI_BOT_BLOCKED_HTTP",
                    message=f"AI crawler request blocked with HTTP {resp.status_code}.",
                )
            ],
            browser_word_count=browser_words,
            bot_word_count=0,
            content_diff_summary=f"Bot request blocked with HTTP {resp.status_code}.",
        )

    if resp.status_code != 200:
        browser_words = len(_extract_text(browser_html).split())
        return CloakingResult(
            url=page_url,
            passed=True,
            issues=[
                CloakingIssue(
                    severity="info",
                    code="CLOAKING_FETCH_FAILED",
                    message=f"Bot fetch returned HTTP status {resp.status_code}.",
                )
            ],
            browser_word_count=browser_words,
            content_diff_summary=f"Bot fetch returned HTTP status {resp.status_code}.",
        )

    bot_html = resp.text or ""

    # Extract plain text from both versions
    browser_text = _extract_text(browser_html)
    bot_text = _extract_text(bot_html)

    browser_words = len(browser_text.split())
    bot_words = len(bot_text.split())

    if browser_words == 0 and bot_words == 0:
        diff_pct = 0.0
    else:
        diff_pct = (abs(browser_words - bot_words) / max(browser_words, 1)) * 100.0

    missing_elements = _find_missing_elements(browser_html, bot_html)

    issues: list[CloakingIssue] = []
    if diff_pct > 50.0:
        issues.append(
            CloakingIssue(
                severity="error",
                code="CLOAKING_DETECTED",
                message=(
                    f"Significant content difference detected ({diff_pct:.1f}% word count delta: "
                    f"browser {browser_words} words vs bot {bot_words} words)."
                ),
            )
        )
        passed = False
        summary = (
            f"Significant cloaking detected: browser has {browser_words} words, "
            f"AI bot received {bot_words} words ({diff_pct:.1f}% difference)."
        )
        if missing_elements:
            summary += f" Elements missing from bot view: {'; '.join(missing_elements[:5])}."
    elif diff_pct > 20.0:
        issues.append(
            CloakingIssue(
                severity="warning",
                code="CLOAKING_SUSPECTED",
                message=(
                    f"Moderate content difference detected ({diff_pct:.1f}% word count delta: "
                    f"browser {browser_words} words vs bot {bot_words} words)."
                ),
            )
        )
        passed = True
        summary = (
            f"Moderate content disparity: browser has {browser_words} words, "
            f"AI bot received {bot_words} words ({diff_pct:.1f}% difference)."
        )
        if missing_elements:
            summary += f" Elements missing from bot view: {'; '.join(missing_elements[:5])}."
    else:
        issues.append(
            CloakingIssue(
                severity="info",
                code="CLOAKING_OK",
                message=f"Content parity verified between browser and AI crawler ({diff_pct:.1f}% word count delta).",
            )
        )
        passed = True
        summary = f"Content parity verified: browser ({browser_words} words) vs AI crawler ({bot_words} words)."

    return CloakingResult(
        url=page_url,
        passed=passed,
        issues=issues,
        browser_word_count=browser_words,
        bot_word_count=bot_words,
        missing_elements=missing_elements,
        content_diff_summary=summary,
    )
