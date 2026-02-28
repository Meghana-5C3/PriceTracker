import requests
from bs4 import BeautifulSoup
import logging
import time

logger = logging.getLogger(__name__)

class ProductScraper:
    """
    A reusable class for scraping e-commerce product pages robustly.
    Handles headers, timeouts, and specific layouts for Amazon and Flipkart.
    """
    def __init__(self, url):
        self.url = url
        self.soup = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch_html(self, retries=3, delay=2):
        """Fetches HTML content with retries and timeout handling."""
        for attempt in range(retries):
            try:
                response = requests.get(self.url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    self.soup = BeautifulSoup(response.content, 'html.parser')
                    return True
                elif response.status_code == 404:
                    logger.error(f"Product not found (404): {self.url}")
                    return False
                else:
                    logger.warning(f"Attempt {attempt+1}: Status Code {response.status_code} for {self.url}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt+1} - Request exception for {self.url}: {e}")
            
            # Wait before retrying
            if attempt < retries - 1:
                time.sleep(delay)
                
        logger.error(f"Failed to fetch {self.url} after {retries} attempts.")
        return False

    def extract_name(self):
        """Extracts the product name based on common e-commerce layouts."""
        if not self.soup:
            return None
            
        # Amazon Layout
        title = self.soup.find(id='productTitle')
        if title:
            return title.get_text(strip=True)
            
        # Flipkart Layout
        title = self.soup.find('span', class_='B_NuCI') or self.soup.find('span', class_='VU-T81')
        if title:
            return title.get_text(strip=True)
            
        # Generic Fallback
        meta_og_title = self.soup.find("meta", property="og:title")
        if meta_og_title:
             return meta_og_title["content"]
             
        title_tag = self.soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
            
        return "Unknown Product"

    def extract_price(self):
        """Extracts the product price based on common e-commerce layouts."""
        if not self.soup:
            return None
            
        # Try finding standard price containers across sites
        price_selectors = [
            ('span', 'a-price-whole'),             # Amazon Main
            ('span', 'a-offscreen'),               # Amazon Alternate
            ('div', 'Nx9bqj CxhGGd'),              # Flipkart New Layout
            ('div', '_30jeq3 _16Jk6d'),            # Flipkart Old Layout
        ]
        
        for tag, class_name in price_selectors:
            price_element = self.soup.find(tag, class_=class_name)
            if price_element:
                text = price_element.get_text(strip=True)
                # Clean up currency symbols and commas (e.g., '₹1,299' -> 1299.0)
                cleaned = ''.join(c for c in text if c.isdigit() or c == '.')
                try:
                    if cleaned:
                        return float(cleaned)
                except ValueError:
                    continue
                    
        return None

    def extract_image(self):
        """Extracts the main product image."""
        if not self.soup:
            return None
            
        # Amazon
        img = self.soup.find(id='landingImage')
        if img and img.get('src'):
            return img.get('src')
            
        # Flipkart
        img = self.soup.find('img', class_='_396cs4 _2amPTt _3qGmMb') or self.soup.find('img', class_='DByuf4')
        if img and img.get('src'):
            return img.get('src')
            
        # Generic OG image
        meta_og_image = self.soup.find('meta', property='og:image')
        if meta_og_image:
            return meta_og_image['content']
            
        return None

    def get_product_details(self):
        """Convenience method to execute full scrape."""
        if self.fetch_html():
            return {
                "name": self.extract_name(),
                "price": self.extract_price(),
                "image_url": self.extract_image()
            }
        return None
