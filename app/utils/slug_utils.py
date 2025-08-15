# app/utils/slug_utils.py
import re
import unicodedata
from typing import Optional
from slugify import slugify as _slugify

_EXPLICIT_REPLACEMENTS = [
    ("&", " e "),
    ("º", "o"), ("ª", "a"),
    ("°", "o"),
]

def _ascii_fallback(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text)
    ascii_str = norm.encode("ascii", "ignore").decode("ascii")
    ascii_str = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_str)
    return re.sub(r"-{2,}", "-", ascii_str).strip("-").lower()

def make_slug(text: Optional[str]) -> str:
    if not text:
        return ""

    for a, b in _EXPLICIT_REPLACEMENTS:
        text = text.replace(a, b)

    # python-slugify >= 8 usa `locale`, não `language`
    s = _slugify(
        text,
        locale="pt",           # mapeia corretamente á/ã/â/é/ê/í/ó/õ/ô/ú e ç→c
        separator="-",
        lowercase=True,
        replacements=[("ç", "c"), ("Ç", "c")],  # redundante mas garante o futuro
        # allow_unicode=False (default) -> ASCII
    )
    return s or _ascii_fallback(text)
