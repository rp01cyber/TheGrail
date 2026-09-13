"""Render Markdown to sanitized HTML. Code blocks get fenced-code support."""
import bleach
import markdown as md
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p", "pre", "code", "span", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "th", "td", "hr", "br", "img",
    "ul", "ol", "li", "blockquote", "strong", "em", "del",
]
ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "rel", "target"],
    "code": ["class"], "span": ["class"], "pre": ["class"],
    "img": ["src", "alt", "title"], "th": ["align"], "td": ["align"],
}

@register.filter
def render_md(text):
    if not text:
        return ""
    html = md.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])
    clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return mark_safe(clean)
