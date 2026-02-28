import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

# Association table for User and Product (many-to-many)
user_product = Table(
    'user_product',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('target_price', Float, nullable=True),
    Column('frequency', String, default='daily'),
    Column('is_paused', Integer, default=0), # 0: active, 1: paused
    Column('created_at', DateTime, default=datetime.utcnow)
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Reward Points System
    redeemable_points = Column(Integer, default=0)
    pending_points = Column(Integer, default=0)
    lifetime_earned_points = Column(Integer, default=0)
    
    referral_code = Column(String, unique=True, nullable=True)
    is_verified = Column(Integer, default=0) # 0: false, 1: true
    
    # Relationships
    tracked_products = relationship('Product', secondary=user_product, back_populates='tracked_by_users')
    reward_transactions = relationship('RewardTransaction', back_populates='user', cascade='all, delete-orphan')

class RewardTransaction(Base):
    __tablename__ = 'reward_transactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Integer, nullable=False)
    type = Column(String, nullable=False) # e.g., "referral", "price_drop_bonus", "gift_card_purchase"
    status = Column(String, default="pending") # "pending", "confirmed"
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='reward_transactions')

class Transaction(Base):
    """Used for the Spend Lens to track mock user spending"""
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    store = Column(String, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class CartItem(Base):
    """Used for the Grocery comparison cart"""
    __tablename__ = 'cart_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True) # allowing null for guest carts initially
    session_id = Column(String, nullable=True) # for guests
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    base_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    domain = Column(String, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to historical prices
    history = relationship('PriceHistory', back_populates='product', cascade='all, delete-orphan')
    tracked_by_users = relationship('User', secondary=user_product, back_populates='tracked_products')

class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    product = relationship('Product', back_populates='history')

# Database setup
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tracker.db')
engine = create_engine(f'sqlite:///{DB_PATH}')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Creates all necessary tables."""
    Base.metadata.create_all(bind=engine)
    
    # Try to add frequency column if it doesn't exist (SQLite simple migration)
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE user_product ADD COLUMN frequency VARCHAR DEFAULT 'daily'"))
            conn.commit()
    except Exception:
        pass

def get_session():
    """Returns a new database session."""
    return SessionLocal()
