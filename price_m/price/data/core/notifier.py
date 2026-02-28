import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configured for demonstration purposes
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SENDER_EMAIL = os.environ.get("SMTP_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.environ.get("SMTP_PASSWORD", "your_app_password")

def send_price_drop_email(product_name: str, url: str, old_price: float, new_price: float, receiver_email: str, is_drop: bool = True):
    """Sends a premium styled email notification for a price change (drop or rise)."""
    msg = MIMEMultipart('alternative')
    
    emoji = "🔥" if is_drop else "⚠️"
    status_text = "Price Drop Detected!" if is_drop else "Price Increase Alert"
    subject = f"📉 Price Drop Alert: {product_name} is Now Cheaper!" if is_drop else f"📈 Price Rise Alert: {product_name} increased in price"
    sub_text = "We found a lower price for an item you're tracking." if is_drop else "An item you are tracking has increased in price."
    hero_bg = "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)" if is_drop else "linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)"
    
    msg['Subject'] = subject
    msg['From'] = f"BuyHatke Alerts <{SENDER_EMAIL}>"
    msg['To'] = receiver_email

    diff_amount = abs(old_price - new_price)
    diff_percentage = (diff_amount / old_price) * 100 if old_price else 0
    
    color_new_price = "#10b981" if is_drop else "#ef4444"
    save_pill_bg = "#ecfdf5" if is_drop else "#fef2f2"
    save_pill_color = "#059669" if is_drop else "#b91c1c"
    save_pill_text = f"You Save ₹{diff_amount:,.2f} ({diff_percentage:.1f}%)" if is_drop else f"Price rose by ₹{diff_amount:,.2f} ({diff_percentage:.1f}%)"
    
    html = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; line-height: 1.6; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 20px auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
          <div style="background: {hero_bg}; padding: 30px; text-align: center; color: white;">
            <h1 style="margin: 0; font-size: 24px;">{status_text} {emoji}</h1>
            <p style="margin: 10px 0 0; opacity: 0.9;">{sub_text}</p>
          </div>
          <div style="padding: 30px; background: white;">
            <h2 style="font-size: 18px; margin-top: 0; color: #0f172a;">{product_name}</h2>
            <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; padding: 20px; border-radius: 12px; margin: 20px 0;">
              <div style="text-align: center; flex: 1;">
                <p style="margin: 0; font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 700;">Old Price</p>
                <p style="margin: 5px 0 0; font-size: 20px; color: #94a3b8; text-decoration: line-through;">₹{old_price:,.2f}</p>
              </div>
              <div style="text-align: center; flex: 1; border-left: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 12px; color: #4f46e5; text-transform: uppercase; font-weight: 700;">New Price</p>
                <p style="margin: 5px 0 0; font-size: 24px; color: {color_new_price}; font-weight: 800;">₹{new_price:,.2f}</p>
              </div>
            </div>
            <div style="text-align: center; margin-bottom: 25px;">
              <span style="background: {save_pill_bg}; color: {save_pill_color}; padding: 6px 12px; border-radius: 20px; font-weight: 700; font-size: 14px;">
                {save_pill_text}
              </span>
            </div>
            <a href="{url}" style="display: block; background: #4f46e5; color: white; text-align: center; padding: 15px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 16px;">
              View Product
            </a>
          </div>
          <div style="background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b;">
            <p style="margin: 0;">You received this because you are tracking this product on BuyHatke Clone.</p>
            <p style="margin: 10px 0 0;">&copy; 2026 BuyHatke Clone. All rights reserved.</p>
          </div>
        </div>
      </body>
    </html>
    """
    
    part = MIMEText(html, 'html')
    msg.attach(part)
    
    try:
        # Avoid connecting if not configured
        if SENDER_EMAIL == "your_email@gmail.com" or SENDER_PASSWORD == "your_app_password":
            logger.info("--------------------------------------------------")
            logger.info(f"📧 SIMULATED EMAIL SENT TO: {receiver_email}")
            logger.info(f"Subject: {msg['Subject']}")
            logger.info(f"Product: {product_name}")
            logger.info(f"Savings: ₹{drop_amount:.2f} ({drop_percentage:.1f}%)")
            logger.info("--------------------------------------------------")
            return
            
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            logger.info(f"Price drop email sent for {product_name}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
