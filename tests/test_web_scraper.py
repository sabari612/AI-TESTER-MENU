import unittest
from unittest.mock import Mock, patch

from extractor.web_scraper import read_website_menu


class WebScraperTests(unittest.TestCase):
    def test_read_website_menu_extracts_ld_json_has_menu(self):
        html = """
        <html><body>
        <script type=\"application/ld+json\">[{\"hasMenu\": {\"items\": [{\"name\": \"Burger\"}]}}]</script>
        </body></html>
        """

        result = read_website_menu("https://example.com/menu", html=html)

        self.assertEqual(result, {"items": [{"name": "Burger"}]})

    @patch("extractor.web_scraper._fetch_with_cache_proxy", return_value=None)
    @patch("extractor.web_scraper._fetch_with_cloudscraper")
    @patch("extractor.web_scraper._fetch_with_requests")
    def test_read_website_menu_raises_friendly_message_for_blocked_sites(
        self, mock_requests, mock_cloudscraper, mock_cache
    ):
        blocked_response = Mock(ok=False, status_code=403, text="Enable JavaScript and cookies to continue")
        mock_requests.return_value = blocked_response
        mock_cloudscraper.return_value = blocked_response

        with self.assertRaises(RuntimeError) as context:
            read_website_menu("https://chickenthyme.net/menu")

        self.assertIn("blocks automated access", str(context.exception))
        self.assertIn("JSON, PDF, image, Word document, or pasted text", str(context.exception))


if __name__ == "__main__":
    unittest.main()