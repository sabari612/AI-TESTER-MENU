import json

from processing.normalize_menu import parse_menu_text

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
BOT_PROTECTION_MARKERS = (
    "enable javascript and cookies to continue",
    "__cf_chl",
    "cf-chl",
    "challenge-platform",
    "cf-browser-verification",
)


def _is_bot_protection_page(html):
    lowered_html = str(html or "").lower()
    return any(marker in lowered_html for marker in BOT_PROTECTION_MARKERS)


def _blocked_website_message(url):
    return (
        f"Unable to extract menu from {url} because the website blocks automated access "
        "(for example, Cloudflare or another bot-protection service). "
        "Please provide the menu as JSON, PDF, image, Word document, or pasted text instead."
    )


def _fetch_with_requests(url):
    """Attempt a plain requests fetch."""
    import requests

    with requests.Session() as session:
        response = session.get(url, headers=REQUEST_HEADERS, timeout=20)
    return response


def _fetch_with_cloudscraper(url):
    """Attempt fetch using cloudscraper to bypass Cloudflare."""
    import cloudscraper

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
    )
    response = scraper.get(url, timeout=30)
    return response


def _fetch_with_cache_proxy(url):
    """Attempt fetch via Google/Wayback cache proxies."""
    import requests

    proxied_urls = [
        f"https://webcache.googleusercontent.com/search?q=cache:{url}",
        f"https://web.archive.org/web/2/{url}",
    ]
    last_exc = None
    for proxied_url in proxied_urls:
        try:
            response = requests.get(proxied_url, headers=REQUEST_HEADERS, timeout=25)
            if response.ok and not _is_bot_protection_page(response.text):
                return response
        except requests.RequestException as exc:
            last_exc = exc
    return None


def _fetch_website_html(url):
    try:
        import requests
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("requests and beautifulsoup4 are required for website extraction.") from exc

    # --- Strategy 1: plain requests ---
    try:
        response = _fetch_with_requests(url)
        if response.ok and not _is_bot_protection_page(response.text):
            return response.text
    except requests.RequestException:
        pass  # fall through to next strategy

    # --- Strategy 2: cloudscraper (handles Cloudflare JS challenges) ---
    try:
        response = _fetch_with_cloudscraper(url)
        if response.ok and not _is_bot_protection_page(response.text):
            return response.text
    except Exception:
        pass  # fall through to next strategy

    # --- Strategy 3: cache proxies (Google Cache / Wayback Machine) ---
    try:
        response = _fetch_with_cache_proxy(url)
        if response is not None:
            return response.text
    except Exception:
        pass

    # All strategies failed
    raise RuntimeError(_blocked_website_message(url))


def read_website_menu(url, html=None):
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("requests and beautifulsoup4 are required for website extraction.") from exc

    if html is None:
        html = _fetch_website_html(url)
    elif _is_bot_protection_page(html):
        raise RuntimeError(_blocked_website_message(url))

    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.get_text(strip=True))
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("hasMenu"):
                return candidate["hasMenu"]

    text_blocks = []
    selectors = ["h1", "h2", "h3", "li", "p", ".menu-item", ".product", ".item"]
    for selector in selectors:
        for element in soup.select(selector):
            content = element.get_text(" ", strip=True)
            if content:
                text_blocks.append(content)
    return parse_menu_text("\n".join(dict.fromkeys(text_blocks)))

