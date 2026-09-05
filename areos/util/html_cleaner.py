from bs4 import BeautifulSoup, Comment
import re
import html

def clean_html_text(html_content: str, remove_media: bool = False, remove_head: bool = False) -> str:
    """
    O(N) HTML tag cleaner using BeautifulSoup.
    Replaces regex-based O(N^2) tag stripping.
    """
    if not html_content:
        return ""
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    tags_to_remove = ["script", "style"]
    if remove_media:
        tags_to_remove.extend(["svg", "video", "audio", "iframe", "canvas", "object", "embed", "img", "source", "track", "param", "noscript"])
    if remove_head:
        tags_to_remove.extend(["head", "noscript"])
        
    for tag in tags_to_remove:
        for el in soup.find_all(tag):
            el.decompose()
            
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        
    text = soup.get_text(separator=" ", strip=True)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
