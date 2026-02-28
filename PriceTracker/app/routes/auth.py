from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import logging

from app.models.models import db, User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        name     = request.form.get('name', '').strip()

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))

        # First registered user becomes admin automatically
        is_first_user = User.query.count() == 0

        new_user = User(email=email, name=name, is_verified=True, is_admin=is_first_user)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Send welcome email (non-blocking, ignore failure)
        try:
            from app.email.email_service import EmailService
            EmailService.send_welcome_email(email, name)
        except Exception:
            pass

        login_user(new_user)
        role_msg = " You have Admin access." if is_first_user else ""
        flash(f'Welcome to PriceTracker Pro, {name or email}! 🎉{role_msg}', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Incorrect email or password. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name or user.email}! 👋', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
