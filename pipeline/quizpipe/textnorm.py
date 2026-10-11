"""Normalisation de texte : comparer un extrait « copié tel quel » au texte réel d'une page de cours.

On tolère uniquement les différences typographiques sans valeur (espaces, apostrophes, tirets,
ligatures, césures en fin de ligne). La casse, les accents et les chiffres doivent être identiques.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

_CHAR_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "´": "'", "`": "'",
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    "­": "", "​": "", "‌": "", "‍": "", "﻿": "",
    "…": "...",
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
}
_TRANS = str.maketrans(_CHAR_MAP)
_SKIP_MARK = re.compile(r"\[(?:…|\.\.\.)\]")
_HYPHEN_BREAK = re.compile(r"(?<=\w)[-‐‑­][ \t]*\r?\n[ \t]*(?=\w)")


def normalize(text: str) -> str:
    """NFC + table de substitution + espaces compactés. Garde la casse et les accents."""
    t = unicodedata.normalize("NFC", text).translate(_TRANS)
    return re.sub(r"\s+", " ", t).strip()


def page_variants(raw: str) -> list[str]:
    """Variantes normalisées d'une page : coupure de mot (tiret supprimé), vrai tiret (gardé), brut."""
    raw = unicodedata.normalize("NFC", raw)
    out: list[str] = []
    for variant in (_HYPHEN_BREAK.sub("", raw), _HYPHEN_BREAK.sub("-", raw), raw):
        n = normalize(variant)
        if n not in out:
            out.append(n)
    return out


def split_excerpt(excerpt: str) -> list[str]:
    """Découpe un extrait aux marqueurs [...] ; chaque segment doit apparaître, dans l'ordre."""
    return [s for s in (normalize(p) for p in _SKIP_MARK.split(excerpt)) if s]


def _find_whole(hay: str, seg: str, start: int) -> int:
    """Première occurrence de seg à partir de start qui ne coupe aucun mot (« jour » n'est pas « jours »)."""
    i = hay.find(seg, start)
    while i >= 0:
        j = i + len(seg)
        left_cut = i > 0 and seg[0].isalnum() and hay[i - 1].isalnum()
        right_cut = j < len(hay) and seg[-1].isalnum() and hay[j].isalnum()
        if not (left_cut or right_cut):
            return i
        i = hay.find(seg, i + 1)
    return -1


def excerpt_in_page(excerpt: str, variants: list[str], min_segment: int = 4) -> bool:
    """Vrai si l'extrait (segments séparés par [...]) figure tel quel, dans l'ordre, dans une variante de la page."""
    segments = split_excerpt(excerpt)
    if not segments or any(len(s) < min_segment for s in segments):
        return False
    for page_text in variants:
        pos = 0
        for seg in segments:
            i = _find_whole(page_text, seg, pos)
            if i < 0:
                break
            pos = i + len(seg)
        else:
            return True
    return False


def find_in_order(items: list[str], text: str) -> bool:
    """Vrai si chaque élément apparaît dans `text` (normalisé), dans l'ordre donné."""
    hay = normalize(text)
    pos = 0
    for item in items:
        i = hay.find(normalize(item), pos)
        if i < 0:
            return False
        pos = i + len(normalize(item))
    return True


def fold(text: str) -> str:
    """Minuscules sans accents (comparaison des initiales d'un mnémotechnique)."""
    d = unicodedata.normalize("NFD", text)
    return "".join(c for c in d if unicodedata.category(c) != "Mn").lower()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
