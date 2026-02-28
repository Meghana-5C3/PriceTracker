import httpx
import asyncio
import random
import logging
from urllib.parse import urlparse
from .parser import parse_product_html, config
from .database import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_random_headers():
    return {
        "User-Agent": random.choice(config["user_agents"]),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.google.com/",
    }

async def fetch_url(client: httpx.AsyncClient, url: str) -> str:
    """Fetches the HTML content of a URL with retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.get(
                url, 
                headers=get_random_headers(), 
                timeout=20.0, 
                follow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.warning(f"403 Forbidden for {url}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            logger.error(f"Error fetching {url}: {e}")
            break
    return None

def get_domain(url: str) -> str:
    """Extracts the base domain from a URL."""
    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

async def scrape_product(client: httpx.AsyncClient, product: Product) -> dict:
    """Scrape a single product."""
    logger.info(f"Scraping {product.url}...")
    html = await fetch_url(client, product.url)
    if not html:
        return None
        
    domain = get_domain(product.url)
    data = parse_product_html(html, domain)
    return {"product_id": product.id, "data": data}

async def fetch_product_data(url: str) -> dict:
    """Fetches product details from URL for new products."""
    async with httpx.AsyncClient() as client:
        html = await fetch_url(client, url)
        if not html:
            return None
        domain = get_domain(url)
        data = parse_product_html(html, domain)
        return data

async def scrape_all_products(products: list[Product]) -> list[dict]:
    """Scrapes a list of products concurrently."""
    async with httpx.AsyncClient() as client:
        tasks = [scrape_product(client, product) for product in products]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
