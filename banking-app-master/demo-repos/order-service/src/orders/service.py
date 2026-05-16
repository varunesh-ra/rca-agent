"""Order service business logic."""
import uuid
from datetime import datetime, timezone
from .schema import CreateOrderRequest, OrderResponse
from .models import Order, OrderItem


def create_order(req: CreateOrderRequest) -> OrderResponse:
    """Validate and create a new order."""
    items = [
        OrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        for item in req.items
    ]
    order = Order(
        id=str(uuid.uuid4()),
        customer_id=req.customer_id,
        items=items,
        shipping_address=req.shipping_address,
        created_at=datetime.now(timezone.utc),
        coupon_code=req.coupon_code,
    )
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        status=order.status,
        total=order.total,
        created_at=order.created_at.isoformat(),
    )
