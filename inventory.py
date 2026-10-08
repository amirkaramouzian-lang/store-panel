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


@router.get("/inventory")
def list_products(request: Request, db: Session = Depends(get_db)):
    products = db.query(models.Product).order_by(models.Product.name).all()
    for p in products:
        p.is_low = p.quantity <= p.low_stock_threshold
    return render_template("inventory.html", {
        "request": request, "products": products, "page_title": "انبار",
    })


@router.get("/inventory/new")
def new_product_form(request: Request):
    return render_template("product_new.html", {
        "request": request, "page_title": "محصول جدید",
    })


@router.post("/inventory/new")
def create_product(
    name: str = Form(...),
    category: str = Form(""),
    quantity: int = Form(0),
    unit_price: float = Form(0),
    low_stock_threshold: int = Form(5),
    db: Session = Depends(get_db),
):
    db.add(models.Product(name=name, category=category, quantity=quantity,
                          unit_price=unit_price, low_stock_threshold=low_stock_threshold))
    db.commit()
    return RedirectResponse(url="/inventory", status_code=302)


@router.get("/inventory/{product_id}/edit")
def edit_product_form(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        return RedirectResponse(url="/inventory", status_code=302)
    return render_template("product_edit.html", {
        "request": request, "product": product, "page_title": "ویرایش محصول",
    })


@router.post("/inventory/{product_id}/edit")
def update_product(
    product_id: int,
    name: str = Form(...),
    category: str = Form(""),
    quantity: int = Form(0),
    unit_price: float = Form(0),
    low_stock_threshold: int = Form(5),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).get(product_id)
    if product:
        product.name = name
        product.category = category
        product.quantity = quantity
        product.unit_price = unit_price
        product.low_stock_threshold = low_stock_threshold
        db.commit()
    return RedirectResponse(url="/inventory", status_code=302)


@router.get("/inventory/{product_id}/delete")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/inventory", status_code=302)


@router.post("/inventory/{product_id}/adjust")
def adjust_stock(product_id: int, delta: int = Form(...), db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if product:
        product.quantity = max(0, product.quantity + delta)
        db.commit()
    return RedirectResponse(url="/inventory", status_code=302)
