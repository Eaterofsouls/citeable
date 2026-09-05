# areos/auditors/media_blindness_auditor.py
#
# Task T-205: Media Blindness Auditor
#
# CONTRACT:
#   - Detects reliance on iframes, images without alt text, media-only content, and videos without transcripts.
#   - Emits structured finding objects with deterministic check codes.
#   - Zero external parser dependencies — uses Python standard library `re` and `html`.
#   - Boundary: Media detection only — no network requests.
#
# CHECK CODES:
#   - IFRAME_HEAVY (warning): Page has >3 iframes (AI crawlers cannot index iframe content)
#   - IMAGES_MISSING_ALT (warning): >30% of img tags have no alt attribute
#   - ALL_CONTENT_IN_MEDIA (error): Page body has <50 words outside of media elements
#   - VIDEO_NO_TRANSCRIPT (info): Video/embed elements found with no transcript or text alternative
#   - MEDIA_OK (info): No media blindness issues detected

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MediaIssue:
    severity: str  # "error" | "warning" | "info"
    code: str  # Check code in SCREAMING_SNAKE_CASE
    message: str


@dataclass
class MediaAuditResult:
    url: str
    passed: bool = True
    issues: list[MediaIssue] = field(default_factory=list)
    media_stats: dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def as_finding_dicts(self) -> list[dict[str, Any]]:
        """Convert issues to finding dictionaries suitable for findings_to_claims wiring."""
        return [
            {
                "code": issue.code,
                "check_code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "url": self.url,
                "check_type": "media_blindness",
            }
            for issue in self.issues
        ]


def _count_body_words_outside_media(html: str) -> int:
    """Extract text outside of media and script/style elements, returning word count."""
    if not html:
        return 0
    # Cap string length at 1MB to prevent regex CPU exhaustion
    raw_html = html[:1000000]

    # Remove non-content sections
    from areos.util.html_cleaner import clean_html_text
    text = clean_html_text(raw_html, remove_media=True, remove_head=True)

    words = text.split()
    return len(words)


def audit_media_blindness(page_url: str, html: str) -> MediaAuditResult:
    """
    Audit a page for media accessibility and AI crawler visibility.

    Evaluates iframe volume, image alt attribute coverage, text content
    volume outside of media wrappers, and presence of transcripts for video/embeds.
    """
    issues: list[MediaIssue] = []
    html_content = html or ""

    # 1. Count <iframe> tags
    iframe_tags = re.findall(r"<iframe\b[^>]*>", html_content, flags=re.IGNORECASE)
    iframe_count = len(iframe_tags)

    # 2. Count <img> tags and those missing alt attributes
    img_tags = re.findall(r"<img\b[^>]*>", html_content, flags=re.IGNORECASE)
    img_count = len(img_tags)
    img_no_alt = 0
    for img_tag in img_tags:
        # Match standard HTML alt attribute (avoid matching data-alt or embedded words)
        if not re.search(r"(?<![a-zA-Z0-9_-])alt(?:\s*=|[\s>/]|$)", img_tag, flags=re.IGNORECASE):
            img_no_alt += 1

    # 3. Count words outside of media elements
    body_word_count = _count_body_words_outside_media(html_content)

    # 4. Count <video> and <embed> tags
    video_tags = re.findall(r"<video\b[^>]*>", html_content, flags=re.IGNORECASE)
    embed_tags = re.findall(r"<embed\b[^>]*>", html_content, flags=re.IGNORECASE)
    video_count = len(video_tags)
    embed_count = len(embed_tags)

    # Check for transcripts / text alternatives when video or embed elements exist
    media_has_transcript = False
    if video_count > 0 or embed_count > 0:
        transcript_patterns = [
            r"<track\b[^>]*>",
            r'itemprop=["\'](?:transcript|caption)["\']',
            r'\bclass=["\'][^"\']*\b(?:transcript|captions?|subtitles?)\b',
            r'\bid=["\'][^"\']*\b(?:transcript|captions?|subtitles?)\b',
            r'\b(?:transcript|captions?|subtitles?)\b',
        ]
        if any(re.search(pat, html_content, flags=re.IGNORECASE) for pat in transcript_patterns):
            media_has_transcript = True

    # 5. Apply thresholds
    # IFRAME_HEAVY: warning — page has >3 iframes
    if iframe_count > 3:
        issues.append(
            MediaIssue(
                severity="warning",
                code="IFRAME_HEAVY",
                message=f"Page contains {iframe_count} iframes (threshold >3); AI crawlers cannot index iframe content.",
            )
        )

    # IMAGES_MISSING_ALT: warning — >30% of img tags have no alt attribute
    if img_count > 0 and (img_no_alt / img_count) > 0.30:
        pct_missing = (img_no_alt / img_count) * 100
        issues.append(
            MediaIssue(
                severity="warning",
                code="IMAGES_MISSING_ALT",
                message=f"{img_no_alt} of {img_count} images ({pct_missing:.1f}%) lack alt attributes (threshold >30%).",
            )
        )

    # ALL_CONTENT_IN_MEDIA: error — page body has <50 words outside of media elements
    if body_word_count < 50:
        issues.append(
            MediaIssue(
                severity="error",
                code="ALL_CONTENT_IN_MEDIA",
                message=f"Page body has only {body_word_count} words outside of media elements (minimum 50 required for AI indexing).",
            )
        )

    # VIDEO_NO_TRANSCRIPT: info — video/embed elements found with no transcript/text alternative
    if (video_count > 0 or embed_count > 0) and not media_has_transcript:
        issues.append(
            MediaIssue(
                severity="info",
                code="VIDEO_NO_TRANSCRIPT",
                message="Video or embedded media elements found without transcript or text alternative.",
            )
        )

    # 6. If no issues, emit MEDIA_OK
    if not issues:
        issues.append(
            MediaIssue(
                severity="info",
                code="MEDIA_OK",
                message="No media blindness issues detected. Media elements are properly augmented with text.",
            )
        )

    passed = not any(i.severity == "error" for i in issues)

    media_stats = {
        "iframe_count": iframe_count,
        "img_count": img_count,
        "img_no_alt": img_no_alt,
        "body_word_count": body_word_count,
        "video_count": video_count,
        "embed_count": embed_count,
    }

    return MediaAuditResult(
        url=page_url,
        passed=passed,
        issues=issues,
        media_stats=media_stats,
    )
