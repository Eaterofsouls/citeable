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
