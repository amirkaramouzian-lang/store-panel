import os
from pathlib import Path
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Request, Depends, Form, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./store.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"): ]
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    orders = relationship("Order", back_populates="customer")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    category = Column(String(80), nullable=True)
    quantity = Column(Integer, default=0, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    low_stock_threshold = Column(Integer, default=5, nullable=False)

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    total_price = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    notes = Column(String(500), nullable=True)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    role = Column(String(80), nullable=True)
    phone = Column(String(30), nullable=True)

    attendance = relationship("Attendance", back_populates="staff")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    check_in = Column(String(8), nullable=True)
    check_out = Column(String(8), nullable=True)
    status = Column(String(10), default="present", nullable=False)

    staff = relationship("Staff", back_populates="attendance")

# Resolve asset directories relative to this file so execution does not depend on cwd.
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def render_template(name, context):
    return templates.TemplateResponse(request=context["request"], name=name, context=context)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="پنل مدیریت فروشگاه")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")




@app.get("/")
def root():
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    low_stock = db.query(Product).filter(
        Product.quantity <= Product.low_stock_threshold
    ).count()
    today = date.today()
    present_today = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status != "absent",
    ).count()
    recent_orders = (
        db.query(Order, Customer.name)
        .join(Customer, Order.customer_id == Customer.id)
        .order_by(Order.created_at.desc())
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
        if db.query(Customer).count() > 0:
            return
        customers = [
            Customer(name="علی رضایی", phone="09121110001"),
            Customer(name="مریم احمدی", phone="09121110002"),
            Customer(name="حسین کریمی", phone="09121110003"),
            Customer(name="سارا موسوی", phone="09121110004"),
            Customer(name="رضا شاهی", phone="09121110005"),
        ]
        db.add_all(customers)

        products = [
            Product(name="موبایل سامسونگ A54", category="موبایل", quantity=12, unit_price=18900000, low_stock_threshold=5),
            Product(name="هدفون بی‌سیم", category="لوازم جانبی", quantity=30, unit_price=850000, low_stock_threshold=10),
            Product(name="پاوربانک ۲۰۰۰۰", category="لوازم جانبی", quantity=8, unit_price=1250000, low_stock_threshold=10),
            Product(name="کیبورد مکانیکال", category="کامپیوتر", quantity=3, unit_price=2100000, low_stock_threshold=5),
            Product(name="ماوس گیمینگ", category="کامپیوتر", quantity=18, unit_price=980000, low_stock_threshold=6),
            Product(name="شارژر فست شارژ", category="لوازم جانبی", quantity=25, unit_price=450000, low_stock_threshold=8),
            Product(name="کابل USB-C", category="لوازم جانبی", quantity=2, unit_price=180000, low_stock_threshold=5),
            Product(name="اسپیکر بلوتوثی", category="صوتی", quantity=9, unit_price=3200000, low_stock_threshold=4),
        ]
        db.add_all(products)

        staff = [
            Staff(name="امیر تهرانی", role="فروشنده", phone="09122220001"),
            Staff(name="نگار صالحی", role="انباردار", phone="09122220002"),
        ]
        db.add_all(staff)
        db.commit()

        statuses = ["delivered", "pending", "processing", "delivered", "cancelled", "pending", "delivered"]
        for i in range(7):
            order = Order(
                customer_id=customers[i % len(customers)].id,
                status=statuses[i],
                total_price=0,
                created_at=datetime.now() - timedelta(days=i),
                notes=None if i % 3 else "پیگیری ارسال سریع‌تر",
            )
            p1 = products[i % len(products)]
            p2 = products[(i + 3) % len(products)]
            for p, q in [(p1, (i % 2) + 1), (p2, (i % 3) + 1)]:
                order.items.append(OrderItem(product_id=p.id, quantity=q, unit_price=p.unit_price))
                order.total_price += q * p.unit_price
            db.add(order)
        db.commit()
    finally:
        db.close()


orders_router = APIRouter()

@orders_router.get("/orders")
def list_orders(request: Request, db: Session = Depends(get_db)):
    orders = (
        db.query(Order, Customer.name)
        .join(Customer, Order.customer_id == Customer.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("orders.html", {
        "request": request, "orders": orders, "page_title": "سفارش‌ها",
    })


@orders_router.get("/orders/new")
def new_order_form(request: Request, db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    products = db.query(Product).filter(Product.quantity > 0).all()
    return render_template("order_new.html", {
        "request": request, "customers": customers, "products": products,
        "product_options": [{"id": p.id, "name": p.name, "quantity": p.quantity} for p in products],
        "page_title": "سفارش جدید",
    })


@orders_router.post("/orders/new")
def create_order(
    customer_id: int = Form(...),
    product_id: list[int] = Form([]),
    quantities: list[int] = Form([]),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    if not product_id or len(product_id) != len(quantities):
        return RedirectResponse(url="/orders/new", status_code=302)
    order = Order(customer_id=customer_id, notes=notes or None, total_price=0)
    for pid, qty in zip(product_id, quantities):
        if qty <= 0:
            continue
        product = db.query(Product).get(pid)
        if not product:
            continue
        order.items.append(OrderItem(product_id=pid, quantity=qty, unit_price=product.unit_price))
        order.total_price += qty * product.unit_price
        product.quantity = max(0, product.quantity - qty)
    if not order.items:
        db.rollback()
        return RedirectResponse(url="/orders/new", status_code=302)
    db.add(order)
    db.commit()
    return RedirectResponse(url="/orders", status_code=302)


@orders_router.post("/orders/{order_id}/status")
def update_status(order_id: int, new_status: str = Form(...), db: Session = Depends(get_db)):
    order = db.query(Order).get(order_id)
    if order and new_status in ("pending", "processing", "delivered", "cancelled"):
        order.status = new_status
        db.commit()
    return RedirectResponse(url="/orders", status_code=302)


@orders_router.get("/orders/{order_id}/delete")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).get(order_id)
    if order:
        db.delete(order)
        db.commit()
    return RedirectResponse(url="/orders", status_code=302)


inventory_router = APIRouter()

@inventory_router.get("/inventory")
def list_products(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.name).all()
    for p in products:
        p.is_low = p.quantity <= p.low_stock_threshold
    return render_template("inventory.html", {
        "request": request, "products": products, "page_title": "انبار",
    })


@inventory_router.get("/inventory/new")
def new_product_form(request: Request):
    return render_template("product_new.html", {
        "request": request, "page_title": "محصول جدید",
    })


@inventory_router.post("/inventory/new")
def create_product(
    name: str = Form(...),
    category: str = Form(""),
    quantity: int = Form(0),
    unit_price: float = Form(0),
    low_stock_threshold: int = Form(5),
    db: Session = Depends(get_db),
):
    db.add(Product(name=name, category=category, quantity=quantity,
                          unit_price=unit_price, low_stock_threshold=low_stock_threshold))
    db.commit()
    return RedirectResponse(url="/inventory", status_code=302)


@inventory_router.get("/inventory/{product_id}/edit")
def edit_product_form(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        return RedirectResponse(url="/inventory", status_code=302)
    return render_template("product_edit.html", {
        "request": request, "product": product, "page_title": "ویرایش محصول",
    })


@inventory_router.post("/inventory/{product_id}/edit")
def update_product(
    product_id: int,
    name: str = Form(...),
    category: str = Form(""),
    quantity: int = Form(0),
    unit_price: float = Form(0),
    low_stock_threshold: int = Form(5),
    db: Session = Depends(get_db),
):
    product = db.query(Product).get(product_id)
    if product:
        product.name = name
        product.category = category
        product.quantity = quantity
        product.unit_price = unit_price
        product.low_stock_threshold = low_stock_threshold
        db.commit()
    return RedirectResponse(url="/inventory", status_code=302)


@inventory_router.get("/inventory/{product_id}/delete")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/inventory", status_code=302)


@inventory_router.post("/inventory/{product_id}/adjust")
def adjust_stock(product_id: int, delta: int = Form(...), db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if product:
        product.quantity = max(0, product.quantity + delta)
        db.commit()
    return RedirectResponse(url="/inventory", status_code=302)


attendance_router = APIRouter()

@attendance_router.get("/attendance")
def attendance_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    staff = db.query(Staff).all()
    today_rows = (
        db.query(Attendance, Staff.name)
        .join(Staff, Attendance.staff_id == Staff.id)
        .filter(Attendance.date == today)
        .all()
    )
    present_ids = {row.Attendance.staff_id for row in today_rows}
    return render_template("attendance.html", {
        "request": request,
        "today": today,
        "today_rows": today_rows,
        "staff": staff,
        "present_ids": present_ids,
        "page_title": "حضور و غیاب",
    })


@attendance_router.post("/attendance/checkin")
def checkin(staff_id: int = Form(...), db: Session = Depends(get_db)):
    today = date.today()
    exists = db.query(Attendance).filter(
        Attendance.staff_id == staff_id, Attendance.date == today
    ).first()
    if not exists:
        now = datetime.now().strftime("%H:%M")
        status = "present" if now < "09:30" else "late"
        db.add(Attendance(staff_id=staff_id, date=today,
                                 check_in=now, status=status))
        db.commit()
    return RedirectResponse(url="/attendance", status_code=302)


@attendance_router.post("/attendance/checkout")
def checkout(attendance_id: int = Form(...), db: Session = Depends(get_db)):
    row = db.query(Attendance).get(attendance_id)
    if row and not row.check_out:
        row.check_out = datetime.now().strftime("%H:%M")
        db.commit()
    return RedirectResponse(url="/attendance", status_code=302)


@attendance_router.get("/attendance/report")
def monthly_report(request: Request, year: int = date.today().year,
                   month: int = date.today().month, db: Session = Depends(get_db)):
    rows = (
        db.query(Attendance.staff_id,
                 Staff.name,
                 func.sum(Attendance.status == "present").label("present_days"),
                 func.sum(Attendance.status == "late").label("late_days"),
                 func.sum(Attendance.status == "absent").label("absent_days"),
                 func.count(Attendance.id).label("total_days"))
        .join(Staff, Attendance.staff_id == Staff.id)
        .filter(func.cast(func.strftime("%Y", Attendance.date), Integer) == year,
                func.cast(func.strftime("%m", Attendance.date), Integer) == month)
        .group_by(Attendance.staff_id, Staff.name)
        .all()
    )
    return render_template("attendance_report.html", {
        "request": request, "rows": rows, "year": year, "month": month,
        "page_title": "گزارش ماهانه",
    })


@attendance_router.get("/attendance/staff/new")
def new_staff_form(request: Request):
    return render_template("staff_new.html", {
        "request": request, "page_title": "کارمند جدید",
    })


@attendance_router.post("/attendance/staff/new")
def create_staff(name: str = Form(...), role: str = Form(""), phone: str = Form(""),
                 db: Session = Depends(get_db)):
    db.add(Staff(name=name, role=role or None, phone=phone or None))
    db.commit()
    return RedirectResponse(url="/attendance", status_code=302)


suggestions_router = APIRouter()

@suggestions_router.get("/suggestions")
def suggestions(request: Request, db: Session = Depends(get_db)):
    top_sellers = (
        db.query(Product.name,
                 func.sum(OrderItem.quantity).label("total_sold"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    max_sold = max((s.total_sold or 0) for s in top_sellers) if top_sellers else 0
    low_stock = db.query(Product).filter(
        Product.quantity <= Product.low_stock_threshold
    ).all()
    reorder = [{
        "name": p.name,
        "quantity": p.quantity,
        "threshold": p.low_stock_threshold,
        "suggested_qty": max(p.low_stock_threshold * 2 - p.quantity, 1),
    } for p in low_stock]
    return render_template("suggestions.html", {
        "request": request, "top_sellers": top_sellers,
        "max_sold": max_sold or 1, "reorder": reorder,
        "page_title": "پیشنهادات",
    })


# Register all routers after their endpoint definitions.
app.include_router(orders_router)
app.include_router(inventory_router)
app.include_router(attendance_router)
app.include_router(suggestions_router)
