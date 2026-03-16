import json
import re
from typing import Any, Dict, List

PRICE_RE = re.compile(r"(?:USD|\$|₹|€|£)?\s*([0-9]+(?:\.[0-9]{1,2})?)")


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def coerce_price(value: Any):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    match = PRICE_RE.search(str(value))
    return round(float(match.group(1)), 2) if match else None


def normalize_record(record: Dict[str, Any], default_category: str = "Uncategorized") -> Dict[str, Any]:
    return {
        "category": clean_text(record.get("category") or default_category),
        "item": clean_text(record.get("item") or record.get("name") or record.get("title")),
        "price": coerce_price(record.get("price") or record.get("amount")),
        "description": clean_text(record.get("description") or record.get("details")),
        "image": clean_text(record.get("image") or record.get("image_url") or record.get("img")),
    }


def _from_category_blocks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for category in data.get("categories", []):
        cat_name = clean_text(category.get("name") or category.get("category") or "Uncategorized")
        for item in category.get("items", []):
            row = dict(item)
            row.setdefault("category", cat_name)
            rows.append(row)
    return rows


def normalize_menu(raw_menu: Any, default_category: str = "Uncategorized") -> List[Dict[str, Any]]:
    if raw_menu is None:
        return []
    if isinstance(raw_menu, str):
        raw_text = raw_menu.strip()
        if not raw_text:
            return []
        try:
            raw_menu = json.loads(raw_text)
        except json.JSONDecodeError:
            return parse_menu_text(raw_text, default_category)
    if isinstance(raw_menu, dict):
        if "categories" in raw_menu:
            raw_menu = _from_category_blocks(raw_menu)
        elif "items" in raw_menu:
            raw_menu = raw_menu["items"]
        elif "menu" in raw_menu:
            raw_menu = raw_menu["menu"]
        else:
            raw_menu = [raw_menu]
    normalized: List[Dict[str, Any]] = []
    for entry in raw_menu:
        if isinstance(entry, dict):
            row = normalize_record(entry, default_category)
            if row["item"]:
                normalized.append(row)
        elif isinstance(entry, str):
            normalized.extend(parse_menu_text(entry, default_category))
    return normalized


_KNOWN_CATEGORIES = {
    "starters", "mains", "desserts", "drinks", "appetizers", "entrees",
    "sides", "beverages", "soups", "salads", "specials", "extras",
    "ramen", "fried", "fish", "rice", "noodles", "sushi", "sashimi",
    "rolls", "soft drinks", "beer", "wine", "sake", "cocktails",
    "lunch specials", "dinner specials", "teishoku", "donburi",
    "salad", "side dishes", "side orders", "add ons", "add-ons",
}

# Lines that look like categories but are actually noise
_FAKE_CATEGORY_NOISE = re.compile(
    r"(?i)^(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"home|about|login|sign up|sign in|register|hours?|open|closed|"
    r"search|cart|order|checkout|total|subtotal|tax|qty|clear|submit|"
    r"terms|privacy|faq|careers|locations?|contact|phone|email|"
    r"get to know|let us help|doing business|connect with|"
    r"online ordering|est wait|wait time|your order|powered by|"
    r"managed by|order by phone|no refunds|pickup|delivery|"
    r"open\s+hours?|operating\s+hours?|business\s+hours?|"
    r"est\s+wait|wait\s+time|categories|asap)s?:?$"
)


def looks_like_category(line: str) -> bool:
    lowered = line.lower().rstrip(":")
    word_count = len(line.split())
    short = word_count <= 5
    no_price = PRICE_RE.search(line) is None
    if not no_price or not short:
        return False
    # Reject known noise patterns
    if _FAKE_CATEGORY_NOISE.match(line.strip()):
        return False
    # Accept if it matches known food categories
    if lowered in _KNOWN_CATEGORIES:
        return True
    # Lines ending with ":" are likely categories (up to 4 words)
    if line.endswith(":") and word_count <= 4:
        return True
    # For ALL CAPS lines, only treat as category if very short (1-2 words)
    # because many menu items are displayed in uppercase
    if line.isupper() and word_count <= 2:
        return True
    return False


def split_item_line(line: str):
    price = coerce_price(line)
    line_wo_price = PRICE_RE.sub("", line).replace("$", "").strip(" -|:")
    for sep in (" - ", " | ", ": "):
        if sep in line_wo_price:
            item, desc = line_wo_price.split(sep, 1)
            return clean_text(item), clean_text(desc), price
    parts = [part.strip() for part in line_wo_price.split(".", 1)]
    if len(parts) == 2 and len(parts[0].split()) <= 5:
        return clean_text(parts[0]), clean_text(parts[1]), price
    return clean_text(line_wo_price), "", price


_NOISE_LINE_RE = re.compile(
    r"(?i)("
    # Days of the week / time
    r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"|^[0-9:]*\s*(am|pm)\s*[-–]?\s*[0-9:]*\s*(am|pm)?\s*$"
    r"|\b(open|business|operating)\s*hours?\b"
    # Navigation / UI elements
    r"|^(home|about|login|sign up|sign in|register|log out|forgot password)"
    r"|^(hours?|open|closed|we are|visit us|follow us|connect with)"
    r"|^(clear|submit|cancel|close|back|next|previous|view|more|less)"
    r"|^(pickup|delivery|asap|categories|dine.?in|take.?out|curbside)"
    r"|^(search|filter|sort|reset|apply|select|choose|browse)"
    r"|^(add to cart|add to order|customize|modify|edit|update)"
    r"|^(see more|show more|load more|view all|view menu|full menu)"
    # Legal / footer
    r"|terms of (use|service)|privacy policy|cookie|copyright|all rights"
    r"|no refunds|location (mistake|acknowledgement)"
    # Cart / checkout
    r"|your (order|cart)|checkout|subtotal|clear order"
    r"|^(qty|quantity|price|tax|total|subtotal|tip|gratuity)\b"
    # Business info
    r"|managed by|powered by|developed by|built with"
    r"|phone|fax|email|contact us|call us|order by phone"
    r"|get to know|let us help|doing business"
    # Form / validation
    r"|enter valid|passcode|incorrect|are you sure|code has been"
    r"|search for|please enter|online ordering|est wait|wait time"
    # Address patterns
    r"|\d+\s+(road|street|st|ave|blvd|dr|suite|suit|canyon|way|ln|ct)\b"
    r"|\b(road|blvd|boulevard|canyon|avenue|street)\b.*\b(suite?|suit)\b"
    r"|\b(ca|california|tx|texas|ny|new york)\s+\d{5}\b"
    r"|\bsan\s+(ramon|francisco|jose|diego|mateo)\b"
    # Phone numbers
    r"|\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    r")"
)

# Standalone noise words / very short fragments
_NOISE_STANDALONE_RE = re.compile(
    r"(?i)^(tax|total|qty|quantity|price|am|pm|mins?|or|and|the|"
    r"yes|no|ok|close|back|next|view|more|less|add|remove|"
    r"popular|featured|new|hot|best seller|recommended|"
    r"required|optional|choose|select|pick|"
    r"mi|km|miles?|minutes?|today|now)[\s\-:.,]*$"
)


def _is_noise_line(line: str) -> bool:
    """Return True if a line of text looks like non-menu noise."""
    stripped = line.strip()
    if len(stripped) < 3:
        return True
    if _NOISE_LINE_RE.search(stripped):
        return True
    if _NOISE_STANDALONE_RE.match(stripped):
        return True
    # Looks like a URL or path fragment
    if stripped.startswith("//") or stripped.startswith("http"):
        return True
    # Single-word non-food items and UI fragments (less than 4 chars)
    if len(stripped.split()) == 1 and len(stripped) < 4 and not stripped[0].isdigit():
        return True
    # Mostly numbers / punctuation (not a real item name)
    alpha_chars = sum(1 for c in stripped if c.isalpha())
    if alpha_chars < 3:
        return True
    return False


def parse_menu_text(text: str, default_category: str = "Uncategorized") -> List[Dict[str, Any]]:
    lines = [clean_text(line) for line in str(text).splitlines() if clean_text(line)]
    current_category = default_category
    rows: List[Dict[str, Any]] = []
    for line in lines:
        # Skip noise lines before any other processing
        if _is_noise_line(line):
            continue
        if looks_like_category(line):
            current_category = clean_text(line.rstrip(":"))
            continue
        item, description, price = split_item_line(line)
        if not item or len(item) < 2:
            continue
        # Additional check: skip items that are clearly not food
        if _is_noise_line(item):
            continue
        rows.append(
            {
                "category": current_category,
                "item": item,
                "price": price,
                "description": description,
                "image": "",
            }
        )
    return rows

