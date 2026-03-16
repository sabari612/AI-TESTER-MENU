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


def looks_like_category(line: str) -> bool:
    lowered = line.lower().rstrip(":")
    short = len(line.split()) <= 4
    no_price = PRICE_RE.search(line) is None
    return no_price and short and (
        line.endswith(":") or line.isupper() or lowered in {"starters", "mains", "desserts", "drinks"}
    )


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


def parse_menu_text(text: str, default_category: str = "Uncategorized") -> List[Dict[str, Any]]:
    lines = [clean_text(line) for line in str(text).splitlines() if clean_text(line)]
    current_category = default_category
    rows: List[Dict[str, Any]] = []
    for line in lines:
        if looks_like_category(line):
            current_category = clean_text(line.rstrip(":"))
            continue
        item, description, price = split_item_line(line)
        if not item or len(item) < 2:
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

