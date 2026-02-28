from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models.models import db, User, Product, PriceHistory, Notification
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Admin Guard ────────────────────────────────────────────────────────────
def admin_required(f):
    """Decorator: only allows users with is_admin=True."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            flash("Admin access required.", "danger")
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def dashboard():
    total_users    = User.query.count()
    total_products = Product.query.count()
    total_checks   = PriceHistory.query.count()
    total_notifs   = Notification.query.count()

    # Latest 10 users
    users = User.query.order_by(User.created_at.desc()).limit(10).all()

    # Top 5 most tracked products
    top_products = (
        db.session.query(Product, func.count(Product.id).label('track_count'))
        .join(Product.tracked_by)
        .group_by(Product.id)
        .order_by(func.count(Product.id).desc())
        .limit(5)
        .all()
    )

    # Price checks per day (last 7 days)
    recent_checks = (
        db.session.query(
            func.date(PriceHistory.checked_at).label('day'),
            func.count(PriceHistory.id).label('count')
        )
        .group_by(func.date(PriceHistory.checked_at))
        .order_by(func.date(PriceHistory.checked_at).desc())
        .limit(7)
        .all()
    )

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_products=total_products,
                           total_checks=total_checks,
                           total_notifs=total_notifs,
                           users=users,
                           top_products=top_products,
                           recent_checks=list(reversed(recent_checks)))


@admin_bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/toggle_admin/<int:user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own admin status.", "warning")
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f"{'Granted' if user.is_admin else 'Revoked'} admin for {user.email}", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Cannot delete yourself.", "danger")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"Deleted user {user.email}", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/products')
@admin_required
def products():
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=all_products)


# ── Email Test ──────────────────────────────────────────────────────────────
@admin_bp.route('/test_email', methods=['POST'])
@admin_required
def test_email():
    from app.email.email_service import EmailService
    ok = EmailService.send_test_email(current_user.email)
    if ok:
        flash(f"✅ Test email sent to {current_user.email}!", "success")
    else:
        flash("❌ Email failed — check EMAIL_USER and EMAIL_PASSWORD in .env", "danger")
    return redirect(url_for('admin.dashboard'))


# ── Manual Scheduler Trigger ────────────────────────────────────────────────
@admin_bp.route('/run_check', methods=['POST'])
@admin_required
def run_check():
    from app.scheduler.tasks import check_prices
    try:
        check_prices()
        flash("✅ Manual price check completed!", "success")
    except Exception as e:
        flash(f"❌ Price check failed: {e}", "danger")
    return redirect(url_for('admin.dashboard'))


# ── API: scheduler stats ────────────────────────────────────────────────────
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    return jsonify({
        "total_users": User.query.count(),
        "total_products": Product.query.count(),
        "total_price_checks": PriceHistory.query.count(),
        "total_notifications": Notification.query.count(),
    })
