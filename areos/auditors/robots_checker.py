# areos/auditors/robots_checker.py
#
# Task 3c: robots.txt / llms.txt Per-Crawler Directive Checker
#
# CONTRACT:
#   - Parses a robots.txt string and checks directives for specific AI crawlers.
#   - Parses an llms.txt string for the presence and quality of key sections.
#   - Returns structured, deterministic results — no LLM involved.
#
# AI CRAWLERS TRACKED (as of mid-2026):
#   - GPTBot            (OpenAI)
#   - ChatGPT-User      (OpenAI browsing)
#   - ClaudeBot         (Anthropic)
#   - Claude-User       (Anthropic)
#   - PerplexityBot     (Perplexity)
#   - Google-Extended   (Google AI training opt-out)
#   - Googlebot         (Google — baseline)
#   - Bingbot           (Microsoft — also used by Copilot)
#   - CCBot             (Common Crawl — feeds many LLM training sets)
#   - anthropic-ai      (Anthropic secondary)
#   - Diffbot           (Diffbot/Meta AI)
#   - YouBot            (You.com)
#   - cohere-ai         (Cohere)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import re

# ── Crawler groups ───────────────────────────────────────────────────────────

AI_CRAWLERS = [
    "GPTBot", "ChatGPT-User", "ClaudeBot", "Claude-User",
    "PerplexityBot", "Google-Extended", "Googlebot", "Bingbot",
    "CCBot", "anthropic-ai", "Diffbot", "YouBot", "cohere-ai",
]


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class CrawlerDirective:
    user_agent: str
    allowed_paths: list[str] = field(default_factory=list)
    disallowed_paths: list[str] = field(default_factory=list)
    crawl_delay: Optional[float] = None

    @property
    def is_fully_blocked(self) -> bool:
        return "/" in self.disallowed_paths and not self.allowed_paths

    @property
    def is_fully_allowed(self) -> bool:
        return not self.disallowed_paths or (
            len(self.disallowed_paths) == 1 and self.disallowed_paths[0] == ""
        )


@dataclass
class RobotsIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str


@dataclass
class RobotsResult:
    """Result for robots.txt analysis."""
    directives: dict[str, CrawlerDirective] = field(default_factory=dict)
    # "wildcard" = the * catch-all
    wildcard_directive: Optional[CrawlerDirective] = None
    issues: list[RobotsIssue] = field(default_factory=list)

    def effective_policy(self, crawler: str) -> CrawlerDirective | None:
        """Return the most specific directive applicable to a given crawler."""
        # Exact match first, then wildcard fallback
        if crawler in self.directives:
            return self.directives[crawler]
        # Case-insensitive match
        for key, val in self.directives.items():
            if key.lower() == crawler.lower():
                return val
        return self.wildcard_directive


@dataclass
class LlmsTxtSection:
    heading: str
    content: str


@dataclass
class LlmsTxtResult:
    """Result for llms.txt analysis."""
    present: bool
    has_h1: bool = False
    sections: list[LlmsTxtSection] = field(default_factory=list)
    issues: list[RobotsIssue] = field(default_factory=list)


# ── Robots.txt parser ────────────────────────────────────────────────────────

def parse_robots_txt(robots_txt: str) -> RobotsResult:
    """
    Parse a robots.txt string and return structured directives
    for all AI crawlers, plus any issues detected.
    """
    result = RobotsResult()
    current_agents: list[str] = []
    current_disallowed: list[str] = []
    current_allowed: list[str] = []
    current_delay: Optional[float] = None

    def flush_group():
        nonlocal current_agents, current_disallowed, current_allowed, current_delay
        if not current_agents:
            return
        directive = CrawlerDirective(
            user_agent=", ".join(current_agents),
            allowed_paths=list(current_allowed),
            disallowed_paths=list(current_disallowed),
            crawl_delay=current_delay,
        )
        for agent in current_agents:
            if agent == "*":
                result.wildcard_directive = directive
            else:
                result.directives[agent] = directive
        current_agents = []
        current_disallowed = []
        current_allowed = []
        current_delay = None

    for raw_line in robots_txt.splitlines():
        line = raw_line.strip()
        # Strip inline comments
        if "#" in line:
            line = line[:line.index("#")].strip()
        if not line:
            # Blank line = end of group
            flush_group()
            continue

        lower = line.lower()
        if lower.startswith("user-agent:"):
            agent_val = line.split(":", 1)[1].strip()
            if current_disallowed or current_allowed:
                # New user-agent after directives = flush
                flush_group()
            current_agents.append(agent_val)
        elif lower.startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            current_disallowed.append(path)
        elif lower.startswith("allow:"):
            path = line.split(":", 1)[1].strip()
            current_allowed.append(path)
        elif lower.startswith("crawl-delay:"):
            try:
                current_delay = float(line.split(":", 1)[1].strip())
            except ValueError:
                result.issues.append(RobotsIssue(
                    "warning", "INVALID_CRAWL_DELAY",
                    f"Could not parse crawl-delay value: {line}"
                ))

    flush_group()

    # ── Issue detection ──────────────────────────────────────────────────────

    # Check each known AI crawler
    for crawler in AI_CRAWLERS:
        directive = result.effective_policy(crawler)
        if directive is None:
            result.issues.append(RobotsIssue(
                "info", "NO_DIRECTIVE",
                f"{crawler}: no explicit directive found (inherits wildcard or is unrestricted)"
            ))
        elif directive.is_fully_blocked:
            result.issues.append(RobotsIssue(
                "warning", "CRAWLER_FULLY_BLOCKED",
                f"{crawler}: Disallow: / — fully blocked, will not index any page"
            ))
        elif directive.is_fully_allowed:
            result.issues.append(RobotsIssue(
                "info", "CRAWLER_ALLOWED",
                f"{crawler}: explicitly allowed to crawl (no Disallow restrictions)"
            ))
        else:
            # Partial — list what's blocked
            blocked_paths = ", ".join(directive.disallowed_paths)
            result.issues.append(RobotsIssue(
                "info", "CRAWLER_PARTIAL",
                f"{crawler}: partially restricted — blocked: [{blocked_paths}]"
            ))

    # Warn if Google-Extended missing (common oversight)
    if "Google-Extended" not in result.directives:
        result.issues.append(RobotsIssue(
            "warning", "GOOGLE_EXTENDED_MISSING",
            "Google-Extended user-agent not specified — Google AI training opt-out is not configured"
        ))

    # Warn if GPTBot missing
    if "GPTBot" not in result.directives:
        result.issues.append(RobotsIssue(
            "warning", "GPTBOT_MISSING",
            "GPTBot user-agent not specified — OpenAI crawler policy not explicitly configured"
        ))

    return result


# ── llms.txt parser ──────────────────────────────────────────────────────────

LLMS_RECOMMENDED_SECTIONS = [
    "about", "docs", "blog", "api", "contact", "optional",
]

def parse_llms_txt(llms_txt: Optional[str]) -> LlmsTxtResult:
    """
    Parse an llms.txt string and validate its structure per the
    emerging llmstxt.org specification (Markdown-based).
    """
    if llms_txt is None or llms_txt.strip() == "":
        return LlmsTxtResult(
            present=False,
            issues=[RobotsIssue("error", "LLMS_TXT_MISSING",
                                "llms.txt not found — AI agents have no structured guidance for this site")]
        )

    result = LlmsTxtResult(present=True)
    lines = llms_txt.splitlines()

    # Extract H1 (must be first non-blank)
    h1_found = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            result.has_h1 = True
            h1_found = True
        break

    if not h1_found:
        result.issues.append(RobotsIssue(
            "error", "LLMS_TXT_MISSING_H1",
            "llms.txt must start with an H1 heading (# Site Name) — not found"
        ))

    # Extract sections (H2 headings)
    section_headings = [l.strip()[3:].strip() for l in lines if l.strip().startswith("## ")]
    for heading in section_headings:
        content_lines = []
        in_section = False
        for line in lines:
            if line.strip() == f"## {heading}":
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("## "):
                    break
                content_lines.append(line)
        result.sections.append(LlmsTxtSection(
            heading=heading,
            content="\n".join(content_lines).strip()
        ))

    # Recommend common sections
    existing_headings_lower = {s.heading.lower() for s in result.sections}
    for rec in LLMS_RECOMMENDED_SECTIONS:
        if rec not in existing_headings_lower:
            result.issues.append(RobotsIssue(
                "info", "LLMS_TXT_MISSING_SECTION",
                f"Recommended section '## {rec.capitalize()}' not present"
            ))

    # Check for file:// links (llms-full.txt pattern)
    link_pattern = re.compile(r'\[.+?\]\(.+?\)')
    has_links = any(link_pattern.search(l) for l in lines)
    if not has_links:
        result.issues.append(RobotsIssue(
            "warning", "LLMS_TXT_NO_LINKS",
            "llms.txt contains no markdown links — consider linking to key docs/pages for AI agents"
        ))

    # Check for blank llms.txt (present but essentially empty)
    meaningful = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if not meaningful:
        result.issues.append(RobotsIssue(
            "warning", "LLMS_TXT_EMPTY_CONTENT",
            "llms.txt has headings but no actual content — add descriptions and links"
        ))

    return result


# ── Formatting helpers ───────────────────────────────────────────────────────

def format_robots_report(url: str, result: RobotsResult) -> str:
    lines = [f"robots.txt Report for: {url}", "=" * 60]

    blocked = [i for i in result.issues if i.code == "CRAWLER_FULLY_BLOCKED"]
    warnings = [i for i in result.issues if i.severity == "warning"]

    lines.append(f"Summary: {len(result.directives)} explicit directives | "
                 f"{len(blocked)} AI crawlers fully blocked | {len(warnings)} warnings\n")

    for issue in result.issues:
        icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}.get(issue.severity, "?")
        lines.append(f"  {icon} [{issue.code}] {issue.message}")

    return "\n".join(lines)


def format_llms_report(url: str, result: LlmsTxtResult) -> str:
    lines = [f"llms.txt Report for: {url}", "=" * 60]
    lines.append(f"Present: {'Yes' if result.present else 'No'} | "
                 f"H1: {'Yes' if result.has_h1 else 'No'} | "
                 f"Sections: {len(result.sections)}\n")

    for issue in result.issues:
        icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}.get(issue.severity, "?")
        lines.append(f"  {icon} [{issue.code}] {issue.message}")

    return "\n".join(lines)
