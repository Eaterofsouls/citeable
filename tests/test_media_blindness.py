# tests/test_media_blindness.py

import pytest
from areos.auditors.media_blindness_auditor import (
    MediaAuditResult,
    MediaIssue,
    audit_media_blindness,
)


def test_iframe_heavy():
    html = "<iframe></iframe>" * 4
    res = audit_media_blindness("http://test.com", html)
    assert any(i.code == "IFRAME_HEAVY" for i in res.issues)
    assert res.media_stats["iframe_count"] == 4


def test_images_missing_alt():
    html = "<img src='test.jpg'>"
    res = audit_media_blindness("http://test.com", html)
    assert any(i.code == "IMAGES_MISSING_ALT" for i in res.issues)
    assert res.media_stats["img_count"] == 1
    assert res.media_stats["img_no_alt"] == 1


def test_images_with_alt():
    html = (
        "<html><body><p>"
        + "word " * 60
        + "</p><img src='test.jpg' alt='A descriptive text'></body></html>"
    )
    res = audit_media_blindness("http://test.com", html)
    assert not any(i.code == "IMAGES_MISSING_ALT" for i in res.issues)
    assert res.media_stats["img_count"] == 1
    assert res.media_stats["img_no_alt"] == 0
    assert any(i.code == "MEDIA_OK" for i in res.issues)
    assert res.passed is True


def test_video_no_transcript():
    html = "<video src='test.mp4'></video>"
    res = audit_media_blindness("http://test.com", html)
    assert any(i.code == "VIDEO_NO_TRANSCRIPT" for i in res.issues)


def test_video_with_transcript():
    html = (
        "<html><body><p>"
        + "word " * 60
        + "</p><video src='test.mp4'><track kind='subtitles' src='subs.vtt'></video>"
        + "<div class='transcript'>Transcript text here</div></body></html>"
    )
    res = audit_media_blindness("http://test.com", html)
    assert not any(i.code == "VIDEO_NO_TRANSCRIPT" for i in res.issues)
    assert res.media_stats["video_count"] == 1
    assert any(i.code == "MEDIA_OK" for i in res.issues)
    assert res.passed is True


def test_all_content_in_media():
    html = "<div><img src='test.jpg' alt='valid alt'></div>"
    res = audit_media_blindness("http://test.com", html)
    assert any(i.code == "ALL_CONTENT_IN_MEDIA" for i in res.issues)
    assert res.passed is False
    assert res.media_stats["body_word_count"] < 50


def test_media_finding_dicts():
    html = "<iframe></iframe>" * 4
    res = audit_media_blindness("http://test.com", html)
    findings = res.as_finding_dicts()
    assert isinstance(findings, list)
    assert len(findings) > 0
    assert all("check_code" in f and "severity" in f for f in findings)
