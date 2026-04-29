from comparator.description_checker import descriptions_differ, detect_spelling_errors
from comparator.image_checker import missing_image_issue
from comparator.item_matcher import best_item_match, similarity, clean_item_name
from comparator.price_checker import price_difference
from processing.normalize_menu import normalize_menu


def compare_menus(our_menu, reference_menu):
    """Compare two menus and return a detailed report of differences.

    Matching is based on fuzzy similarity of *cleaned* item names — dietary
    tags, portion sizes, embedded prices and slash-suffixes are stripped before
    comparison so that e.g. "Yellow Curry Chicken" matches
    "Yellow Curry Chicken / Rice (GF) $13.95".
    """
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

        # Collect ALL differences for this matched pair
        differences = []

        # Check price
        price_issue = price_difference(match, reference_item)
        if price_issue:
            differences.append("price")

        # Check category
        our_cat = match.get("category", "").strip().lower()
        ref_cat = reference_item.get("category", "").strip().lower()
        if our_cat != ref_cat:
            differences.append("category")

        # Check description
        if descriptions_differ(match, reference_item):
            differences.append("description")

        # Check name similarity (even matched items may have slightly different names)
        name_score = similarity(match.get("item", ""), reference_item.get("item", ""))
        if name_score < 99:
            differences.append("name_variation")

        report["matched_items"].append({
            "our_item": match.get("item", ""),
            "our_item_clean": clean_item_name(match.get("item", "")),
            "reference_item": reference_item.get("item", ""),
            "reference_item_clean": clean_item_name(reference_item.get("item", "")),
            "score": round(score, 2),
            "our_price": match.get("price", ""),
            "reference_price": reference_item.get("price", ""),
            "our_category": match.get("category", ""),
            "reference_category": reference_item.get("category", ""),
            "our_description": match.get("description", ""),
            "reference_description": reference_item.get("description", ""),
            "our_image": match.get("image", ""),
            "reference_image": reference_item.get("image", ""),
            "differences": differences,
            "is_perfect_match": len(differences) == 0,
        })

    report["extra_items"].extend(remaining_our)

    # Build detailed issue lists from matched pairs
    for pair_info in report["matched_items"]:
        our_item_dict = {"item": pair_info["our_item"], "price": pair_info["our_price"],
                         "category": pair_info["our_category"], "description": pair_info["our_description"],
                         "image": pair_info.get("our_image", "")}
        ref_item_dict = {"item": pair_info["reference_item"], "price": pair_info["reference_price"],
                         "category": pair_info["reference_category"], "description": pair_info["reference_description"],
                         "image": pair_info.get("reference_image", "")}

        if "category" in pair_info["differences"]:
            report["category_mismatches"].append({
                "item": pair_info["reference_item"],
                "our_item": pair_info["our_item"],
                "our_category": pair_info["our_category"],
                "reference_category": pair_info["reference_category"],
                "reason": f"'{pair_info['our_item']}' is in '{pair_info['our_category']}' but reference has it in '{pair_info['reference_category']}'",
            })

        if "price" in pair_info["differences"]:
            report["price_mismatches"].append({
                "item": pair_info["reference_item"],
                "our_item": pair_info["our_item"],
                "our_price": pair_info["our_price"],
                "reference_price": pair_info["reference_price"],
                "reason": f"Our price ${pair_info['our_price']} vs reference ${pair_info['reference_price']}",
            })

        if "description" in pair_info["differences"]:
            report["description_mismatches"].append({
                "item": pair_info["reference_item"],
                "our_item": pair_info["our_item"],
                "our_description": pair_info["our_description"],
                "reference_description": pair_info["reference_description"],
                "reason": "Description text differs between our menu and reference",
            })

        for issue in detect_spelling_errors(
                pair_info["our_description"], pair_info["reference_description"]):
            report["spelling_errors"].append({
                "item": pair_info["reference_item"],
                "our_item": pair_info["our_item"],
                "field": "description", **issue,
            })

        if "name_variation" in pair_info["differences"]:
            for issue in detect_spelling_errors(
                    pair_info["our_item"], pair_info["reference_item"]):
                report["spelling_errors"].append({
                    "item": pair_info["reference_item"],
                    "our_item": pair_info["our_item"],
                    "field": "item_name", **issue,
                })

        img_issue = missing_image_issue(our_item_dict, ref_item_dict)
        if img_issue:
            report["missing_images"].append(img_issue)

    report["summary"] = {
        "our_total": len(our_items),
        "reference_total": len(reference_items),
        "matched_total": len(matched_pairs),
        "perfect_matches": sum(1 for m in report["matched_items"] if m["is_perfect_match"]),
        "items_with_differences": sum(1 for m in report["matched_items"] if not m["is_perfect_match"]),
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
    """Return a normalized list of menu item dicts."""
    if isinstance(menu_data, list) and menu_data and isinstance(menu_data[0], dict) and "item" in menu_data[0]:
        return menu_data
    return normalize_menu(menu_data)

