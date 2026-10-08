from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def render_template(name, context):
    return templates.TemplateResponse(request=context["request"], name=name, context=context)


@router.get("/orders")
def list_orders(request: Request, db: Session = Depends(get_db)):
    orders = (
        db.query(models.Order, models.Customer.name)
        .join(models.Customer, models.Order.customer_id == models.Customer.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return render_template("orders.html", {
        "request": request, "orders": orders, "page_title": "سفارش‌ها",
    })


@router.get("/orders/new")
def new_order_form(request: Request, db: Session = Depends(get_db)):
    customers = db.query(models.Customer).all()
    products = db.query(models.Product).filter(models.Product.quantity > 0).all()
    return render_template("order_new.html", {
        "request": request, "customers": customers, "products": products,
        "product_options": [{"id": p.id, "name": p.name, "quantity": p.quantity} for p in products],
        "page_title": "سفارش جدید",
    })


@router.post("/orders/new")
def create_order(
    customer_id: int = Form(...),
    product_id: list[int] = Form([]),
    quantities: list[int] = Form([]),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    if not product_id or len(product_id) != len(quantities):
        return RedirectResponse(url="/orders/new", status_code=302)
    order = models.Order(customer_id=customer_id, notes=notes or None, total_price=0)
    for pid, qty in zip(product_id, quantities):
        if qty <= 0:
            continue
        product = db.query(models.Product).get(pid)
        if not product:
            continue
        order.items.append(models.OrderItem(product_id=pid, quantity=qty, unit_price=product.unit_price))
        order.total_price += qty * product.unit_price
        product.quantity = max(0, product.quantity - qty)
    if not order.items:
        db.rollback()
        return RedirectResponse(url="/orders/new", status_code=302)
    db.add(order)
    db.commit()
    return RedirectResponse(url="/orders", status_code=302)


@router.post("/orders/{order_id}/status")
def update_status(order_id: int, new_status: str = Form(...), db: Session = Depends(get_db)):
    order = db.query(models.Order).get(order_id)
    if order and new_status in ("pending", "processing", "delivered", "cancelled"):
        order.status = new_status
        db.commit()
    return RedirectResponse(url="/orders", status_code=302)


@router.get("/orders/{order_id}/delete")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).get(order_id)
    if order:
        db.delete(order)
        db.commit()
    return RedirectResponse(url="/orders", status_code=302)
