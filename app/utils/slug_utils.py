import re
import unicodedata
from typing import Optional
from slugify import slugify as _slugify

# Mapeamentos explícitos para casos chatos (º, ª, símbolos, etc.)
_EXPLICIT_REPLACEMENTS = [
    ("ç", "c"), ("Ç", "c"),
    ("º", "o"), ("ª", "a"),
    ("°", "o"),
    ("&", " e "),
]

def _ascii_fallback(text: str) -> str:
    # Normaliza para ASCII removendo diacríticos
    norm = unicodedata.normalize("NFKD", text)
    ascii_str = norm.encode("ascii", "ignore").decode("ascii")
    # Troca qualquer coisa que não seja [a-z0-9] por hífen
    ascii_str = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_str)
    return re.sub(r"-{2,}", "-", ascii_str).strip("-").lower()

def make_slug(text: Optional[str]) -> str:
    if not text:
        return ""

    # Aplica substituições explícitas antes
    for a, b in _EXPLICIT_REPLACEMENTS:
        text = text.replace(a, b)

    # Tenta via python-slugify com locale pt
    s = _slugify(
        text,
        language="pt",          # mapeia bem á/â/ã/é/ê/í/ó/ô/õ/ú e ç
        separator="-",
        lowercase=True,
        # Se quiser, force substituições aqui também:
        # replacements=_EXPLICIT_REPLACEMENTS
    )
    if s:  # funcionou
        return s

    # Fallback robusto
    return _ascii_fallback(text)
