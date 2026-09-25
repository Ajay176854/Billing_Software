# Models package — import all models so Base.metadata knows about them
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.stock_transaction import StockTransaction
from app.models.setting import Setting

__all__ = [
    "User",
    "Category",
    "Product",
    "Sale",
    "SaleItem",
    "StockTransaction",
    "Setting",
]
