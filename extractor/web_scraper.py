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
# Markers that ALWAYS indicate a bot protection page regardless of size
_STRONG_BOT_MARKERS = (
    "enable javascript and cookies to continue",
    "cf-browser-verification",
    "having trouble accessing google search",
    "attention required! | cloudflare",
    "checking your browser",
)

# Markers that only indicate a bot page when the HTML is small (<50KB).
# Large pages may contain these as part of normal Cloudflare infrastructure
# scripts (e.g. cf-chl in CDN script URLs on DoorDash/order.online).
_WEAK_BOT_MARKERS = (
    "challenge-platform",
    "just a moment...",
    "__cf_chl",
    "cf-chl",
)


def _is_bot_protection_page(html):
    lowered_html = str(html or "").lower()
    if any(marker in lowered_html for marker in _STRONG_BOT_MARKERS):
        return True
    # Only check weak markers on small pages (real content pages are large)
    if len(lowered_html) < 50000:
        if any(marker in lowered_html for marker in _WEAK_BOT_MARKERS):
            return True
    return False


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


def _fetch_with_playwright(url, wait_seconds=30):
    """Fetch page using Playwright with system Chrome to bypass Cloudflare.

    Runs in a **subprocess** to avoid asyncio/greenlet conflicts with Streamlit.
    Uses the system-installed Chrome browser (via channel='chrome') which has
    a genuine browser fingerprint that Cloudflare trusts more than Playwright's
    bundled Chromium.
    """
    import subprocess
    import sys
    import tempfile
    import os
    from pathlib import Path

    print(f"[playwright] Starting subprocess for {url[:80]}...", flush=True)

    # Resolve the correct Python executable (prefer venv over system Python)
    venv_python = Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        python_exe = str(venv_python)
    else:
        python_exe = sys.executable
    print(f"[playwright] Using Python: {python_exe}", flush=True)

    # Create a temp file for the output HTML
    fd, tmp_path = tempfile.mkstemp(suffix=".html", prefix="pw_")
    os.close(fd)

    try:
        result = subprocess.run(
            [python_exe, "-m", "extractor._playwright_fetch", url, tmp_path, str(wait_seconds)],
            capture_output=True,
            text=True,
            timeout=wait_seconds + 90,  # generous timeout
            cwd=str(Path(__file__).resolve().parent.parent),  # project root
        )
        print(f"[playwright] Subprocess exit code: {result.returncode}", flush=True)
        if result.stderr:
            print(f"[playwright] stderr: {result.stderr[:500]}", flush=True)

        if result.returncode == 0 and os.path.exists(tmp_path):
            with open(tmp_path, "r", encoding="utf-8") as f:
                html = f.read()
            print(f"[playwright] Got {len(html)} chars from subprocess", flush=True)
            return html if len(html) > 1000 else None
        else:
            print(f"[playwright] Subprocess failed (rc={result.returncode})", flush=True)
            return None
    except subprocess.TimeoutExpired:
        print("[playwright] Subprocess timed out", flush=True)
        return None
    except Exception as exc:
        print(f"[playwright] Exception: {exc}", flush=True)
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _fetch_website_html(url):
    import sys
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
        if response is not None and not _is_bot_protection_page(response.text):
            return response.text
    except Exception:
        pass

    # --- Strategy 4: Playwright with system Chrome (handles JS SPAs + Cloudflare) ---
    try:
        print(f"[web_scraper] Attempting Playwright for {url[:80]}...", flush=True)
        sys.stdout.flush()
        html = _fetch_with_playwright(url, wait_seconds=45)
        if html:
            is_bot = _is_bot_protection_page(html)
            print(f"[web_scraper] Playwright returned {len(html)} chars, bot_page={is_bot}", flush=True)
            if not is_bot:
                return html
        else:
            print("[web_scraper] Playwright returned None", flush=True)
    except Exception as exc:
        import traceback
        print(f"[web_scraper] Playwright exception: {exc}", flush=True)
        traceback.print_exc()

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


# ---------------------------------------------------------------------------
# Hierarchical scraping: categories → subcategories → items
# ---------------------------------------------------------------------------

def _extract_card_based_hierarchy(soup):
    """Extract menu from card-based layouts (e.g. Boons ordering sites).

    Looks for sectioned containers (divs with a heading + item cards inside).
    Each card has separate elements for name, description, price, image.
    """
    hierarchy = {}

    # --- Strategy: find section containers that have a heading + item cards ---
    # Common patterns: div.tabItem, section with h-tag + card children
    _CARD_CLASSES = ("food-item-card", "menu-item", "menu-card", "product-card",
                     "item-card", "dish-card", "menu-item-card")
    _SECTION_CLASSES = ("tabItem", "menu-section", "menu-category",
                        "category-section", "menu-group")

    # Try explicit section containers first
    sections = []
    for cls in _SECTION_CLASSES:
        sections.extend(soup.find_all("div", class_=cls))
    if not sections:
        sections.extend(soup.find_all("section", class_=lambda c: c and
                        any(kw in (c if isinstance(c, str) else " ".join(c))
                            for kw in _SECTION_CLASSES)))

    if not sections:
        return {}

    for section in sections:
        # Find the category heading inside this section
        heading = section.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        cat_name = "Uncategorized"
        if heading:
            raw = heading.get_text(strip=True)
            text = _clean_category_text(raw)
            if text and len(text) > 1 and not _is_noise_line(text):
                cat_name = text

        if cat_name not in hierarchy:
            hierarchy[cat_name] = {"subcategories": {}, "items": []}

        # Find item cards inside this section
        cards = []
        for cls in _CARD_CLASSES:
            cards.extend(section.find_all("div", class_=lambda c: c and
                         cls in (c if isinstance(c, str) else " ".join(c))))
        if not cards:
            # Fallback: look for any div that contains an h6 (item name)
            for div in section.find_all("div", recursive=True):
                if div.find("h6") and div not in cards:
                    cards.append(div)

        seen_names = set()
        for card in cards:
            # Extract item name (h5, h6, or first strong/b)
            name_el = card.find(["h5", "h6"]) or card.find("strong") or card.find("b")
            if not name_el:
                continue
            item_name = clean_text(name_el.get_text(strip=True))
            if not item_name or len(item_name) < 2:
                continue
            if item_name.lower() in seen_names:
                continue
            seen_names.add(item_name.lower())

            # Extract description
            desc = ""
            desc_el = card.find("p")
            if desc_el:
                desc = clean_text(desc_el.get_text(strip=True))

            # Extract price — prefer explicit price elements over full-text scan
            price = None
            price_el = card.find("span", class_=lambda c: c and
                                 "price" in (c if isinstance(c, str) else " ".join(c)))
            if not price_el:
                price_el = card.find(["b", "strong"], class_=lambda c: c and
                                    "price" in (c if isinstance(c, str) else " ".join(c)))
            if price_el:
                price = coerce_price(price_el.get_text(strip=True))
            if price is None:
                # Fallback: find $-prefixed price in card text
                card_text = card.get_text(" ", strip=True)
                dollar_match = re.search(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", card_text)
                if dollar_match:
                    price = round(float(dollar_match.group(1)), 2)
                else:
                    price = coerce_price(card_text)

            # Extract image
            img = ""
            img_el = card.find("img")
            if img_el:
                img = img_el.get("src", "") or img_el.get("data-src", "") or ""

            hierarchy[cat_name]["items"].append({
                "category": cat_name,
                "subcategory": "",
                "item": item_name,
                "price": price,
                "description": desc,
                "image": img,
            })

    # Remove empty categories
    hierarchy = {k: v for k, v in hierarchy.items()
                 if v["items"] or v["subcategories"]}
    return hierarchy


def _extract_heading_based_hierarchy(soup):
    """Walk the DOM using heading tags as category/subcategory markers.

    H1/H2 → main category, H3/H4 → subcategory, leaf tags → items.
    Items must contain a price to be extracted.
    """
    body = soup.find("body") or soup
    hierarchy = {}
    current_cat = None
    current_sub = None

    for element in body.descendants:
        if not hasattr(element, "name") or element.name is None:
            continue
        tag = (element.name or "").lower()

        if tag in ("h1", "h2"):
            raw = element.get_text(strip=True)
            text = _clean_category_text(raw)
            if text and len(text) > 1 and not _is_noise_line(text):
                current_cat = text
                current_sub = None
                if current_cat not in hierarchy:
                    hierarchy[current_cat] = {"subcategories": {}, "items": []}
            continue

        if tag in ("h3", "h4"):
            raw = element.get_text(strip=True)
            text = _clean_category_text(raw)
            if text and len(text) > 1 and not _is_noise_line(text):
                if current_cat is None:
                    current_cat = text
                    if current_cat not in hierarchy:
                        hierarchy[current_cat] = {"subcategories": {}, "items": []}
                else:
                    current_sub = text
                    if current_sub not in hierarchy[current_cat]["subcategories"]:
                        hierarchy[current_cat]["subcategories"][current_sub] = []
            continue

        if tag in ("h5", "h6"):
            raw = element.get_text(strip=True)
            text = _clean_category_text(raw)
            if text and len(text) > 1 and not _is_noise_line(text) and current_cat:
                current_sub = text
                if current_sub not in hierarchy[current_cat]["subcategories"]:
                    hierarchy[current_cat]["subcategories"][current_sub] = []
            continue

        if tag not in _LEAF_TAGS:
            continue

        text = element.get_text(" ", strip=True)
        if not text or len(text) < 3 or len(text) > 300:
            continue
        if _is_noise_line(text):
            continue

        price = coerce_price(text)
        if price is None:
            continue
        name_text = PRICE_RE.sub("", text).replace("$", "").strip(" -|:")
        name_text = clean_text(name_text)
        if not name_text or len(name_text) < 2 or _is_noise_line(name_text):
            continue

        item = {
            "category": current_cat or "Uncategorized",
            "subcategory": current_sub or "",
            "item": name_text,
            "price": price,
            "description": "",
            "image": "",
        }

        if current_cat and current_cat in hierarchy:
            if current_sub and current_sub in hierarchy[current_cat]["subcategories"]:
                hierarchy[current_cat]["subcategories"][current_sub].append(item)
            else:
                hierarchy[current_cat]["items"].append(item)
        else:
            if "Uncategorized" not in hierarchy:
                hierarchy["Uncategorized"] = {"subcategories": {}, "items": []}
            hierarchy["Uncategorized"]["items"].append(item)

    return hierarchy


def _extract_rsc_field(text, field_name, start_pos):
    """Extract a field value from RSC escaped-JSON text starting at start_pos.

    Looks for pattern like: \\"field_name\\":\\"VALUE\\" and returns VALUE.
    Returns (value, end_pos) or (None, start_pos) if not found.
    """
    # Try escaped-quote format first: \"field_name\":\"VALUE\"
    marker = '\\"' + field_name + '\\":\\"'
    idx = text.find(marker, start_pos)
    if idx >= 0:
        val_start = idx + len(marker)
        val_end = text.find('\\"', val_start)
        if val_end >= 0:
            return text[val_start:val_end], val_end + 2
    # Try unescaped format: "field_name":"VALUE"
    marker = '"' + field_name + '":"'
    idx = text.find(marker, start_pos)
    if idx >= 0:
        val_start = idx + len(marker)
        val_end = text.find('"', val_start)
        if val_end >= 0:
            return text[val_start:val_end], val_end + 1
    return None, start_pos


def _extract_spa_menu_hierarchy(soup):
    """Extract menu from JS-rendered SPA pages (DoorDash order.online, etc.).

    DoorDash uses React Server Components (RSC) with a large inline script
    containing the full menu data as serialized JSON with escaped quotes.
    This function parses the RSC payload to extract categories and items.
    """
    hierarchy = {}

    # Find the RSC payload script (large script containing MenuPageItem data)
    rsc_text = ""
    for script in soup.find_all("script"):
        text = script.string or ""
        if len(text) > 50000 and "MenuPageItem" in text:
            rsc_text = text
            break

    if not rsc_text:
        return {}

    # ── Locate all MenuPageItemList blocks (categories) ──
    cat_marker = "MenuPageItemList"
    cat_positions = []  # [(pos, category_name), ...]
    search_pos = 0
    while True:
        idx = rsc_text.find(cat_marker, search_pos)
        if idx < 0:
            break
        # Extract the "name" field right after this marker
        cat_name, _ = _extract_rsc_field(rsc_text, "name", idx)
        if cat_name:
            cat_name = cat_name.replace("\\u0026", "&")
            cat_positions.append((idx, cat_name))
        search_pos = idx + len(cat_marker)

    # ── Locate all MenuPageItem entries (items) ──
    item_marker = '"MenuPageItem"'
    esc_item_marker = '\\"MenuPageItem\\"'
    item_entries = []  # [(pos, name, desc, price, img_url), ...]
    search_pos = 0
    while True:
        # Find next MenuPageItem (try escaped first, then unescaped)
        idx_esc = rsc_text.find(esc_item_marker, search_pos)
        idx_plain = rsc_text.find(item_marker, search_pos)
        candidates = [i for i in [idx_esc, idx_plain] if i >= 0]
        if not candidates:
            break
        idx = min(candidates)

        # Extract fields: name, description, displayPrice, imageUrl
        name, _ = _extract_rsc_field(rsc_text, "name", idx)
        desc, _ = _extract_rsc_field(rsc_text, "description", idx)
        price_str, _ = _extract_rsc_field(rsc_text, "displayPrice", idx)
        img_url, _ = _extract_rsc_field(rsc_text, "imageUrl", idx)

        if name:
            name = name.replace("\\u0026", "&")
            desc = (desc or "").replace("\\u0026", "&")
            # RSC encodes $ as $$ in the payload
            price = None
            if price_str:
                clean_price = price_str.replace("$$", "$")
                pm = re.search(r"\$([0-9]+(?:\.[0-9]{1,2})?)", clean_price)
                if pm:
                    price = round(float(pm.group(1)), 2)
            item_entries.append((idx, name, desc, price, img_url or ""))

        search_pos = idx + 10

    if not cat_positions or not item_entries:
        return {}

    # ── Skip pseudo-categories that duplicate real ones ──
    _SKIP_CATEGORIES = {"most ordered", "popular", "featured items", "trending"}

    # ── Group items by nearest preceding category ──
    # Use per-category dedup so items can appear in their real category even if
    # they also appear in "Most Ordered" etc.  Also skip duplicate category
    # occurrences (RSC payload often contains 2 copies of the full menu).
    processed_cats = set()
    for i, (cpos, cat_name) in enumerate(cat_positions):
        if cat_name.lower() in _SKIP_CATEGORIES:
            continue
        if cat_name in processed_cats:
            continue  # skip duplicate occurrence of same category
        processed_cats.add(cat_name)

        next_cpos = cat_positions[i + 1][0] if i + 1 < len(cat_positions) else len(rsc_text)

        if cat_name not in hierarchy:
            hierarchy[cat_name] = {"subcategories": {}, "items": []}

        seen_in_cat = set()
        for ipos, name, desc, price, img_url in item_entries:
            if ipos <= cpos or ipos >= next_cpos:
                continue
            if name.lower() in seen_in_cat:
                continue
            seen_in_cat.add(name.lower())
            hierarchy[cat_name]["items"].append({
                "category": cat_name,
                "subcategory": "",
                "item": name,
                "price": price,
                "description": desc,
                "image": img_url,
            })

    # Remove empty categories
    hierarchy = {k: v for k, v in hierarchy.items()
                 if v["items"] or v["subcategories"]}
    return hierarchy


def scrape_menu_hierarchy(url):
    """Scrape a website and return a hierarchical dict of categories.

    Tries multiple extraction strategies:
    1. Card-based layout (sectioned containers with item cards)
    2. SPA/JS-rendered pages (DoorDash, Uber Eats, etc.)
    3. Heading-based DOM walk (h1/h2 = category, h3/h4 = subcategory)
    4. Flat fallback via read_website_menu

    Returns
    -------
    dict  { "categories": { "Cat Name": { "subcategories": {...}, "items": [...] }, ... } }
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 is required.") from exc

    html = _fetch_website_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # --- Strategy 1: card-based extraction (Boons, Square, etc.) ---
    hierarchy = _extract_card_based_hierarchy(soup)
    if hierarchy:
        return {"categories": hierarchy}

    # --- Strategy 2: SPA extraction (DoorDash, Uber Eats, etc.) ---
    hierarchy = _extract_spa_menu_hierarchy(soup)
    if hierarchy:
        return {"categories": hierarchy}

    # --- Strategy 3: heading-based DOM walk ---
    clean_soup = BeautifulSoup(html, "html.parser")
    for el in clean_soup.find_all(list(_NOISE_TAGS)):
        el.decompose()
    hierarchy = _extract_heading_based_hierarchy(clean_soup)
    if hierarchy:
        return {"categories": hierarchy}

    # --- Strategy 4: flat fallback ---
    hierarchy = {}
    items = read_website_menu(url, html=html)
    if isinstance(items, list):
        for it in items:
            cat = it.get("category", "Uncategorized")
            if cat not in hierarchy:
                hierarchy[cat] = {"subcategories": {}, "items": []}
            hierarchy[cat]["items"].append(it)

    return {"categories": hierarchy}

