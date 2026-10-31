from datetime import date
from decimal import Decimal

from sqlmodel import SQLModel


class PeriodTotals(SQLModel):
    revenue: Decimal
    orders: int
    average_order: Decimal
    new_customers: int
    repeat_customers: int  # bought in the period and have 2+ orders in total
    cancelled_orders: int


class MonthTotals(SQLModel):
    month: str  # YYYY-MM in the business time zone
    revenue: Decimal
    orders: int
    new_customers: int


class ProductSales(SQLModel):
    product_id: int
    name: str
    units: int
    revenue: Decimal


class SourceCount(SQLModel):
    source: str
    customers: int


class StockAlert(SQLModel):
    product_id: int
    name: str
    quantity: int
    sold_last_30_days: int
    days_left: int | None  # None when nothing sold in the last 30 days


class AnalyticsSummary(SQLModel):
    start: date
    end: date
    timezone: str
    currency: str
    current: PeriodTotals
    previous: PeriodTotals
    monthly: list[MonthTotals]
    top_products: list[ProductSales]
    new_customers_by_source: list[SourceCount]
    low_stock: list[StockAlert]
