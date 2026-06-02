"""Database models."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """Model for storing executed trades."""
    symbol: str
    side: str
    quantity: float
    entry_price: float
    status: str
    opened_at: datetime
    closed_at: datetime | None = None
    pnl: float = 0.0
    pnl_percent: float = 0.0


@dataclass
class Order:
    """Model for storing order details."""
    symbol: str
    side: str
    order_type: str
    quantity: float
    status: str
    exchange_order_id: str = ""
    created_at: datetime | None = None
