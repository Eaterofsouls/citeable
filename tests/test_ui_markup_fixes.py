from pathlib import Path
UI = Path(__file__).resolve().parents[1] / "areos" / "ui"

def test_wizard_dots_use_delegated_listener_not_inline_onclick():
    src = (UI / "guided_review.js").read_text(encoding="utf-8")
    assert "goToInlineStep(${i})" not in src
    assert 'data-step="${i}"' in src
    assert ".gr-dot-btn[data-step]" in src
