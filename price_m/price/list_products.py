import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.core.database import Product, DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_products():
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    products = session.query(Product).all()
    
    if not products:
        print("\nNo products found in the database.")
    else:
        print("\n" + "="*80)
        print(f"{'ID':<4} | {'Domain':<15} | {'Target':<10} | {'Name'}")
        print("-" * 80)
        for p in products:
            target = f"${p.target_price}" if p.target_price else "None"
            name = p.name if p.name else "Pending first scrape..."
            print(f"{p.id:<4} | {p.domain:<15} | {target:<10} | {name}")
        print("="*80 + "\n")
    
    session.close()

if __name__ == "__main__":
    list_products()
