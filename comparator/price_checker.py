def price_difference(our_item, reference_item, tolerance: float = 0.01):
    our_price = our_item.get("price")
    reference_price = reference_item.get("price")
    if our_price is None or reference_price is None:
        return None
    if abs(float(our_price) - float(reference_price)) <= tolerance:
        return None
    return {
        "item": reference_item.get("item"),
        "our_price": our_price,
        "reference_price": reference_price,
    }

