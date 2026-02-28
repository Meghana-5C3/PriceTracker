import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.core.database import get_session, Product, PriceHistory
from data.core.scraper import scrape_all_products
from data.core.notifier import send_price_drop_email

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def update_now():
    """Main job checking prices and sending alerts."""
    logger.info("Starting manual price update...")
    db = get_session()
    try:
        products = db.query(Product).all()
        if not products:
            logger.warning("No products in database to track.")
            return

        results = await scrape_all_products(products)

        for result in results:
            product_id = result["product_id"]
            data = result["data"]
            current_price = data["price"]
            name = data["name"]

            if current_price is None:
                logger.warning(f"Could not parse price for product ID {product_id}. Skipping.")
                continue

            product = db.query(Product).filter(Product.id == product_id).first()
            if not product.name or product.name == "Unknown Product":
                if name:
                    product.name = name
                
            # Get the most recent stored price
            last_history = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).order_by(PriceHistory.timestamp.desc()).first()
            
            # Save new price
            new_history = PriceHistory(product_id=product_id, price=current_price)
            db.add(new_history)
            
            # Better formatting string
            display_name = product.name if product.name else "Unknown Product"
            logger.info(f"[{product.domain}] Updated {display_name}: {current_price}")

        db.commit()
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        db.rollback()
    finally:
        db.close()
    
    logger.info("Manual price update completed.")

if __name__ == "__main__":
    asyncio.run(update_now())
