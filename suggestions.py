from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def render_template(name, context):
    return templates.TemplateResponse(request=context["request"], name=name, context=context)


@router.get("/suggestions")
def suggestions(request: Request, db: Session = Depends(get_db)):
    top_sellers = (
        db.query(models.Product.name,
                 func.sum(models.OrderItem.quantity).label("total_sold"))
        .join(models.OrderItem, models.OrderItem.product_id == models.Product.id)
        .group_by(models.Product.id, models.Product.name)
        .order_by(func.sum(models.OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    max_sold = max((s.total_sold or 0) for s in top_sellers) if top_sellers else 0
    low_stock = db.query(models.Product).filter(
        models.Product.quantity <= models.Product.low_stock_threshold
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
