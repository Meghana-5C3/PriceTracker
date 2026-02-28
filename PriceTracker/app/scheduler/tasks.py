import logging
from app.models.models import db, Product, PriceHistory, Notification, User, user_products
from app.scraper.product_scraper import ProductScraper
from app.email.email_service import EmailService

logger = logging.getLogger(__name__)


def _classify_severity(drop_pct: float) -> str:
    if drop_pct >= 30: return 'mega'
    if drop_pct >= 15: return 'hot'
    return 'normal'


def check_prices():
    """
    Background job: iterates all tracked products, scrapes fresh prices,
    updates history, detects drops, and fires email + in-app notifications.
    """
    logger.info("Scheduler: starting price check…")

    from app import create_app
    app = create_app()

    with app.app_context():
        products = Product.query.all()
        if not products:
            logger.info("Scheduler: no products to check.")
            return

        for product in products:
            logger.info(f"Checking: {product.product_name or product.url}")

            scraper = ProductScraper(product.url)
            details = scraper.get_product_details()

            if not details or details.get('price') is None:
                logger.warning(f"Scheduler: price fetch failed for {product.url}")
                # Notify every user tracking this product
                rows = db.session.execute(
                    user_products.select().where(user_products.c.product_id == product.id)
                ).fetchall()
                for row in rows:
                    db.session.add(Notification(
                        user_id=row.user_id,
                        product_id=product.id,
                        message=f"Scraping failed for \"{product.product_name or 'product'}\". Will retry.",
                        type='error'
                    ))
                db.session.commit()
                continue

            new_price = details['price']
            if not product.product_name and details.get('name'):
                product.product_name = details['name']
            if not product.image_url and details.get('image_url'):
                product.image_url = details['image_url']

            old_price = product.last_price

            # Save history
            db.session.add(PriceHistory(product_id=product.id, price=new_price))
            product.last_price = new_price
            db.session.commit()

            if old_price and new_price < old_price:
                drop_pct = round((old_price - new_price) / old_price * 100, 1)
                severity = _classify_severity(drop_pct)
                emoji = '🚀' if severity == 'mega' else ('🔥' if severity == 'hot' else '📉')
                logger.info(f"{emoji} DROP {drop_pct}% on {product.product_name}")

                # Notify all users tracking this product
                rows = db.session.execute(
                    user_products.select().where(user_products.c.product_id == product.id)
                ).fetchall()
                for row in rows:
                    db.session.add(Notification(
                        user_id=row.user_id,
                        product_id=product.id,
                        message=f"{emoji} {product.product_name}: ₹{old_price:,.0f} → ₹{new_price:,.0f} ({drop_pct}% off)",
                        type='drop',
                        severity=severity
                    ))

                db.session.commit()

                # Email the owner
                with app.app_context():
                    EmailService.send_price_drop_alert(
                        product_name=product.product_name,
                        old_price=old_price,
                        new_price=new_price,
                        url=product.url
                    )

            elif old_price and new_price > old_price:
                logger.info(f"📈 RISE on {product.product_name}: {old_price} → {new_price}")
            else:
                logger.info(f"No change for {product.product_name} ({new_price})")

        logger.info("Scheduler: price check complete.")
