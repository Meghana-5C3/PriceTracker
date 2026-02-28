from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
import logging
from app.models.models import db, Product, PriceHistory, Notification

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)


def _get_severity(drop_pct: float) -> str:
    """Classify price drop severity for alerts."""
    if drop_pct >= 30:
        return 'mega'
    elif drop_pct >= 15:
        return 'hot'
    return 'normal'


def _build_dashboard_data(products):
    """Convert a list of Product objects into enriched dicts for the template."""
    dashboard_data = []
    for p in products:
        history = PriceHistory.query.filter_by(product_id=p.id)\
                                    .order_by(PriceHistory.checked_at.asc()).all()

        prev_price = history[-2].price if len(history) >= 2 else p.last_price
        curr_price = history[-1].price if history else p.last_price

        # Guard: if price is still None (scraper hasn't run yet), skip analytics
        if curr_price is None:
            dashboard_data.append({
                "id": p.id,
                "name": p.product_name or "Fetching details…",
                "url": p.url,
                "image": p.image_url or "https://placehold.co/100x100/e9ecef/6c757d?text=No+Img",
                "current_price": None,
                "previous_price": None,
                "trend": "pending",
                "diff": 0,
                "diff_pct": 0,
                "severity": "normal",
                "lowest": None,
                "highest": None,
                "avg": None,
                "savings_pct": 0,
                "checked_at": "Pending first check…",
                "history_points": [],
                "history_labels": [],
            })
            continue

        trend, diff, diff_pct = "unchanged", 0, 0
        if prev_price and curr_price and prev_price != 0:
            diff = round(float(abs(prev_price - curr_price)), 2)
            diff_pct = round(float(abs(curr_price - prev_price) / prev_price * 100), 1)
            if curr_price < prev_price:
                trend = "down"
            elif curr_price > prev_price:
                trend = "up"

        prices = [h.price for h in history if h.price is not None]
        lowest  = min(prices) if prices else curr_price
        highest = max(prices) if prices else curr_price
        avg     = round(float(sum(prices) / len(prices)), 2) if prices else curr_price
        savings_pct = round(float((highest - curr_price) / highest * 100), 1) if highest else 0

        severity = _get_severity(diff_pct) if trend == "down" else "normal"

        dashboard_data.append({
            "id": p.id,
            "name": p.product_name or "Fetching name…",
            "url": p.url,
            "image": p.image_url or "https://placehold.co/100x100/e9ecef/6c757d?text=No+Img",
            "current_price": curr_price,
            "previous_price": prev_price,
            "trend": trend,
            "diff": diff,
            "diff_pct": diff_pct,
            "severity": severity,
            "lowest": lowest,
            "highest": highest,
            "avg": avg,
            "savings_pct": savings_pct,
            "checked_at": history[-1].checked_at.strftime('%d %b %H:%M') if history else "Never",
            "history_points": prices,
            "history_labels": [h.checked_at.strftime('%m/%d %H:%M') for h in history],
        })
    return dashboard_data


@bp.route('/')
@login_required
def index():
    """Main dashboard — shows per-user tracked products."""
    products = current_user.tracked_products
    dashboard_data = _build_dashboard_data(products)

    # Unread notification count for bell icon
    unread_count = current_user.notifications.filter_by(is_read=False).count()
    recent_notifs = current_user.notifications.order_by(
        Notification.created_at.desc()).limit(10).all()

    # Gamification: total savings (only products with real prices)
    total_savings = sum(
        p['diff'] for p in dashboard_data if p['trend'] == 'down' and p['diff']
    )

    return render_template('dashboard.html',
                           products=dashboard_data,
                           unread_count=unread_count,
                           recent_notifs=recent_notifs,
                           total_savings=total_savings)


@bp.route('/add', methods=['POST'])
@login_required
def add_product():
    """Add a new product URL to the user's tracking list."""
    from app.scraper.product_scraper import ProductScraper
    from app.utils.url_cleaner import clean_url

    raw_url = request.form.get('url', '').strip()
    if not raw_url:
        flash("Please provide a valid URL.", "danger")
        return redirect(url_for('main.index'))

    # Clean / canonicalize the URL before storing
    url = clean_url(raw_url)

    existing = Product.query.filter_by(url=url).first()
    if existing:
        if existing in current_user.tracked_products:
            flash("Already in your tracking list.", "warning")
        else:
            current_user.tracked_products.append(existing)
            db.session.commit()
            flash("Added existing product to your list.", "success")
        return redirect(url_for('main.index'))

    scraper = ProductScraper(url)
    details = scraper.get_product_details()

    name  = details.get('name')      if details else None
    price = details.get('price')     if details else None
    img   = details.get('image_url') if details else None

    new_product = Product(url=url, product_name=name, last_price=price, image_url=img)
    db.session.add(new_product)
    current_user.tracked_products.append(new_product)
    db.session.commit()

    if price is not None:
        db.session.add(PriceHistory(product_id=new_product.id, price=price))
        db.session.add(Notification(
            user_id=current_user.id,
            product_id=new_product.id,
            message=f"Now tracking \"{name or 'new product'}\" at ₹{price:,.0f}",
            type='info'
        ))
        db.session.commit()
        flash(f"Tracking started: {name}", "success")
    else:
        db.session.add(Notification(
            user_id=current_user.id,
            product_id=new_product.id,
            message=f"Added product but price fetch failed. Will retry.",
            type='error'
        ))
        db.session.commit()
        flash("Product added — price fetch failed. Scheduler will retry.", "info")

    return redirect(url_for('main.index'))


@bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Remove a product from the current user's tracking list."""
    product = Product.query.get_or_404(product_id)
    if product in current_user.tracked_products:
        current_user.tracked_products.remove(product)
        db.session.commit()
    flash('Removed from your tracking list.', 'success')
    return redirect(url_for('main.index'))


@bp.route('/force_check', methods=['POST'])
@login_required
def force_check():
    """Manually run a price check right now."""
    import app.scheduler.tasks as scheduler_tasks
    try:
        scheduler_tasks.check_prices()
        flash('All prices refreshed!', 'success')
    except Exception as e:
        logger.error(f"Force check error: {e}")
        flash('Error refreshing prices.', 'danger')
    return redirect(url_for('main.index'))


# ──── Notifications ────────────────────────────────────────────────────────
@bp.route('/notifications/mark_read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark all notifications as read."""
    current_user.notifications.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'ok'})


# ──── REST API ─────────────────────────────────────────────────────────────
@bp.route('/api/products')
@login_required
def api_products():
    """REST — list all tracked products for the current user."""
    return jsonify([p.to_dict() for p in current_user.tracked_products])


@bp.route('/api/prices/<int:product_id>')
@login_required
def api_prices(product_id):
    """REST — price history for a given product."""
    history = PriceHistory.query.filter_by(product_id=product_id)\
                                .order_by(PriceHistory.checked_at.asc()).all()
    return jsonify([h.to_dict() for h in history])


@bp.route('/api/alerts')
@login_required
def api_alerts():
    """REST — unread notifications for the current user."""
    notifs = current_user.notifications.order_by(Notification.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'type': n.type,
        'severity': n.severity,
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat()
    } for n in notifs])


@bp.route('/api/predict/<int:product_id>')
@login_required
def api_predict(product_id):
    """REST — AI price prediction for a tracked product."""
    from app.services.price_predictor import predict_price_trend
    result = predict_price_trend(product_id)
    return jsonify(result)


# ──── Export ───────────────────────────────────────────────────────────────
@bp.route('/export/csv')
@login_required
def export_csv():
    """Download a CSV of the user's tracked products and latest prices."""
    import csv, io
    from flask import Response

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product', 'URL', 'Current Price', 'Lowest Ever', 'Added At'])

    for p in current_user.tracked_products:
        prices = [h.price for h in p.history]
        lowest = min(prices) if prices else p.last_price
        writer.writerow([p.product_name, p.url, p.last_price, lowest, p.created_at.strftime('%Y-%m-%d')])

    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=pricetracker_report.csv'})


# ──── Profile & Settings ────────────────────────────────────────────────────
@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    action = request.form.get('action')

    if action == 'profile':
        current_user.name = request.form.get('name', '').strip() or current_user.name
        db.session.commit()
        flash('Name updated!', 'success')

    elif action == 'prefs':
        try:
            current_user.check_interval  = int(request.form.get('check_interval', 6))
            current_user.min_drop_alert_pct = float(request.form.get('min_drop_pct', 1.0))
            db.session.commit()
            flash('Alert preferences saved!', 'success')
        except Exception:
            flash('Invalid values.', 'danger')

    elif action == 'password':
        cur = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        con = request.form.get('confirm_password', '')
        if not current_user.check_password(cur):
            flash('Current password is incorrect.', 'danger')
        elif new != con:
            flash('New passwords do not match.', 'danger')
        elif len(new) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            current_user.set_password(new)
            db.session.commit()
            flash('Password changed successfully!', 'success')

    return redirect(url_for('main.profile'))


@bp.route('/profile/delete', methods=['POST'])
@login_required
def delete_account():
    from flask_login import logout_user
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('auth.signup'))


# ──── Product Detail ───────────────────────────────────────────────────────
@bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if product not in current_user.tracked_products:
        flash('Product not found in your list.', 'danger')
        return redirect(url_for('main.index'))

    history = PriceHistory.query.filter_by(product_id=product.id)\
                                .order_by(PriceHistory.checked_at.asc()).all()
    prices  = [h.price for h in history if h.price is not None]
    labels  = [h.checked_at.strftime('%d %b %H:%M') for h in history if h.price is not None]

    curr = prices[-1] if prices else product.last_price
    prev = prices[-2] if len(prices) >= 2 else curr
    trend = 'down' if (curr and prev and curr < prev) else ('up' if (curr and prev and curr > prev) else 'flat')

    p_data = {
        'id': product.id,
        'name':          product.product_name or 'Fetching…',
        'url':           product.url,
        'image':         product.image_url,
        'current_price': curr,
        'lowest':        min(prices) if prices else None,
        'highest':       max(prices) if prices else None,
        'avg':           round(sum(prices)/len(prices), 0) if prices else None,
        'trend':         trend,
        'history_points': prices,
        'history_labels': labels,
    }

    # AI Prediction
    prediction = None
    try:
        from app.services.price_predictor import predict_price_trend
        prediction = predict_price_trend(product.id)
    except Exception:
        pass

    # Target price for this user-product pair
    from sqlalchemy import select, text
    row = db.session.execute(
        text("SELECT target_price FROM user_products WHERE user_id=:u AND product_id=:p"),
        {'u': current_user.id, 'p': product.id}
    ).fetchone()
    target_price = row[0] if row else None

    return render_template('product_detail.html',
                           p=p_data,
                           history_rows=list(reversed(history)),
                           prediction=prediction,
                           target_price=target_price)


# ──── Target Price Alert ───────────────────────────────────────────────────
@bp.route('/product/<int:product_id>/set_target', methods=['POST'])
@login_required
def set_target_price(product_id):
    product = Product.query.get_or_404(product_id)
    if product not in current_user.tracked_products:
        flash('Product not found.', 'danger')
        return redirect(url_for('main.index'))
    try:
        tp = float(request.form.get('target_price', 0))
        from sqlalchemy import text
        db.session.execute(
            text("UPDATE user_products SET target_price=:tp WHERE user_id=:u AND product_id=:p"),
            {'tp': tp, 'u': current_user.id, 'p': product_id}
        )
        db.session.commit()
        flash(f'Target price set to ₹{tp:,.0f}. You\'ll get an email when it hits that price!', 'success')
    except Exception as e:
        flash('Invalid price.', 'danger')
    return redirect(url_for('main.product_detail', product_id=product_id))

