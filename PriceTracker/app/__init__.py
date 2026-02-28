from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from flask_login import LoginManager
import logging
from config import Config
from app.models.models import db, User

background_scheduler = BackgroundScheduler()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    """
    Application factory pattern.
    Creates and configures the Flask instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from app.routes.views import bp as main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # ── Global template context ──────────────────────────────────────────────
    # Inject notification variables into ALL templates so base.html always works
    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        from app.models.models import Notification
        if current_user.is_authenticated:
            try:
                unread_count  = current_user.notifications.filter_by(is_read=False).count()
                recent_notifs = current_user.notifications.order_by(
                    Notification.created_at.desc()).limit(10).all()
            except Exception:
                unread_count, recent_notifs = 0, []
        else:
            unread_count, recent_notifs = 0, []
        return dict(unread_count=unread_count, recent_notifs=recent_notifs)

    return app

def start_scheduler(app):
    """
    Starts the APScheduler background tasks using the application context.
    """
    import app.scheduler.tasks as scheduler_tasks
    interval_hours = app.config.get('CHECK_INTERVAL', 6)
    
    # Store app config in scheduler so it can create contexts later
    if not background_scheduler.get_job('price_check'):
        background_scheduler.add_job(
            id='price_check',
            func=scheduler_tasks.check_prices,
            trigger='interval',
            hours=interval_hours
        )
        background_scheduler.start()
        app.logger.info(f"Background Scheduler started. Running every {interval_hours} hours.")
