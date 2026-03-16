import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(text: str) -> str:
    return NON_ALNUM.sub(" ", str(text or "").lower()).strip()


def similarity(left: str, right: str) -> float:
    left_norm, right_norm = normalize_name(left), normalize_name(right)
    if not left_norm or not right_norm:
        return 0.0
    if fuzz:
        return float(fuzz.token_sort_ratio(left_norm, right_norm))
    return SequenceMatcher(None, left_norm, right_norm).ratio() * 100


def best_item_match(
    reference_item: Dict[str, str],
    candidate_items: List[Dict[str, str]],
    threshold: float = 84.0,
) -> Tuple[Optional[Dict[str, str]], float]:
    best_score = 0.0
    best_candidate = None
    ref_name = reference_item.get("item", "")
    ref_category = reference_item.get("category", "")
    for candidate in candidate_items:
        score = similarity(ref_name, candidate.get("item", ""))
        if normalize_name(ref_category) == normalize_name(candidate.get("category", "")):
            score += 3
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return (best_candidate, best_score) if best_score >= threshold else (None, best_score)

