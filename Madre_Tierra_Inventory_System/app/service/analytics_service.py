"""Sales and customer numbers for the dashboard.

Orders are stored in naive UTC; days and months are counted in the business time zone.
A customer is "new" in the period that holds their first non-cancelled order, and a
"repeat" customer in any period they buy in once they have two or more orders.
"""
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.models import Client, Order, OrderProduct, Product
from app.schema.analytics import (
    AnalyticsSummary,
    MonthTotals,
    PeriodTotals,
    ProductSales,
    SourceCount,
    StockAlert,
)

CENTS = Decimal("0.01")
TOP_PRODUCTS = 5
LOW_STOCK_UNITS = 5
LOW_STOCK_DAYS = 30
MAX_RANGE_DAYS = 3660


def summary_service(
    session: Session,
    start: date | None = None,
    end: date | None = None,
    today: date | None = None,
) -> AnalyticsSummary:
    zone = ZoneInfo(settings.business_timezone)
    today = today or datetime.now(zone).date()
    end = end or today
    start = start or _month_start(end, -11)
    if start > end:
        raise ValueError("start must be on or before end")
    if (end - start).days > MAX_RANGE_DAYS:
        raise ValueError("Choose a range of ten years or less")

    def bound(day: date) -> datetime:
        """Midnight of a local day, as the naive UTC value stored in the database."""
        return datetime.combine(day, time.min, zone).astimezone(UTC).replace(tzinfo=None)

    def month_of(moment: datetime) -> str:
        return moment.replace(tzinfo=UTC).astimezone(zone).strftime("%Y-%m")

    lower, upper = bound(start), bound(end + timedelta(days=1))
    previous_lower = bound(start - timedelta(days=(end - start).days + 1))

    sold = col(Order.cancelled_at).is_(None)
    first_order = (
        select(Order.client_id, func.min(Order.created_at).label("first_at"))
        .where(sold)
        .group_by(Order.client_id)
        .subquery()
    )
    first_orders: dict[int, datetime] = dict(
        session.exec(select(first_order.c.client_id, first_order.c.first_at)).all()
    )
    orders = session.exec(
        select(Order).where(Order.created_at >= previous_lower, Order.created_at < upper)
    ).all()

    revenue: Counter[str] = Counter()
    order_count: Counter[str] = Counter()
    new_count: Counter[str] = Counter()
    for order in orders:
        if order.created_at >= lower and order.cancelled_at is None:
            revenue[month_of(order.created_at)] += order.total
            order_count[month_of(order.created_at)] += 1
    for first_at in first_orders.values():
        if lower <= first_at < upper:
            new_count[month_of(first_at)] += 1

    months = []
    cursor = start.replace(day=1)
    while cursor <= end:
        months.append(cursor.strftime("%Y-%m"))
        cursor = _month_start(cursor, 1)

    line_revenue = func.sum(OrderProduct.unit_price * OrderProduct.quantity)
    top_products = session.exec(
        select(Product.id, Product.name, func.sum(OrderProduct.quantity), line_revenue)
        .join(OrderProduct, col(OrderProduct.product_id) == Product.id)
        .join(Order, col(Order.id) == OrderProduct.order_id)
        .where(sold, Order.created_at >= lower, Order.created_at < upper)
        .group_by(Product.id, Product.name)
        .order_by(line_revenue.desc())
        .limit(TOP_PRODUCTS)
    ).all()

    sources = session.exec(
        select(Client.source, func.count())
        .join(first_order, first_order.c.client_id == Client.id)
        .where(first_order.c.first_at >= lower, first_order.c.first_at < upper)
        .group_by(Client.source)
        .order_by(func.count().desc())
    ).all()

    return AnalyticsSummary(
        start=start,
        end=end,
        timezone=settings.business_timezone,
        currency=settings.currency,
        current=_period_totals(session, orders, first_orders, lower, upper),
        previous=_period_totals(session, orders, first_orders, previous_lower, lower),
        monthly=[
            MonthTotals(
                month=month,
                revenue=Decimal(revenue[month]),
                orders=order_count[month],
                new_customers=new_count[month],
            )
            for month in months
        ],
        top_products=[
            ProductSales(product_id=product_id, name=name, units=units, revenue=_money(total))
            for product_id, name, units, total in top_products
        ],
        new_customers_by_source=[
            SourceCount(source=source or "Not recorded", customers=count)
            for source, count in sources
        ],
        low_stock=_low_stock(session, since=bound(today - timedelta(days=LOW_STOCK_DAYS - 1))),
    )


def _period_totals(
    session: Session,
    orders: list[Order],
    first_orders: dict[int, datetime],
    lower: datetime,
    upper: datetime,
) -> PeriodTotals:
    in_period = [order for order in orders if lower <= order.created_at < upper]
    sold = [order for order in in_period if order.cancelled_at is None]
    revenue = sum((order.total for order in sold), Decimal("0"))
    buyers = {order.client_id for order in sold}
    new = {client_id for client_id in buyers if first_orders[client_id] >= lower}
    repeat_buyers = set(
        session.exec(
            select(Order.client_id)
            .where(col(Order.cancelled_at).is_(None), Order.created_at < upper)
            .group_by(Order.client_id)
            .having(func.count() >= 2)
        ).all()
    )
    return PeriodTotals(
        revenue=revenue,
        orders=len(sold),
        average_order=(revenue / len(sold)).quantize(CENTS) if sold else Decimal("0"),
        new_customers=len(new),
        repeat_customers=len(buyers & repeat_buyers),
        cancelled_orders=len(in_period) - len(sold),
    )


def _low_stock(session: Session, since: datetime) -> list[StockAlert]:
    """Products that are nearly out, or will run out within LOW_STOCK_DAYS at the recent pace."""
    recent_units = dict(
        session.exec(
            select(OrderProduct.product_id, func.sum(OrderProduct.quantity))
            .join(Order, col(Order.id) == OrderProduct.order_id)
            .where(col(Order.cancelled_at).is_(None), Order.created_at >= since)
            .group_by(OrderProduct.product_id)
        ).all()
    )
    alerts = []
    for product in session.exec(select(Product)).all():
        units = recent_units.get(product.id, 0)
        days_left = product.quantity * LOW_STOCK_DAYS // units if units else None
        if product.quantity <= LOW_STOCK_UNITS or (
            days_left is not None and days_left <= LOW_STOCK_DAYS
        ):
            alerts.append(
                StockAlert(
                    product_id=product.id,
                    name=product.name,
                    quantity=product.quantity,
                    sold_last_30_days=units,
                    days_left=days_left,
                )
            )
    alerts.sort(key=lambda alert: (
        alert.quantity > 0,
        alert.days_left if alert.days_left is not None else LOW_STOCK_DAYS + 1,
        alert.quantity,
    ))
    return alerts


def _month_start(day: date, offset: int) -> date:
    """First day of the month `offset` months away from `day`'s month."""
    index = day.year * 12 + day.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def _money(value) -> Decimal:
    # SQLite returns sums of Numeric columns as floats; Postgres returns Decimal.
    return Decimal(str(value or 0)).quantize(CENTS)
