from flask import Blueprint

bp = Blueprint('main', __name__)

# Import views to register the routes
from app.routes import views
