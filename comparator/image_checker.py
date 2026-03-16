def missing_image_issue(our_item, reference_item):
    """Report a missing image only when the reference has one but ours doesn't."""
    ref_image = (reference_item.get("image") or "").strip()
    our_image = (our_item.get("image") or "").strip()
    # Only flag if the reference actually provides an image and ours is missing
    if ref_image and not our_image:
        return {
            "item": reference_item.get("item") or our_item.get("item"),
            "category": reference_item.get("category") or our_item.get("category"),
        }
    return None

