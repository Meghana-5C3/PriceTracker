import re
from bs4 import BeautifulSoup
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')

with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

def clean_price(price_str: str) -> float:
    """Removes currency symbols and commas from the price string and converts to float."""
    if not price_str:
        return None
    # Remove everything except digits and decimal point
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_product_html(html: str, domain: str) -> dict:
    """Parses HTML and extracts product title and price based on domain config."""
    domain_config = config['domains'].get(domain)
    if not domain_config:
        # Fallback to generic parsing if domain is not configured
        return {"name": None, "price": None}

    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract Title
    title_element = soup.select_one(domain_config['title_selector'])
    title = title_element.get_text(strip=True) if title_element else "Unknown Product"

    # Extract Price
    price = None
    for selector in domain_config['price_selectors']:
        price_element = soup.select_one(selector)
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = clean_price(price_text)
            if price is not None:
                break
                
    return {"name": title, "price": price}
