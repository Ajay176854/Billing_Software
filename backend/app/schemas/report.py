"""
Report schemas.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DailySalesReport(BaseModel):
    date: str
    total_sales: float
    total_bills: int
    total_discount: float
    total_tax: float


class ProductSalesReport(BaseModel):
    product_id: int
    product_name: str
    barcode: Optional[str] = None
    total_qty_sold: int
    total_revenue: float


class InventoryReport(BaseModel):
    product_id: int
    product_name: str
    barcode: Optional[str] = None
    category_name: Optional[str] = None
    stock_qty: int
    purchase_price: float
    selling_price: float
    stock_value: float  # stock_qty * purchase_price
    status: str


class PaymentSummary(BaseModel):
    payment_method: str
    total_amount: float
    count: int


class DashboardStats(BaseModel):
    today_sales: float
    today_bills: int
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    total_inventory_value: float
    recent_sales: List[dict] = []
    top_products: List[dict] = []
    payment_summary: List[PaymentSummary] = []
