# areos/util/sanitize.py
# Server-side HTML sanitization for any text that might be rendered in the UI.
# Defense-in-depth alongside the client-side DOMPurify/textContent approach.

import html

def sanitize_text(text: str) -> str:
    """Escape HTML entities in text to prevent XSS."""
    if not text:
        return ""
    return html.escape(str(text), quote=True)
