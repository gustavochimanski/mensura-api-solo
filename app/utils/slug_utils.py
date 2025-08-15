# app/utils/slug_utils.py
import re, unicodedata
from typing import Optional
from slugify import slugify as _slugify

_EXPLICIT_REPLACEMENTS = [
    ("&", " e "),
    ("%", " percent "),
    ("º", "o"), ("ª", "a"),
    ("°", "o"),
    ("ç", "c"), ("Ç", "c"),
]

def _ascii_fallback(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text)
    ascii_str = norm.encode("ascii", "ignore").decode("ascii")
    ascii_str = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_str)
    return re.sub(r"-{2,}", "-", ascii_str).strip("-").lower()

def make_slug(text: Optional[str]) -> str:
    if not text:
        return ""
    s = _slugify(
        text,
        separator="-",
        lowercase=True,
        replacements=_EXPLICIT_REPLACEMENTS,
        allow_unicode=False,
    )
    return s or _ascii_fallback(text)
