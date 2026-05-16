"""Order request/response schemas — Pydantic models."""
from pydantic import BaseModel, validator  # @validator removed in pydantic v2!


class OrderItemSchema(BaseModel):
    product_id: str
    quantity: int
    unit_price: float

    @validator("quantity")  # Pydantic v1 style — PydanticUserError in v2
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @validator("unit_price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Unit price must be positive")
        return v


class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list[OrderItemSchema]
    shipping_address: str
    coupon_code: str | None = None


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    status: str
    total: float
    created_at: str
