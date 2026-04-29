import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


NON_ALNUM = re.compile(r"[^a-z0-9]+")

# ── Patterns to strip from item names before matching ────────────────
# Dietary / allergen tags like (GF), (VG), (V), (DF), (N), etc.
_DIETARY_TAG_RE = re.compile(r"\(\s*(?:GF|VG|VE|V|DF|NF|N|SF|VEGAN|VEGETARIAN)\s*\)", re.IGNORECASE)
# Prices embedded in names like "$13.95" or "13.95"
_INLINE_PRICE_RE = re.compile(r"\$?\d{1,3}(?:\.\d{2})?\s*$")
# Portion/size markers like "(6 Pc)", "(8 slices)", "(32 oz.)"
_PORTION_RE = re.compile(r"\(\s*\d+\s*(?:pc|pcs|pieces?|slices?|oz\.?|ct|count|cut\s*(?:pc|pcs)?\.?)\s*\)", re.IGNORECASE)
# Slash-separated suffixes: " / Rice", " / Noodle" — keep the core item
_SLASH_SUFFIX_RE = re.compile(r"\s*/\s*\S.*$")
# Trailing size/quantity like "6 Pc" or "6 Pieces" at end of name (no parens)
_TRAILING_QTY_RE = re.compile(r"\s+\d+\s*(?:pc|pcs|pieces?|slices?|oz\.?)\s*$", re.IGNORECASE)


def clean_item_name(text: str) -> str:
    """Strip dietary tags, prices, portions, and suffixes from an item name.

    'Yellow Curry Chicken / Rice (GF) $13.95'  →  'Yellow Curry Chicken'
    'Cream Cheese Rangoon (4)'                  →  'Cream Cheese Rangoon'
    'Roti Trio (8 slices)'                      →  'Roti Trio'
    """
    s = str(text or "").strip()
    s = _DIETARY_TAG_RE.sub("", s)
    s = _PORTION_RE.sub("", s)
    s = _INLINE_PRICE_RE.sub("", s)
    s = _SLASH_SUFFIX_RE.sub("", s)
    s = _TRAILING_QTY_RE.sub("", s)
    # Remove generic parenthesized numbers like "(4)" or "(6)"
    s = re.sub(r"\(\s*\d+\s*\)", "", s)
    return s.strip(" -|:/")


def normalize_name(text: str) -> str:
    return NON_ALNUM.sub(" ", str(text or "").lower()).strip()


def similarity(left: str, right: str) -> float:
    """Fuzzy similarity between two item names, with name cleaning."""
    left_clean = clean_item_name(left)
    right_clean = clean_item_name(right)
    left_norm = normalize_name(left_clean)
    right_norm = normalize_name(right_clean)
    if not left_norm or not right_norm:
        return 0.0

    # Exact substring match → high score
    if left_norm in right_norm or right_norm in left_norm:
        shorter = min(len(left_norm), len(right_norm))
        longer = max(len(left_norm), len(right_norm))
        if shorter / longer > 0.5:
            return max(92.0, shorter / longer * 100)

    if fuzz:
        # Use token_sort_ratio on cleaned names for best fuzzy matching
        return float(fuzz.token_sort_ratio(left_norm, right_norm))
    return SequenceMatcher(None, left_norm, right_norm).ratio() * 100


def best_item_match(
    reference_item: Dict[str, str],
    candidate_items: List[Dict[str, str]],
    threshold: float = 75.0,
) -> Tuple[Optional[Dict[str, str]], float]:
    best_score = 0.0
    best_candidate = None
    ref_name = reference_item.get("item", "")
    ref_category = reference_item.get("category", "")
    for candidate in candidate_items:
        score = similarity(ref_name, candidate.get("item", ""))
        # Category bonus
        if normalize_name(ref_category) == normalize_name(candidate.get("category", "")):
            score += 3
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return (best_candidate, best_score) if best_score >= threshold else (None, best_score)

