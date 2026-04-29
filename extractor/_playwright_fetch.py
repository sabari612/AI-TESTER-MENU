"""Standalone Playwright fetcher — runs as a subprocess to avoid asyncio conflicts.

Usage: python -m extractor._playwright_fetch <url> <output_file> [wait_seconds]

Writes the rendered HTML to <output_file> on success, exits with code 0.
Exits with code 1 on failure.
"""
import sys


def fetch(url, wait_seconds=30):
    """Launch Chrome via Playwright, pass Cloudflare, return rendered HTML."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = None
        for channel in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(
                    channel=channel,
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                break
            except Exception:
                continue
        if browser is None:
            return None

        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait for Cloudflare challenge to resolve
        cf_passed = False
        for i in range(wait_seconds // 3):
            page.wait_for_timeout(3000)
            try:
                title = page.title() or ""
            except Exception:
                continue
            if "just a moment" not in title.lower():
                page.wait_for_timeout(5000)
                cf_passed = True
                break

        if not cf_passed:
            browser.close()
            return None

        html = page.content()
        browser.close()
        return html


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m extractor._playwright_fetch <url> <output_file> [wait_seconds]",
              file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    output_file = sys.argv[2]
    wait_seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    html = fetch(url, wait_seconds)
    if html:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        sys.exit(0)
    else:
        sys.exit(1)
