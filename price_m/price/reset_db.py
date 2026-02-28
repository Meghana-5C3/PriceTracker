import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.core.database import get_session, Product, PriceHistory, init_db

logging.basicConfig(level=logging.INFO)

def reset_and_seed():
    init_db()
    db = get_session()
    
    # Delete everything
    db.query(PriceHistory).delete()
    db.query(Product).delete()
    
# Seed Products
    adidas = Product(
        url="https://www.adidas.co.in/pureboost-23-shoes/IF2375.html",
        domain="adidas.co.in",
        name="Pureboost 23 Shoes",
        image_url="https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/7cd6bc559ed141c28c6eaf4b00a6e60b_9366/Pureboost_23_Shoes_White_IF2375_01_standard.jpg",
        category="fashion"
    )
    amazon = Product(
        url="https://www.amazon.in/BSB-HOME-Bedsheet-Breathable-Wrinkle/dp/B0F99WNFW1",
        domain="amazon.in",
        name="Double Bed Bedsheet Set",
        image_url="https://m.media-amazon.com/images/I/81z3W8kXQyL._SL1500_.jpg",
        category="grocery"
    )
    iphone = Product(
        url="https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4",
        domain="flipkart.com",
        name="iPhone 15 (Black, 128 GB)",
        image_url="https://rukminim2.flixcart.com/image/832/832/xif0q/mobile/h/d/9/-original-imagtc2qzgnnzuwp.jpeg",
        category="electronics"
    )
    
    db.add_all([adidas, amazon, iphone])
    db.commit()
    
    # Add Price History
    db.add_all([
        PriceHistory(product_id=adidas.id, price=12999.0),
        PriceHistory(product_id=adidas.id, price=6499.5),
        PriceHistory(product_id=amazon.id, price=229.0),
        PriceHistory(product_id=iphone.id, price=54900.0)
    ])
    
    db.commit()
    db.close()
    print("Database reset and seeded with working products and history.")

if __name__ == "__main__":
    # Ensure tracker.db is deleted for a clean start
    # Based on database.py, it's in the 'data' directory relative to project root
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'tracker.db')
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Deleted old database: {DB_FILE}")
    reset_and_seed()
