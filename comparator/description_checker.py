import re
from difflib import SequenceMatcher

TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")


def normalize_description(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def descriptions_differ(our_item, reference_item, threshold: float = 0.88) -> bool:
    our_desc = normalize_description(our_item.get("description", ""))
    ref_desc = normalize_description(reference_item.get("description", ""))
    if not ref_desc:
        return False
    if not our_desc:
        return True
    ratio = SequenceMatcher(None, our_desc, ref_desc).ratio()
    incomplete = len(our_desc.split()) + 2 < len(ref_desc.split())
    return ratio < threshold or incomplete


def detect_spelling_errors(our_text: str, reference_text: str):
    our_tokens = TOKEN_RE.findall(normalize_description(our_text))
    ref_tokens = TOKEN_RE.findall(normalize_description(reference_text))
    issues = []
    for our_token in our_tokens:
        if our_token in ref_tokens:
            continue
        best_match = ""
        best_score = 0.0
        for ref_token in ref_tokens:
            score = SequenceMatcher(None, our_token, ref_token).ratio()
            if score > best_score:
                best_score = score
                best_match = ref_token
        if best_score >= 0.82 and best_match and our_token != best_match:
            issues.append({"our": our_token, "reference": best_match})
    unique = []
    seen = set()
    for issue in issues:
        key = (issue["our"], issue["reference"])
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique

