import re
from pathlib import Path
UI = Path(__file__).resolve().parents[1] / "areos" / "ui"

def test_wizard_dots_use_delegated_listener_not_inline_onclick():
    src = (UI / "guided_review.js").read_text(encoding="utf-8")
    assert "goToInlineStep(${i})" not in src
    assert 'data-step="${i}"' in src
    assert ".gr-dot-btn[data-step]" in src

def test_no_94_percent_claim_in_user_facing_files():
    for f in list(UI.glob("*.html")) + list(UI.glob("*.js")):
        assert "94%" not in f.read_text(encoding="utf-8"), f.name

def test_site_is_pinned_to_light_mode():
    css = (UI / "index.css").read_text(encoding="utf-8")
    assert "prefers-color-scheme" not in css
    assert 'data-theme="dark"' not in css
    assert re.search(r":root\s*\{\s*color-scheme:\s*light;\s*\}", css)

def test_cors_docs_list_every_origin_the_code_allows():
    root = Path(__file__).resolve().parents[1]
    main_src = (root / "areos" / "api" / "main.py").read_text(encoding="utf-8")
    block = main_src[main_src.index("allow_origins=["):]
    block = block[: block.index("]")]
    origins = re.findall(r'"http://([^"]+)"', block)
    assert len(origins) == 4
    docs = (UI / "docs" / "internal" / "10-security.md").read_text(encoding="utf-8")
    docs += (UI / "docs" / "internal" / "15-known-issues.md").read_text(encoding="utf-8")
    for origin in origins:
        assert origin in docs, origin
