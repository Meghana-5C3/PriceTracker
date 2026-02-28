"""
URL Cleaner Utility.
Extracts a canonical, clean product URL from messy Amazon/Flipkart tracking links.
"""
import re
from urllib.parse import urlparse, parse_qs


def clean_url(raw_url: str) -> str:
    """
    Given any Amazon or Flipkart URL (including sponsored / affiliate / redirect links),
    return the shortest clean canonical URL.

    Examples:
        amazon.in/sspa/click?...url=%2Fdp%2FB0XYZ → https://www.amazon.in/dp/B0XYZ
        amazon.in/some-product/dp/B0ABC123/ref=... → https://www.amazon.in/dp/B0ABC123
        flip.kart.com/product?pid=ITEM123          → unchanged (best effort)
    """
    raw_url = raw_url.strip()

    # ── Amazon ──────────────────────────────────────────────────────────────
    if 'amazon.' in raw_url:
        # Case 1: Sponsored redirect — the real URL is in the `url` query param
        # e.g. amazon.in/sspa/click?...&url=%2Fdp%2FB0XYZ%2F...
        parsed = urlparse(raw_url)
        qs = parse_qs(parsed.query)
        if 'url' in qs:
            inner = qs['url'][0]   # e.g. /BRAND/dp/B0XYZ/ref=...
            # Extract ASIN from inner path
            asin = _extract_amazon_asin(inner)
            if asin:
                return f"https://www.amazon.in/dp/{asin}"

        # Case 2: Normal or ref-bloated Amazon URL
        asin = _extract_amazon_asin(raw_url)
        if asin:
            return f"https://www.amazon.in/dp/{asin}"

    # ── Flipkart ────────────────────────────────────────────────────────────
    if 'flipkart.com' in raw_url:
        # Strip all query params except pid and lid
        parsed = urlparse(raw_url)
        qs = parse_qs(parsed.query)
        pid = qs.get('pid', [''])[0]
        # Clean path: keep only up to /p/ segment
        clean_path = re.sub(r'\?.*', '', raw_url)
        return clean_path if not pid else f"{clean_path}?pid={pid}"

    # ── Fallback: return as-is ───────────────────────────────────────────────
    return raw_url


def _extract_amazon_asin(url_or_path: str) -> str | None:
    """Extract a 10-character Amazon ASIN from a URL or path string."""
    # Match /dp/ASIN or /gp/product/ASIN
    match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url_or_path)
    if match:
        return match.group(1)
    return None
