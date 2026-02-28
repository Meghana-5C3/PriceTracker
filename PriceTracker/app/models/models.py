from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association table for User <-> Product (Many-to-Many)
user_products = db.Table('user_products',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('target_price', db.Float, nullable=True),
    db.Column('wishlisted', db.Boolean, default=False),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    """
    Model representing an authenticated user.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin    = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Settings (Phase 1)
    check_interval = db.Column(db.Integer, default=6) # hours
    min_drop_alert_pct = db.Column(db.Float, default=1.0) # minimum percentage to alert
    
    # Relationships
    tracked_products = db.relationship('Product', secondary=user_products, lazy='subquery',
                                       backref=db.backref('tracked_by', lazy=True))
    otps = db.relationship('OTP', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class OTP(db.Model):
    """
    Model storing One Time Passwords for Email Verification.
    """
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)


class Notification(db.Model):
    """
    In-app notification model (Phase 2: Notification Center).
    Stores events like price drops, scrape failures, new products.
    """
    __tablename__ = 'notifications'

    SEVERITY_NORMAL = 'normal'    # < 5% drop
    SEVERITY_HOT = 'hot'          # 15%+ drop  🔥
    SEVERITY_MEGA = 'mega'        # 30%+ drop  🚀

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    message = db.Column(db.String(512), nullable=False)
    type = db.Column(db.String(50), default='info')   # info, drop, error, stock
    severity = db.Column(db.String(20), default='normal')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))


class Product(db.Model):
    """
    Model representing a tracked e-commerce product.
    """
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(255), nullable=True)
    url = db.Column(db.String(2048), unique=True, nullable=False)
    image_url = db.Column(db.String(2048), nullable=True)
    last_price = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to historical prices
    history = db.relationship('PriceHistory', backref='product', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        prices = [h.price for h in self.history if h.price is not None]
        return {
            "id": self.id,
            "name": self.product_name or "Fetching details…",
            "url": self.url,
            "image": self.image_url,
            "current_price": self.last_price,
            "lowest_ever": min(prices) if prices else None,
            "highest_ever": max(prices) if prices else None,
            "price_checks": len(prices),
            "tracked_since": self.created_at.strftime('%d %b %Y')
        }


class PriceHistory(db.Model):
    """
    Model storing historical price records for products.
    """
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "price": self.price,
            "checked_at": self.checked_at.isoformat()
        }
