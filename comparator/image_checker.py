def missing_image_issue(our_item, reference_item):
    if our_item.get("image"):
        return None
    return {
        "item": reference_item.get("item") or our_item.get("item"),
        "category": reference_item.get("category") or our_item.get("category"),
    }

