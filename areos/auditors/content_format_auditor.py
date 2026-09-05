# areos/auditors/content_format_auditor.py
#
# AP-04 Content Accessibility & Format Auditor (Zyppy Factor Scoring)
#
# CONTRACT:
#   - Evaluates page HTML/text signals against top-scoring Zyppy format factors (8.0–9.2).
#   - Emits structured finding objects with deterministic check codes.
#   - Zero API cost required; relies on DOM heuristics and content structure analysis.
#
# ZYPPY FACTORS TRACKED:
#   - Answer near top of page (9.2 / 10)
#   - Preview / snippet controls allowing extraction (9.0 / 10)
#   - Self-contained answer framing (8.8 / 10)
#   - Factual specificity vs vague hedging (8.5 / 10)
#   - Structured list / table presentation (8.0 / 10)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any
import re

@dataclass
class FormatIssue:
    severity: str        # "error" | "warning" | "info"
    code: str            # machine-readable check code
    message: str

@dataclass
class FormatAuditResult:
    url: str
    passed: bool
    issues: list[FormatIssue] = field(default_factory=list)
    signals_analyzed: dict = field(default_factory=dict)
    extracted_lead_text: str = ""

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
                "check_type": "content_format"
            }
            for issue in self.issues
        ]


def extract_text_blocks(html: str) -> list[str]:
    """Extract rough text paragraphs from HTML without heavy external parser dependencies."""
    if not html:
        return []
    # Cap string length at 1MB to prevent regex CPU exhaustion on massive DOM payloads
    html = html[:1000000]
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    blocks = [(tag.name, tag.decode_contents()) for tag in soup.find_all(["p", "div", "section", "article", "li"])]
    text_blocks = []
    for t_tag, t_content in blocks:
        # strip tags inside block
        from areos.util.html_cleaner import clean_html_text
        txt = clean_html_text(t_content)
        if len(txt.split()) >= 2: # keep non-trivial text chunks
            text_blocks.append(txt)
    if not text_blocks and html:
        # fall back to stripping all tags from string if no semantic tags found
        from areos.util.html_cleaner import clean_html_text
        txt = clean_html_text(html)
        if txt:
            text_blocks = [txt]
    return text_blocks


def audit_page_format(url: str, html: str = "", signals: Optional[dict[str, Any]] = None, client_keys: dict | None = None) -> FormatAuditResult:
    """
    Audit page formatting for AI engine snippet generation and RAG ingestion.
    Can analyze raw HTML or pre-computed signals dictionary.
    """
    if signals is None:
        signals = {}

    issues: list[FormatIssue] = []
    html_lower = html.lower() if html else ""
    meta_robots = str(signals.get("meta_robots", "")).lower()
    
    # 1. Check snippet blocking directives (Zyppy score 9.0)
    has_nosnippet = (
        "nosnippet" in meta_robots or 
        "max-snippet:0" in meta_robots or 
        ("name=\"robots\"" in html_lower and "nosnippet" in html_lower) or
        "data-nosnippet" in html_lower
    )
    if has_nosnippet:
        issues.append(FormatIssue(
            severity="error",
            code="NOSNIPPET_BLOCKING_AI",
            message="Page contains 'nosnippet' or 'max-snippet:0' directive, blocking AI search engine summary inclusion."
        ))

    # Determine text blocks and counts from signals or HTML
    text_blocks = signals.get("paragraphs")
    if not text_blocks:
        text_blocks = extract_text_blocks(html)
        
    list_item_count = signals.get("list_item_count")
    if list_item_count is None and html:
        list_item_count = len(re.findall(r"<li[^>]*>", html_lower, flags=re.IGNORECASE))
    elif list_item_count is None:
        list_item_count = 0
        
    table_count = signals.get("table_count")
    if table_count is None and html:
        table_count = len(re.findall(r"<table[^>]*>", html_lower, flags=re.IGNORECASE))
    elif table_count is None:
        table_count = 0

    # 2. Answer position check (Zyppy score 9.2) — T-401
    # Is there a substantive descriptive block (>= 30 words) in the first 30% of blocks?
    substantive_early = False
    top_30_pct = max(1, int(len(text_blocks) * 0.30))
    for i, block in enumerate(text_blocks[:top_30_pct]):
        words = block.split()
        if len(words) >= 30:
            substantive_early = True
            break

    if len(text_blocks) >= 2 and not substantive_early:
        issues.append(FormatIssue(
            severity="error",
            code="ANSWER_NOT_NEAR_TOP",
            message="No complete answer or substantive definition found in the first 30% of page content. AI engines favor answers located near the top of the page."
        ))

    # 3. Self-contained phrasing check (Zyppy score 8.8)
    # Check if early paragraphs start with pronoun references that fail when extracted out-of-context
    dangling_patterns = [r"^this (item|product|service|article|post|page|tool) is", r"^it is (a|an|the)", r"^as mentioned (above|earlier)", r"^in the previous section"]
    for block in text_blocks[:3]:
        block_lower = block.lower().strip()
        if any(re.match(p, block_lower) for p in dangling_patterns):
            issues.append(FormatIssue(
                severity="warning",
                code="ANSWER_NOT_SELF_CONTAINED",
                message="Opening paragraph starts with a dangling reference ('This tool...', 'As mentioned above...'). AI RAG chunks require self-contained entity naming to retain meaning."
            ))
            break

    # 4. Factual specificity check (Zyppy score 8.5)
    # Vague hedging without concrete facts/numbers in descriptive blocks
    vague_phrases = ["many ways", "several benefits", "various tools", "some people", "can vary widely"]
    has_vague = any(vp in " ".join(text_blocks[:4]).lower() for vp in vague_phrases)
    has_numbers = any(re.search(r"\b\d+(\.\d+)?(%|x|s|ms|m|k)?\b", block) for block in text_blocks[:4])
    if has_vague and not has_numbers and len(text_blocks) > 0:
        issues.append(FormatIssue(
            severity="warning",
            code="ANSWER_NOT_FACTUALLY_SPECIFIC",
            message="Content relies on vague generalizations without specific factual numbers or data points. Specific statistics significantly increase AI quote frequency."
        ))

    # 5. List or Table presence (Zyppy score 8.0)
    if list_item_count < 2 and table_count == 0 and len(text_blocks) > 1:
        issues.append(FormatIssue(
            severity="warning",
            code="NO_LIST_OR_TABLE",
            message="Page lacks structured HTML lists (<ul>, <ol>) or tables (<table>). Scannable itemized formats are heavily preferred for conversational AI enumeration replies."
        ))

    # If no errors or warnings, emit a good format pass finding
    if not any(i.severity in ("error", "warning") for i in issues):
        issues.append(FormatIssue(
            severity="info",
            code="ANSWER_FORMAT_GOOD",
            message="Page content passes AI extractability and Zyppy format heuristic checks."
        ))

    passed = not any(i.severity == "error" for i in issues)
    
    return FormatAuditResult(
        url=url,
        passed=passed,
        issues=issues,
        signals_analyzed={
            "text_blocks_count": len(text_blocks),
            "list_items": list_item_count,
            "tables": table_count,
            "has_nosnippet": has_nosnippet
        }
    )
