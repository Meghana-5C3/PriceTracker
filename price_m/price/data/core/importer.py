import os
import sys
import logging
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.core.database import get_session, Product, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_domain(url: str) -> str:
    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def import_urls_from_file(file_path: str):
    """Reads URLs from a file and adds them to the database."""
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return

    db = get_session()
    try:
        # Get first user as default owner if none exists
        admin = db.query(User).first()
        
        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        count = 0
        for url in urls:
            # Check if exists
            product = db.query(Product).filter(Product.url == url).first()
            if not product:
                domain = get_domain(url)
                product = Product(url=url, domain=domain)
                db.add(product)
                db.flush()
                count += 1
                logger.info(f"Imported: {url}")
            
            # Associate with admin user if logged in/exists
            if admin and product not in admin.tracked_products:
                admin.tracked_products.append(product)
        
        db.commit()
        logger.info(f"Successfully imported {count} new URLs.")
    except Exception as e:
        logger.error(f"Error importing URLs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'urls.txt')
    import_urls_from_file(import_file)
