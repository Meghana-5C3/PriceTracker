import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-super-secret-key')
    
    # Database Configuration
    # Uses SQLite by default, can be overridden with DATABASE_URL in .env for PostgreSQL
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'pricetracker.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email Settings
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    
    # Scheduler Settings (hours)
    CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 6))
