from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


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
