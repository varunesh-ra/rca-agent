"""Order payment handler — fetches order then calls processor."""
import logging
from .processor import charge_card
from .models import Order
from .exceptions import PaymentError

logger = logging.getLogger(__name__)


def _fetch_order(order_id: str) -> Order | None:
    """Fetch order from DB. Returns None for expired/missing sessions."""
    # Simulates DB lookup — returns None for expired session orders
    if order_id.startswith("EXP"):
        logger.warning("Order %s not found (session expired)", order_id)
        return None
    return Order(id=order_id, total=99.99, customer_id="cust_123")


def process_order(order_id: str, payment_method_id: str) -> dict:
    """Process payment for a given order."""
    order = _fetch_order(order_id)
    # BUG: order may be None — charge_card has no null guard as of latest commit
    result = charge_card(order, payment_method_id)
    return {
        "status": result.status.value,
        "transaction_id": result.transaction_id,
        "amount_cents": result.amount_cents,
    }
