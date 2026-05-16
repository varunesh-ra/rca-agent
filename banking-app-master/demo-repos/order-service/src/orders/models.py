from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class OrderItem:
    product_id: str
    quantity: int
    unit_price: float


@dataclass
class Order:
    id: str
    customer_id: str
    items: list[OrderItem]
    shipping_address: str
    created_at: datetime
    status: str = "pending"
    coupon_code: str | None = None

    @property
    def total(self) -> float:
        return sum(i.quantity * i.unit_price for i in self.items)
