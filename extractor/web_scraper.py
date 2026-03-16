import json
import re

from processing.normalize_menu import (
    parse_menu_text, _is_noise_line, coerce_price, clean_text,
    looks_like_category, PRICE_RE,
)

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


_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_LEAF_TAGS = {"td", "li", "p", "a", "span"}
_CATEGORY_SUFFIX_RE = re.compile(r"(?i)(categories|category|items?)$")
_NOISE_TAGS = frozenset([
    "script", "style", "nav", "footer", "header", "aside", "form",
    "button", "input", "select", "textarea", "iframe", "noscript",
    "svg", "canvas",
])
_NOISE_CLASS_KEYWORDS = frozenset([
    "cart", "sidebar", "navbar", "footer", "nav",
    "checkout", "modal", "popup", "cookie", "banner", "social",
    "login", "signup", "search", "accessibility",
])


def _clean_category_text(text):
    """Strip trailing 'Categories' / 'Category' button text from headings."""
    cleaned = _CATEGORY_SUFFIX_RE.sub("", text).strip()
    return clean_text(cleaned) if cleaned else ""


def _is_noise_element(element):
    """Check if an element or any ancestor is a noise container."""
    tag = (element.name or "").lower()
    if tag in _NOISE_TAGS:
        return True
    classes = " ".join(element.get("class", [])).lower() if hasattr(element, "get") else ""
    el_id = (element.get("id", "") or "").lower() if hasattr(element, "get") else ""
    role = (element.get("role", "") or "").lower() if hasattr(element, "get") else ""
    if role in ("navigation", "banner", "contentinfo", "complementary"):
        return True
    for kw in _NOISE_CLASS_KEYWORDS:
        if kw in classes or kw in el_id:
            return True
    return False


def _ancestor_is_noise(element):
    """Check if any ancestor of element is a noise container."""
    parent = element.parent
    while parent:
        if hasattr(parent, "name") and parent.name:
            if _is_noise_element(parent):
                return True
        parent = getattr(parent, "parent", None)
    return False


def _extract_structured_menu(soup):
    """Walk the DOM in document order without modifying it.

    Uses headings as category markers, skips noise elements programmatically.
    Returns a list of menu item dicts, or empty list if extraction fails.
    """
    body = soup.find("body") or soup
    current_category = "Uncategorized"
    rows = []
    seen_names = set()  # normalized name for dedup

    for element in body.descendants:
        if not hasattr(element, "name") or element.name is None:
            continue

        tag = (element.name or "").lower()

        # --- Heading = potential category (check BEFORE noise skip) ---
        if tag in _HEADING_TAGS:
            raw = element.get_text(strip=True)
            heading_text = _clean_category_text(raw)
            if heading_text and len(heading_text) > 1 and not _is_noise_line(heading_text):
                if looks_like_category(heading_text) or heading_text.isupper():
                    current_category = heading_text
            continue

        # Skip non-leaf tags
        if tag not in _LEAF_TAGS:
            continue

        # Skip noise elements and elements inside noise containers
        if _is_noise_element(element) or _ancestor_is_noise(element):
            continue

        text = element.get_text(" ", strip=True)
        if not text or len(text) < 3 or len(text) > 300:
            continue
        if _is_noise_line(text):
            continue

        # Require a price for confident item extraction
        price = coerce_price(text)
        if price is None:
            continue

        # Extract item name by removing price
        name_text = PRICE_RE.sub("", text).replace("$", "").strip(" -|:")
        name_text = clean_text(name_text)
        if not name_text or len(name_text) < 2 or _is_noise_line(name_text):
            continue

        # Dedup by name only (same item may appear with/without price)
        dedup_key = name_text.lower()
        if dedup_key in seen_names:
            continue
        seen_names.add(dedup_key)

        rows.append({
            "category": current_category,
            "item": name_text,
            "price": price,
            "description": "",
            "image": "",
        })

    return rows



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

    # --- Strategy A: structured JSON-LD data ---
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.get_text(strip=True))
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("hasMenu"):
                return candidate["hasMenu"]

    # --- Strategy B: structured DOM extraction (preserves headings) ---
    # Walk the DOM WITHOUT destroying it first — noise is skipped programmatically
    # so that heading/category structure is preserved.
    items = _extract_structured_menu(soup)
    if items:
        return items

    # --- Strategy C: fallback to flat text extraction ---
    # Remove noise elements, then extract remaining text
    for el in soup.find_all(list(_NOISE_TAGS)):
        el.decompose()
    for el in soup.find_all(["script", "style"]):
        el.decompose()
    body = soup.find("body") or soup
    raw_text = body.get_text("\n", strip=True)
    return parse_menu_text(raw_text)


# Re-use the comprehensive noise filter from normalize_menu
_is_noise_text = _is_noise_line

