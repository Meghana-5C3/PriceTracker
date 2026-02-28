# 🛒 PriceTracker – Smart Product Price Monitoring System

PriceTracker is a Python-based web application that helps users track product prices across websites, compare deals, and receive updates when prices drop.  
It automates scraping, storage, and notification workflows to help users save money and make better purchasing decisions.

---

## 🚀 Features

- 📊 Track product prices from multiple URLs  
- 🔔 Price drop alerts & notifications  
- 📉 Historical price tracking using SQLite database  
- 🔍 Compare product prices across stores  
- 🧾 User authentication (login/register system)  
- 📱 Responsive web dashboard with templates & static UI  
- 🧠 Modular scraper, parser, importer, and notifier architecture  

---

## 🏗️ Project Structure
price/
│
├── web_app.py # Web server entry point
├── main.py # Core execution script
├── data/
│ ├── tracker.db # SQLite database
│ └── core/
│ ├── scraper.py
│ ├── parser.py
│ ├── database.py
│ ├── importer.py
│ └── notifier.py
│
├── routers/ # Auth & route handlers
├── templates/ # HTML templates
├── static/ # CSS, images, assets
└── config.json # Configuration file


---

## ⚙️ Tech Stack

- Python
- SQLite Database
- HTML / CSS Templates
- Web Scraping Modules
- Email Notification System

---

## 💻 Running Locally

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Meghana-5C3/PriceTracker.git
cd PriceTracker
2️⃣ Create virtual environment
python -m venv venv
venv\Scripts\activate
3️⃣ Install dependencies
pip install -r requirements.txt
4️⃣ Start the app
python price/web_app.py

Open in browser:

http://127.0.0.1:8000
