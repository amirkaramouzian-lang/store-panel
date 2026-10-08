from datetime import date, datetime, timedelta
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from database import engine, get_db, SessionLocal
from routers import orders, inventory, attendance, suggestions

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="پنل مدیریت فروشگاه")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def render_template(name, context):
    return templates.TemplateResponse(request=context["request"], name=name, context=context)

app.include_router(orders.router)
app.include_router(inventory.router)
app.include_router(attendance.router)
app.include_router(suggestions.router)


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    total_orders = db.query(func.count(models.Order.id)).scalar() or 0
    total_products = db.query(func.count(models.Product.id)).scalar() or 0
    low_stock = db.query(models.Product).filter(
        models.Product.quantity <= models.Product.low_stock_threshold
    ).count()
    today = date.today()
    present_today = db.query(models.Attendance).filter(
        models.Attendance.date == today,
        models.Attendance.status != "absent",
    ).count()
    recent_orders = (
        db.query(models.Order, models.Customer.name)
        .join(models.Customer, models.Order.customer_id == models.Customer.id)
        .order_by(models.Order.created_at.desc())
        .limit(6)
        .all()
    )
    return render_template("dashboard.html", {
        "request": request,
        "total_orders": total_orders,
        "total_products": total_products,
        "low_stock": low_stock,
        "present_today": present_today,
        "recent_orders": recent_orders,
        "page_title": "داشبورد",
    })


@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        if db.query(models.Customer).count() > 0:
            return
        customers = [
            models.Customer(name="علی رضایی", phone="09121110001"),
            models.Customer(name="مریم احمدی", phone="09121110002"),
            models.Customer(name="حسین کریمی", phone="09121110003"),
            models.Customer(name="سارا موسوی", phone="09121110004"),
            models.Customer(name="رضا شاهی", phone="09121110005"),
        ]
        db.add_all(customers)

        products = [
            models.Product(name="موبایل سامسونگ A54", category="موبایل", quantity=12, unit_price=18900000, low_stock_threshold=5),
            models.Product(name="هدفون بی‌سیم", category="لوازم جانبی", quantity=30, unit_price=850000, low_stock_threshold=10),
            models.Product(name="پاوربانک ۲۰۰۰۰", category="لوازم جانبی", quantity=8, unit_price=1250000, low_stock_threshold=10),
            models.Product(name="کیبورد مکانیکال", category="کامپیوتر", quantity=3, unit_price=2100000, low_stock_threshold=5),
            models.Product(name="ماوس گیمینگ", category="کامپیوتر", quantity=18, unit_price=980000, low_stock_threshold=6),
            models.Product(name="شارژر فست شارژ", category="لوازم جانبی", quantity=25, unit_price=450000, low_stock_threshold=8),
            models.Product(name="کابل USB-C", category="لوازم جانبی", quantity=2, unit_price=180000, low_stock_threshold=5),
            models.Product(name="اسپیکر بلوتوثی", category="صوتی", quantity=9, unit_price=3200000, low_stock_threshold=4),
        ]
        db.add_all(products)

        staff = [
            models.Staff(name="امیر تهرانی", role="فروشنده", phone="09122220001"),
            models.Staff(name="نگار صالحی", role="انباردار", phone="09122220002"),
        ]
        db.add_all(staff)
        db.commit()

        statuses = ["delivered", "pending", "processing", "delivered", "cancelled", "pending", "delivered"]
        for i in range(7):
            order = models.Order(
                customer_id=customers[i % len(customers)].id,
                status=statuses[i],
                total_price=0,
                created_at=datetime.now() - timedelta(days=i),
                notes=None if i % 3 else "پیگیری ارسال سریع‌تر",
            )
            p1 = products[i % len(products)]
            p2 = products[(i + 3) % len(products)]
            for p, q in [(p1, (i % 2) + 1), (p2, (i % 3) + 1)]:
                order.items.append(models.OrderItem(product_id=p.id, quantity=q, unit_price=p.unit_price))
                order.total_price += q * p.unit_price
            db.add(order)
        db.commit()
    finally:
        db.close()
