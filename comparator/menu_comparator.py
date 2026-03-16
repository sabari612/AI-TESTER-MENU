from comparator.description_checker import descriptions_differ, detect_spelling_errors
from comparator.image_checker import missing_image_issue
from comparator.item_matcher import best_item_match, similarity
from comparator.price_checker import price_difference
from processing.normalize_menu import normalize_menu


def compare_menus(our_menu, reference_menu):
    """Compare two menus and return a detailed report of differences.

    Accepts either raw menu data (will be normalized) or already-normalized
    lists of dicts.  Handles both cases gracefully.
    """
    # Normalize if not already normalized lists of dicts
    our_items = _ensure_normalized(our_menu)
    reference_items = _ensure_normalized(reference_menu)

    remaining_our = list(our_items)
    matched_pairs = []
    report = {
        "summary": {},
        "missing_items": [],
        "extra_items": [],
        "price_mismatches": [],
        "description_mismatches": [],
        "spelling_errors": [],
        "missing_images": [],
        "category_mismatches": [],
        "matched_items": [],
    }

    for reference_item in reference_items:
        match, score = best_item_match(reference_item, remaining_our)
        if not match:
            report["missing_items"].append(reference_item)
            continue
        remaining_our.remove(match)
        matched_pairs.append((match, reference_item, score))
        report["matched_items"].append(
            {"reference_item": reference_item["item"], "our_item": match["item"], "score": round(score, 2)}
        )

    report["extra_items"].extend(remaining_our)

    for our_item, reference_item, score in matched_pairs:
        category_match = our_item.get("category", "").strip().lower() == reference_item.get("category", "").strip().lower()
        if not category_match:
            report["category_mismatches"].append(
                {
                    "item": reference_item.get("item"),
                    "our_category": our_item.get("category"),
                    "reference_category": reference_item.get("category"),
                }
            )

        price_issue = price_difference(our_item, reference_item)
        if price_issue:
            report["price_mismatches"].append(price_issue)

        if descriptions_differ(our_item, reference_item):
            report["description_mismatches"].append(
                {
                    "item": reference_item.get("item"),
                    "our_description": our_item.get("description"),
                    "reference_description": reference_item.get("description"),
                }
            )

        img_issue = missing_image_issue(our_item, reference_item)
        if img_issue:
            report["missing_images"].append(img_issue)

        for issue in detect_spelling_errors(our_item.get("description", ""), reference_item.get("description", "")):
            report["spelling_errors"].append({"item": reference_item.get("item"), "field": "description", **issue})

        if similarity(our_item.get("item", ""), reference_item.get("item", "")) < 99:
            for issue in detect_spelling_errors(our_item.get("item", ""), reference_item.get("item", "")):
                report["spelling_errors"].append({"item": reference_item.get("item"), "field": "item", **issue})

    report["summary"] = {
        "our_total": len(our_items),
        "reference_total": len(reference_items),
        "matched_total": len(matched_pairs),
        "missing_items": len(report["missing_items"]),
        "extra_items": len(report["extra_items"]),
        "price_mismatches": len(report["price_mismatches"]),
        "description_mismatches": len(report["description_mismatches"]),
        "spelling_errors": len(report["spelling_errors"]),
        "missing_images": len(report["missing_images"]),
        "category_mismatches": len(report["category_mismatches"]),
    }
    return report


def _ensure_normalized(menu_data):
    """Return a normalized list of menu item dicts.

    If the data is already a list of dicts with 'item' keys, return as-is.
    Otherwise, run normalize_menu to convert it.
    """
    if isinstance(menu_data, list) and menu_data and isinstance(menu_data[0], dict) and "item" in menu_data[0]:
        return menu_data
    return normalize_menu(menu_data)

