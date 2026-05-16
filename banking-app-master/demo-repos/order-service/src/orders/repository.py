"""In-memory order repository (stub — replace with DB in production)."""
from .models import Order

_store: dict[str, Order] = {}


def save(order: Order) -> Order:
    _store[order.id] = order
    return order


def find_by_id(order_id: str) -> Order | None:
    return _store.get(order_id)


def find_by_customer(customer_id: str) -> list[Order]:
    return [o for o in _store.values() if o.customer_id == customer_id]
