"""
Email Service — sends all alert types via Gmail SMTP.
Credentials loaded from Flask config (EMAIL_USER / EMAIL_PASSWORD).
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app

logger = logging.getLogger(__name__)


# ── Shared SMTP helper ────────────────────────────────────────────────────────
def _send(to_email: str, subject: str, html_body: str) -> bool:
    """Low-level send via Gmail SMTP. Returns True on success."""
    sender = current_app.config.get('EMAIL_USER', '').strip()
    password = current_app.config.get('EMAIL_PASSWORD', '').strip()

    if not sender or not password:
        logger.warning("EMAIL_USER / EMAIL_PASSWORD not set — skipping email.")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"PriceTracker Pro <{sender}>"
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        logger.info(f"📧 Email sent to {to_email} — {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to_email}: {e}")
        return False


# ── Email Templates ───────────────────────────────────────────────────────────
class EmailService:

    @staticmethod
    def send_price_drop_alert(product_name: str, old_price: float,
                               new_price: float, url: str,
                               recipient_email: str = None) -> bool:
        """
        Send a price drop alert to a specific user's email.
        Falls back to EMAIL_USER (owner) if no recipient given.
        """
        diff     = old_price - new_price
        diff_pct = round(diff / old_price * 100, 1)

        emoji = "🚀" if diff_pct >= 30 else ("🔥" if diff_pct >= 15 else "📉")
        subject = f"{emoji} Price Dropped! {product_name[:40]} — ₹{new_price:,.0f}"

        to = recipient_email or current_app.config.get('EMAIL_USER', '')
        if not to:
            return False

        html = f"""
        <html><body style="font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f8;margin:0;padding:20px;">
          <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;
                      box-shadow:0 4px 15px rgba(0,0,0,.1);">

            <!-- Header -->
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;text-align:center;">
              <h1 style="color:#fff;margin:0;font-size:24px;">📉 Price Drop Alert!</h1>
              <p style="color:rgba(255,255,255,.85);margin:8px 0 0;">PriceTracker Pro</p>
            </div>

            <!-- Body -->
            <div style="padding:30px;">
              <p style="font-size:16px;">Great news! An item you're tracking just dropped in price.</p>

              <div style="background:#f8f9fa;padding:20px;border-radius:8px;border-left:4px solid #22c55e;margin:20px 0;">
                <h2 style="margin:0 0 12px;font-size:18px;">{product_name}</h2>
                <table style="width:100%;border-collapse:collapse;">
                  <tr>
                    <td style="padding:6px 0;color:#6c757d;">Old Price</td>
                    <td style="text-align:right;"><del style="color:#dc3545;">₹{old_price:,.2f}</del></td>
                  </tr>
                  <tr>
                    <td style="padding:6px 0;color:#6c757d;">New Price</td>
                    <td style="text-align:right;font-size:22px;font-weight:bold;color:#22c55e;">₹{new_price:,.2f}</td>
                  </tr>
                  <tr style="border-top:1px solid #dee2e6;">
                    <td style="padding:10px 0;font-weight:bold;">You Save</td>
                    <td style="text-align:right;font-weight:bold;color:#22c55e;">₹{diff:,.2f} ({diff_pct}% off)</td>
                  </tr>
                </table>
              </div>

              <div style="text-align:center;margin:30px 0;">
                <a href="{url}" style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;
                   padding:14px 35px;text-decoration:none;border-radius:8px;font-weight:bold;
                   font-size:16px;display:inline-block;">🛒 Buy Now</a>
              </div>
            </div>

            <!-- Footer -->
            <div style="background:#f8f9fa;padding:15px;text-align:center;font-size:12px;color:#6c757d;">
              PriceTracker Pro — Tracking prices, saving money.<br>
              You received this because you're tracking this product.
            </div>
          </div>
        </body></html>
        """
        return _send(to, subject, html)

    @staticmethod
    def send_welcome_email(email: str, name: str) -> bool:
        """Send welcome email after signup."""
        subject = "🎉 Welcome to PriceTracker Pro!"
        html = f"""
        <html><body style="font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f8;padding:20px;">
          <div style="max-width:580px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;
                      box-shadow:0 4px 15px rgba(0,0,0,.08);">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;text-align:center;">
              <h1 style="color:#fff;margin:0;">Welcome, {name or 'Saver'}! 🎉</h1>
            </div>
            <div style="padding:30px;">
              <p style="font-size:16px;">You've just joined <strong>PriceTracker Pro</strong> — your personal deal hunter.</p>
              <ul style="line-height:2.2;padding-left:20px;">
                <li>📦 Paste Amazon or Flipkart URLs to track products</li>
                <li>📉 Get email alerts when prices drop</li>
                <li>📊 View full price history charts</li>
                <li>🤖 AI-powered buy/wait recommendations</li>
              </ul>
              <div style="text-align:center;margin-top:25px;">
                <a href="http://127.0.0.1:5000" style="background:linear-gradient(135deg,#667eea,#764ba2);
                   color:#fff;padding:12px 30px;text-decoration:none;border-radius:8px;font-weight:bold;">
                   Open My Dashboard →</a>
              </div>
            </div>
            <div style="background:#f8f9fa;padding:12px;text-align:center;font-size:12px;color:#999;">
              PriceTracker Pro — Built with ❤️
            </div>
          </div>
        </body></html>
        """
        return _send(email, subject, html)

    @staticmethod
    def send_daily_summary(email: str, name: str, products_data: list) -> bool:
        """Send daily price summary email."""
        subject = "📊 Your Daily Price Summary — PriceTracker Pro"
        rows = ""
        for p in products_data:
            trend_icon = "📉" if p.get("trend") == "down" else ("📈" if p.get("trend") == "up" else "➖")
            price = f"₹{p['current_price']:,.0f}" if p.get('current_price') else "Pending"
            rows += f"""
            <tr>
              <td style="padding:10px;border-bottom:1px solid #f0f0f0;">{trend_icon} {p['name'][:50]}</td>
              <td style="padding:10px;border-bottom:1px solid #f0f0f0;text-align:right;">{price}</td>
            </tr>"""

        html = f"""
        <html><body style="font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f8;padding:20px;">
          <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;
                      box-shadow:0 4px 15px rgba(0,0,0,.08);">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:25px;text-align:center;">
              <h1 style="color:#fff;margin:0;font-size:20px;">Daily Price Summary</h1>
              <p style="color:rgba(255,255,255,.8);margin:5px 0 0;">Hey {name or 'there'}, here's today's update</p>
            </div>
            <div style="padding:20px;">
              <table style="width:100%;border-collapse:collapse;">
                <thead>
                  <tr style="background:#f8f9fa;">
                    <th style="padding:10px;text-align:left;">Product</th>
                    <th style="padding:10px;text-align:right;">Current Price</th>
                  </tr>
                </thead>
                <tbody>{rows}</tbody>
              </table>
              <div style="text-align:center;margin-top:20px;">
                <a href="http://127.0.0.1:5000" style="background:linear-gradient(135deg,#667eea,#764ba2);
                   color:#fff;padding:12px 25px;text-decoration:none;border-radius:8px;font-weight:bold;">
                   View Full Dashboard</a>
              </div>
            </div>
          </div>
        </body></html>
        """
        return _send(email, subject, html)

    @staticmethod
    def send_test_email(recipient: str) -> bool:
        """Send a test email to verify SMTP config."""
        subject = "✅ PriceTracker Pro — SMTP Test Successful"
        html = """
        <html><body style="font-family:Arial,sans-serif;text-align:center;padding:40px;">
          <h2 style="color:#22c55e;">✅ Email is working!</h2>
          <p>Your SMTP configuration is correct. Price drop alerts will be delivered successfully.</p>
        </body></html>
        """
        return _send(recipient, subject, html)
