"""Template filters for rendering entry content."""
import re

from django import template

register = template.Library()

# A blank line (two or more newlines, ignoring intervening spaces/tabs) is a
# paragraph break; a lone newline is just an email client's hard wrap.
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n\s*")


@register.filter
def unwrap(value):
    """Collapse hard-wrap newlines so each paragraph flows to the full width.

    Email clients wrap reply text at ~72 columns. Piped straight into Django's
    ``linebreaks`` that wrap becomes a ``<br>`` on every line, so the entry
    renders as a narrow ragged column instead of filling its card. We join the
    consecutive lines within a paragraph with a space and keep blank-line
    paragraph breaks intact for ``linebreaks`` to turn into ``<p>`` tags.
    """
    if not value:
        return value
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = _PARAGRAPH_BREAK.split(text)
    return "\n\n".join(
        " ".join(line.strip() for line in paragraph.split("\n") if line.strip())
        for paragraph in paragraphs
        if paragraph.strip()
    )
