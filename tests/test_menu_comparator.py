import unittest

from comparator.menu_comparator import compare_menus


class MenuComparatorTests(unittest.TestCase):
    def test_compare_menus_detects_core_differences(self):
        our_menu = [
            {
                "category": "Starters",
                "item": "Paneer Tikkaa",
                "price": 12.99,
                "description": "Grilled cottage cheese with spicez",
                "image": "",
            },
            {
                "category": "Drinks",
                "item": "Butter Chicken",
                "price": 15.50,
                "description": "Creamy tomato chicken curry",
                "image": "butter.jpg",
            },
            {
                "category": "Desserts",
                "item": "Gulab Jamun",
                "price": 6.00,
                "description": "Milk dumplings in syrup",
                "image": "gulab.jpg",
            },
        ]
        reference_menu = [
            {
                "category": "Starters",
                "item": "Paneer Tikka",
                "price": 11.99,
                "description": "Grilled cottage cheese with spices",
                "image": "paneer.jpg",
            },
            {
                "category": "Main Course",
                "item": "Butter Chicken",
                "price": 15.50,
                "description": "Creamy tomato chicken curry",
                "image": "butter.jpg",
            },
            {
                "category": "Breads",
                "item": "Garlic Naan",
                "price": 3.99,
                "description": "Tandoor baked naan with garlic",
                "image": "naan.jpg",
            },
        ]

        report = compare_menus(our_menu, reference_menu)

        self.assertEqual(report["summary"]["missing_items"], 1)
        self.assertEqual(report["summary"]["extra_items"], 1)
        self.assertEqual(report["summary"]["price_mismatches"], 1)
        self.assertEqual(report["summary"]["missing_images"], 1)
        self.assertEqual(report["summary"]["category_mismatches"], 1)
        self.assertGreaterEqual(report["summary"]["spelling_errors"], 1)
        self.assertEqual(report["missing_items"][0]["item"], "Garlic Naan")
        self.assertEqual(report["extra_items"][0]["item"], "Gulab Jamun")


if __name__ == "__main__":
    unittest.main()

