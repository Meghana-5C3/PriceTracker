import os
import sys
from fastapi import FastAPI, Request, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio
import logging
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.core.database import init_db, get_session, Product, PriceHistory, User, RewardTransaction
from data.core.scraper import fetch_product_data, scrape_all_products
from data.core.notifier import send_price_drop_email
from data.core.importer import import_urls_from_file
from starlette.middleware.sessions import SessionMiddleware
import routers.auth as auth

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="BuyHatke Clone")

# Session Middleware
app.add_middleware(SessionMiddleware, secret_key="buyhatke-secret-key")

# Mount static and templates
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register Routers
app.include_router(auth.router)

templates = Jinja2Templates(directory="templates")

def seed_database():
    """Populates the database with some example URLs for demonstration purposes."""
    db = get_session()
    
    # Check if data already exists to avoid duplicates
    if db.query(Product).count() > 0:
        db.close()
        return

    # Seed Products
    adidas = Product(
        url="https://www.adidas.co.in/pureboost-23-shoes/IF2375.html",
        domain="adidas.co.in",
        name="Pureboost 23 Shoes",
        image_url="https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/7cd6bc559ed141c28c6eaf4b00a6e60b_9366/Pureboost_23_Shoes_White_IF2375_01_standard.jpg",
        category="fashion"
    )
    amazon = Product(
        url="https://www.amazon.in/BSB-HOME-Bedsheet-Breathable-Wrinkle/dp/B0F99WNFW1",
        domain="amazon.in",
        name="Double Bed Bedsheet Set",
        image_url="https://m.media-amazon.com/images/I/81z3W8kXQyL._SL1500_.jpg",
        category="grocery"
    )
    iphone = Product(
        url="https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4",
        domain="flipkart.com",
        name="iPhone 15 (Black, 128 GB)",
        image_url="https://rukminim2.flixcart.com/image/832/832/xif0q/mobile/h/d/9/-original-imagtc2qzgnnzuwp.jpeg",
        category="electronics"
    )
    
    db.add_all([adidas, amazon, iphone])
    db.commit()
    
    # Add initial price history
    db.add_all([
        PriceHistory(product_id=adidas.id, price=12999.0),
        PriceHistory(product_id=adidas.id, price=6499.5),
        PriceHistory(product_id=amazon.id, price=229.0),
        PriceHistory(product_id=iphone.id, price=54900.0)
    ])
    
    db.commit()
    db.close()

# Reuse price tracking logic from main.py
async def track_prices_task():
    """Background task for price tracking."""
    logger.info("Starting background price tracking...")
    db = get_session()
    try:
        products = db.query(Product).all()
        if not products:
            logger.warning("No products to track.")
            return

        results = await scrape_all_products(products)

        for result in results:
            product_id = result["product_id"]
            data = result["data"]
            current_price = data["price"]
            name = data["name"]

            if current_price is None:
                continue

            product = db.query(Product).filter(Product.id == product_id).first()
            if not product.name and name:
                product.name = name
            
            last_history = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).order_by(PriceHistory.timestamp.desc()).first()
            new_history = PriceHistory(product_id=product_id, price=current_price)
            db.add(new_history)
            
            old_price = last_history.price if last_history else None
            
            # Check alerts for all users tracking this product
            from data.core.database import user_product
            trackers = db.execute(user_product.select().where(user_product.c.product_id == product_id)).fetchall()
            
            for tracker in trackers:
                target = tracker.target_price
                user_id = tracker.user_id
                
                if old_price is not None:
                    drop_pct = ((old_price - current_price) / old_price) * 100 if current_price < old_price else 0
                    rise_pct = ((current_price - old_price) / old_price) * 100 if current_price > old_price else 0
                    
                    user = db.query(User).filter(User.id == user_id).first()
                    receiver_email = user.email if user else "guest@example.com"
                    
                    if target and current_price <= target:
                        logger.info(f"🎯 TARGET HIT: {product.name} (₹{current_price}) for user {user_id}")
                        send_price_drop_email(product.name, product.url, old_price, current_price, receiver_email)
                    elif drop_pct >= 5: # Significant drop alert (>5%)
                        logger.info(f"🔥 PRICE DROP: {product.name} fell by {drop_pct:.1f}% for user {user_id}")
                        send_price_drop_email(product.name, product.url, old_price, current_price, receiver_email)
                    elif rise_pct >= 5: # Significant rise alert (>5%)
                        logger.info(f"📈 PRICE RISE: {product.name} increased by {rise_pct:.1f}% for user {user_id}")
                        send_price_drop_email(product.name, product.url, old_price, current_price, receiver_email, is_drop=False)

        db.commit()
    except Exception as e:
        logger.error(f"Error in tracking: {e}")
        db.rollback()
    finally:
        db.close()
    logger.info("Background price tracking completed.")

# Scheduler
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    init_db()
    seed_database()
    
    # Bulk Import from urls.txt
    urls_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'urls.txt')
    if os.path.exists(urls_file):
        logger.info("Importing URLs from urls.txt...")
        import_urls_from_file(urls_file)
        
    # Run once on startup
    asyncio.create_task(track_prices_task())
    # Schedule every 6 hours
    scheduler.add_job(track_prices_task, 'interval', hours=6)
    scheduler.start()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, tab: str = "all", platform: str = None, category: str = None):
    db = get_session()
    user_id = request.session.get("user_id")
    
    # Base query
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        products_db = user.tracked_products if user else []
    else:
        # For guests, show all public products or a selection
        products_db = db.query(Product).limit(10).all()
        
    product_list = []
    for p_db in products_db:
        history_db = db.query(PriceHistory).filter(PriceHistory.product_id == p_db.id).order_by(PriceHistory.timestamp.asc()).all()
        latest = history_db[-1].price if history_db else None
        
        # Determine previous price
        previous = None
        if len(history_db) > 1:
            previous = history_db[-2].price
        elif latest:
            previous = latest * 1.1 # Default 10% drop for demo
            
        # Metrics calculation
        discount_pct = 0
        if latest and previous and previous > latest:
            discount_pct = int(((previous - latest) / previous) * 100)

        # Get user-specific tracking info if logged in
        target_price = None
        is_paused = False
        if user_id:
            from data.core.database import user_product
            up = db.execute(user_product.select().where(
                (user_product.c.user_id == user_id) & (user_product.c.product_id == p_db.id)
            )).first()
            if up:
                target_price = up.target_price
                is_paused = bool(up.is_paused)

        last_checked = history_db[-1].timestamp if history_db else p_db.created_at # Mocked if no history
        if not last_checked: last_checked = datetime.utcnow() # Fallback

        p_data = {
            "id": p_db.id,
            "category": p_db.category or "Others",
            "name": p_db.name or "Product Fetching...",
            "url": p_db.url,
            "domain": p_db.domain or "unknown",
            "current_price": latest,
            "previous_price": previous,
            "target_price": target_price,
            "is_paused": is_paused,
            "discount_pct": discount_pct,
            "deal_score": max(70, min(100, 70 + discount_pct)),
            "lowest_ever": True,
            "image_url": p_db.image_url or "https://via.placeholder.com/150",
            "last_checked": last_checked.strftime("%Y-%m-%d %H:%M"),
            "history": [{"price": h.price, "date": h.timestamp.strftime("%m/%d %H:%M")} for h in history_db]
        }
        
        if history_db and latest:
            p_data["lowest_ever"] = latest <= min([h.price for h in history_db])

        product_list.append(p_data)

    # Filtering Logic based on active tab
    if tab == "hot-deals":
        product_list = [p for p in product_list if p["discount_pct"] > 10]
        product_list.sort(key=lambda x: x["discount_pct"], reverse=True)
    elif tab == "price-tracker":
        # Specific view for trackers
        pass
    lens_data = {}
    rewards_data = {}

    if tab == "spend-lens":
        total_spent = sum([p['current_price'] or 0 for p in product_list])
        total_saved = sum([(p['previous_price'] or 0) - (p['current_price'] or 0) for p in product_list if p['previous_price'] and p['current_price'] and p['previous_price'] > p['current_price']])
        
        from collections import defaultdict
        cat_counts = defaultdict(float)
        for p in product_list:
            cat_counts[p['category'].title()] += (p['current_price'] or 0)
            
        lens_data = {
            "total_spent": int(total_spent),
            "total_saved": int(total_saved),
            "categories": list(cat_counts.keys()),
            "category_amounts": list(cat_counts.values())
        }
        
    elif tab == "rewards":
        # Simulate dynamic rewards based on tracked items
        base_points = 500
        tracked_bonus = len(product_list) * 250 # 250 points per tracked product
        rewards_data = {
            "simulated_points": base_points + tracked_bonus,
            "simulated_pending": len(product_list) * 50
        }

        
    if platform:
        product_list = [p for p in product_list if platform.lower() in p["domain"].lower()]
    if category:
        product_list = [p for p in product_list if category.lower() in (p_db.category or "").lower()]

    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

    db.close()
    
    # Select template based on tab
    template_name = "dashboard.html"
    if tab == "spend-lens":
        template_name = "tabs/spend_lens.html"
    elif tab == "rewards":
        template_name = "tabs/rewards.html"
    elif tab == "price-compare":
        template_name = "tabs/compare.html"
    elif tab == "grocery":
        template_name = "tabs/grocery.html"
    elif tab == "price-tracker":
        template_name = "tabs/tracker.html"

    return templates.TemplateResponse(template_name, {
        "request": request, 
        "products": product_list,
        "products_to_json": json.dumps(product_list),
        "active_tab": tab,
        "active_platform": platform,
        "active_category": category,
        "user": user,
        "lens_data": lens_data,
        "rewards_data": rewards_data
    })

@app.get("/grocery", response_class=HTMLResponse)
async def grocery_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "products": [], "active_tab": "grocery"})

@app.get("/ride-compare", response_class=HTMLResponse)
async def ride_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "products": [], "active_tab": "ride"})

@app.post("/api/scrape-now")
async def scrape_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(track_prices_task)

@app.post("/api/toggle-pause")
async def toggle_pause(request: Request, data: dict):
    user_id = request.session.get("user_id")
    if not user_id: return JSONResponse({"error": "Login required"}, 401)
    
    product_id = data.get("id")
    db = get_session()
    try:
        from data.core.database import user_product
        up = db.execute(user_product.select().where(
            (user_product.c.user_id == user_id) & (user_product.c.product_id == product_id)
        )).first()
        
        if up:
            new_paused = 0 if up.is_paused else 1
            db.execute(
                user_product.update().where(
                    (user_product.c.user_id == user_id) & (user_product.c.product_id == product_id)
                ).values(is_paused=new_paused)
            )
            db.commit()
            return {"status": "success", "is_paused": bool(new_paused)}
        return JSONResponse({"error": "Tracker not found"}, 404)
    except Exception as e:
        db.rollback()
        return JSONResponse({"error": str(e)}, 500)
    finally:
        db.close()

from urllib.parse import urlparse

def get_domain(url: str) -> str:
    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/add-product")
async def add_product(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id: return JSONResponse({"error": "Login required"}, 401)
    
    data = await request.json()
    url = data.get("url")
    frequency = data.get("frequency", "daily")
    if not url: return JSONResponse({"error": "URL missing"}, 400)
    
    # Check if already in DB
    product = db.query(Product).filter(Product.url == url).first()
    if not product:
        domain = get_domain(url)
        try:
            p_data = await fetch_product_data(url)
            if p_data and p_data.get("name"):
                product = Product(url=url, domain=domain, name=p_data.get("name"))
                db.add(product)
                db.flush()
                if p_data.get("price"):
                    from data.core.database import PriceHistory
                    new_history = PriceHistory(product_id=product.id, price=p_data["price"])
                    db.add(new_history)
        except Exception as e:
            logger.error(f"Scrape error: {e}")
            return JSONResponse({"error": "Website not currently supported"}, 400)
            
    if not product:
        return JSONResponse({"error": "Failed to fetch product data"}, 400)
        
    user = db.query(User).get(user_id)
    if user not in product.users:
        product.users.append(user)
        db.commit()
        
        # Set frequency and initial target
        from data.core.database import user_product
        target_price = data.get("target_price")
        update_stmt = user_product.update().where(
            (user_product.c.user_id == user_id) & (user_product.c.product_id == product.id)
        ).values(frequency=frequency)
        if target_price:
            try:
                update_stmt = update_stmt.values(target_price=float(target_price))
            except: pass
        db.execute(update_stmt)
        db.commit()
        
        background_tasks.add_task(track_prices_task)
        return {"status": "success", "message": "Product added to tracking"}
    
    return JSONResponse({"error": "Already tracking this product"}, 400)

@app.post("/api/delete-product/{product_id}")
async def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id: return JSONResponse({"error": "Login required"}, 401)
    
    product = db.query(Product).get(product_id)
    user = db.query(User).get(user_id)
    if product and user in product.users:
        product.users.remove(user)
        db.commit()
        return {"status": "success"}
    return JSONResponse({"error": "Product not found"}, 404)

@app.post("/api/test-email/{product_id}")
async def test_email(product_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id: return JSONResponse({"error": "Login required"}, 401)
    
    product = db.query(Product).get(product_id)
    user = db.query(User).get(user_id)
    if product and user in product.users:
        from data.core.notifier import send_price_drop_email
        
        # Get latest price to simulate a realistic drop
        from data.core.database import PriceHistory
        last_history = db.query(PriceHistory).filter(PriceHistory.product_id == product.id).order_by(PriceHistory.timestamp.desc()).first()
        current = last_history.price if last_history else 1000.0
        old_price = current * 1.2 # 20% more
        
        receiver_email = user.email if user else "guest@example.com"
        # Since it's a test, we try to send the email immediately
        send_price_drop_email(product.name, product.url, old_price, current, receiver_email)
        return {"status": "success", "message": f"Test price drop email for {product.name} triggered."}
    return JSONResponse({"error": "Product not found"}, 404)

@app.post("/api/mock-checkout")
async def mock_checkout(request: Request):
    if not request.session.get("user_id"): return JSONResponse({"error": "Login required"}, 401)
    return {"status": "success"}

import random

@app.get("/api/compare")
async def get_compare_results(query: str):
    base = random.randint(500, 20000)
    stores = [
        {"name": "Amazon India", "logo": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg", "delivery": "₹40", "price": base * random.uniform(0.9, 1.2)},
        {"name": "Flipkart", "logo": "https://upload.wikimedia.org/wikipedia/commons/2/24/Flipkart_logo.png", "delivery": "Free", "price": base * random.uniform(0.9, 1.2)},
        {"name": "Croma", "logo": "https://upload.wikimedia.org/wikipedia/commons/f/fe/Croma_Logo.png", "delivery": "Free", "price": base * random.uniform(0.9, 1.2)}
    ]
    stores.sort(key=lambda x: x["price"])
    stores[0]["is_lowest"] = True
    
    formatted = [{"name": s["name"], "logo": s["logo"], "delivery": s["delivery"], "price": int(s["price"]), "is_lowest": s.get("is_lowest", False)} for s in stores]
    return {"query": query.title(), "results": formatted}

@app.post("/api/cart/add")
async def add_to_cart(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    name = data.get("name")
    user_id = request.session.get("user_id")
    
    if not name: return JSONResponse({"error": "Name required"}, 400)
    base_price = random.randint(20, 500)
    
    from data.core.database import CartItem
    item = CartItem(user_id=user_id, name=name, base_price=base_price, quantity=1)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "success", "item": {"id": item.id, "name": item.name, "base_price": item.base_price, "qty": item.quantity}}

@app.post("/api/mock-buy-reward")
async def mock_buy_reward(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id: return JSONResponse({"error": "Login required"}, 401)
    
    data = await request.json()
    value = data.get("value", 0)
    brand = data.get("brand", "Gift Card")
    
    user = db.query(User).get(user_id)
    if user.redeemable_points >= value:
        user.redeemable_points -= value
        tx = RewardTransaction(user_id=user_id, points=-value, description=f"Redeemed {brand} Voucher")
        db.add(tx)
        db.commit()
        return {"status": "success"}
    return JSONResponse({"error": "Not enough points"}, 400)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
