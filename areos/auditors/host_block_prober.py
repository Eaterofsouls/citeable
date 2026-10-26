# areos/auditors/host_block_prober.py
"""
WP-4.2: Live AI-bot host-block probing.
Probes target root concurrently with verified AI crawler User-Agents via SSRF-safe fetch.
Detects infrastructure-level (WAF/CDN/429/403/5xx) blocking that is invisible in robots.txt.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
import logging
from typing import Any, Optional

from areos.util.ssrf import safe_get

logger = logging.getLogger(__name__)

# Verified User-Agent strings for primary generative AI crawlers and fetchers
AI_PROBE_USER_AGENTS: dict[str, str] = {
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
    "ChatGPT-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
    "OAI-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
    "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "Claude-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; +claude-searchbot@anthropic.com)",
    "Claude-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-User/1.0; +claude-user@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Perplexity-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)",
    "Amazonbot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot)",
    "Amzn-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Amzn-SearchBot/1.0; +https://developer.amazon.com/support/amzn-searchbot)",
}


@dataclass
class HostBlockIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str


@dataclass
class HostBlockProbeResult:
    target_url: str
    control_status: int
    probe_results: dict[str, Optional[int]] = field(default_factory=dict)
    blocked_bots: dict[str, int] = field(default_factory=dict)
    issues: list[HostBlockIssue] = field(default_factory=list)


def probe_host_blocks(
    target_url: str,
    control_status: int = 200,
    timeout: float = 3.0,
    max_workers: int = 5,
    user_agents: Optional[dict[str, str]] = None,
) -> HostBlockProbeResult:
    """
    Concurrently probe target URL with verified AI crawler User-Agents.

    If control_status is 2xx (plain browser succeeds) but any AI bot receives
    403, 429, or 5xx, emit AI_CRAWLER_HOST_BLOCKED (severity="error").
    """
    if user_agents is None:
        user_agents = AI_PROBE_USER_AGENTS

    result = HostBlockProbeResult(
        target_url=target_url,
        control_status=control_status,
    )

    # If control request did not succeed with 2xx, site is down or globally blocking
    if not (200 <= control_status < 300):
        return result

    def _probe_one(bot_name: str, ua: str) -> tuple[str, Optional[int]]:
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            resp = safe_get(target_url, timeout=timeout, headers=headers, max_bytes=1024)
            return bot_name, resp.status_code
        except Exception as exc:
            logger.debug("Probe failed for bot %s on %s: %s", bot_name, target_url, exc)
            return bot_name, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_probe_one, bot, ua): bot
            for bot, ua in user_agents.items()
        }
        for future in concurrent.futures.as_completed(future_map):
            bot, status = future.result()
            result.probe_results[bot] = status
            if status is not None and (status in (403, 429) or (500 <= status < 600)):
                result.blocked_bots[bot] = status

    if result.blocked_bots:
        details = ", ".join(
            f"{bot} (HTTP {code})" for bot, code in sorted(result.blocked_bots.items())
        )
        msg = (
            f"Infrastructure-level AI crawler host blocks detected: [{details}]. "
            "Hosting WAF, CDN, or server rate-limits are rejecting AI user-agents while serving standard browser traffic."
        )
        result.issues.append(HostBlockIssue(
            severity="error",
            code="AI_CRAWLER_HOST_BLOCKED",
            message=msg,
        ))

    return result
