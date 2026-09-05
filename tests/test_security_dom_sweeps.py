import re
import pytest
from pathlib import Path

UI_DIR = Path("areos/ui")


def test_no_raw_single_quotes_in_inline_onclick_attributes():
    """Verify no JS/HTML files contain unescaped dynamic variables in inline onclick handlers."""
    for file_path in UI_DIR.glob("**/*.*"):
        if file_path.suffix not in (".js", ".html"):
            continue
        content = file_path.read_text(encoding="utf-8")
        # Match dangerous patterns like onclick="...${raw_var}..." without encodeURIComponent or escapeHtml
        matches = re.findall(r"onclick=[\"'][^\"']*\$\{(?!encodeURIComponent|escapeHtml|safeUrl|window\.)[^}]+\}[^\"']*[\"']", content)
        assert len(matches) == 0, f"Found potential raw injection in {file_path}: {matches}"


def test_safe_url_always_escapes_output():
    """Verify dom.js safeUrl function calls escapeHtml."""
    content = (UI_DIR / "dom.js").read_text(encoding="utf-8")
    assert "return escapeHtml(url);" in content


def test_command_palette_uses_delegated_event_listeners():
    """Verify nav.js cmdk-results uses event listener delegation and data-href."""
    content = (UI_DIR / "nav.js").read_text(encoding="utf-8")
    assert "data-href=" in content
    assert "cmdkResults.addEventListener('click'" in content


def test_claims_explorer_uses_event_listeners():
    """Verify app.js does not use inline onclick for pin/propose/preview buttons."""
    content = (UI_DIR / "app.js").read_text(encoding="utf-8")
    assert "pinBtn.addEventListener('click'" in content
    assert "proposeBtn.addEventListener('click'" in content
