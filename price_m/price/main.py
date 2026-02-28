import sys
import os
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.database import init_db, get_session, Product, PriceHistory
from core.scraper import scrape_all_products
from core.notifier import send_price_drop_email

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def seed_database():
    """Populates the database with some example URLs for demonstration purposes."""
    db = get_session()
    if db.query(Product).count() == 0:
        logger.info("Seeding database with example products...")
        examples = [
            Product(
                url="https://www.walmart.com/ip/Nintendo-Switch-with-Neon-Blue-and-Neon-Red-Joy-Con/5464902?athbdg=L1600",
                domain="walmart.com",
                target_price=290.00
            ),
            Product(
                url="https://www.bestbuy.com/site/sony-playstation-5-console-white/6426149.p?skuId=6426149",
                domain="bestbuy.com",
                target_price=480.00
            )
        ]
        db.add_all(examples)
        db.commit()
    db.close()

async def track_prices():
    """Main job checking prices and sending alerts."""
    logger.info("Starting price tracking job...")
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
            if not product.name and name:
                product.name = name  # Update name if previously unknown
                
            # Get the most recent stored price
            last_history = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).order_by(PriceHistory.timestamp.desc()).first()
            
            # Save new price
            new_history = PriceHistory(product_id=product_id, price=current_price)
            db.add(new_history)
            
            # Check price drop conditions
            old_price = last_history.price if last_history else None
            
            # Better formatting string
            display_name = product.name if product.name else "Unknown Product"
            logger.info(f"[{product.domain}] {display_name} - Current: ${current_price} | Old: ${old_price} | Target: ${product.target_price}")
            
            if old_price is not None and current_price < old_price:
                # Price has dropped compared to last check
                if product.target_price and current_price <= product.target_price:
                    # Target price reached
                    logger.info(f"ALERT: Price drop detected and target hit for {display_name}!")
                    send_price_drop_email(display_name, product.url, old_price, current_price)
                elif not product.target_price:
                    # Notify on any drop
                    logger.info(f"ALERT: Price drop detected for {display_name}!")
                    send_price_drop_email(display_name, product.url, old_price, current_price)
                else:
                    logger.info(f"Price dropped, but target of ${product.target_price} not yet reached.")

        db.commit()
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        db.rollback()
    finally:
        db.close()
    
    logger.info("Price tracking job completed.")

async def main():
    init_db()
    seed_database()
    
    # Setup scheduler for periodic runs
    scheduler = AsyncIOScheduler()
    scheduler.add_job(track_prices, 'interval', hours=6, next_run_time=datetime.now())
    
    logger.info("Scheduler started. Processing immediately, then every 6 hours. Press Ctrl+C to exit.")
    scheduler.start()
    
    try:
        # Keep the main async loop alive
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
