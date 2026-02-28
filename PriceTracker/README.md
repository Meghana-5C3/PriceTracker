# PriceTracker Pro (Flask Version)

A lightweight, production-ready Python web application that periodically scrapes e-commerce product pages (Amazon, Flipkart), tracks price fluctuations, stories historical data, and sends automatic SMTP email alerts when a price drop occurs.

## 🏗️ Architecture

This project strictly adheres to modular, beginner-friendly separation of concerns:
```
PriceTracker/
├── app.py                  # Main Flask entrypoint & Factory runner
├── config.py               # Centralized configuration (.env loader)
├── requirements.txt        # Python dependencies
├── README.md               # Setup instructions
└── app/                    # Primary application package
    ├── __init__.py         # Flask Application Factory
    ├── routes/             # Web API and View Endpoints (views.py)
    ├── models/             # SQLite Data Schema (models.py)
    ├── scraper/            # OOP Web Scraping Tool (product_scraper.py)
    ├── scheduler/          # APScheduler background tasks (tasks.py)
    ├── email/              # SMTP HTML Notifications (email_service.py)
    ├── templates/          # Jinja2 Layouts (base.html, dashboard.html)
    └── static/             # Assets (style.css)
```

## ✨ Features
1. **Add by URL**: Automatically uses a robust `ProductScraper` to extract Amazon/Flipkart names, images, and prices. Handles anti-bot timeouts securely.
2. **Periodic Checks**: Runs completely automatically every 6 hours via `APScheduler` in the background. Does not require the web dashboard to be open!
3. **Drop Detection Algorithm**: `tasks.py` specifically compares historical records.
4. **Email Alerts**: Dispatches a premium HTML styled email securely if the new price is lower than the previous run.
5. **Dashboard**: Fully responsive Bootstrap 5 interface with embedded `Chart.js` tracking timelines.

## 🚀 Setup Instructions

### 1. Requirements
Ensure you have Python 3 installed. Navigate to the project root directory:
```bash
cd PriceTracker
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root `PriceTracker` folder next to `app.py`. Add the following credentials:
```env
# Optional: Keep 6 hours by default, or change for testing
CHECK_INTERVAL=6

# SMTP Gmail Configuration (Important for Alerts!)
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_16_digit_app_password
```
*(Note for Gmail: You must generate an **App Password** from your Google Account > Security settings. Standard passwords will be rejected).*

### 4. Run the Application
Start the Flask server:
```bash
python app.py
```
* The SQLite Database (`pricetracker.db`) will auto-generate on first boot.
* Access the beautiful dashboard at: `http://127.0.0.1:5000/`

## 🧠 How Price Drop Detection Works (For Students)
1. **Background Job**: The file `app/scheduler/tasks.py` runs a `check_prices()` function on a continuous loop on another thread.
2. **Current vs Old**: It retrieves every product from the SQLite DB. It finds the `product.last_price` cached from the last run.
3. **Scrape**: It instantiates `ProductScraper(url)` to get the live price right now.
4. **Compare**: If `new_price < old_price`, a genuine drop occurred! It immediately calls `EmailService.send_price_drop_alert`.
5. **Update**: It saves `new_price` into the `PriceHistory` timeline table, and updates `product.last_price = new_price` so the next run has a fresh baseline.
