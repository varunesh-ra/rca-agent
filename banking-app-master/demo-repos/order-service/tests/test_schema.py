"""Schema validation tests — note: these import schema which will fail in v2!"""
import pytest


def test_import_schema():
    """This test will fail due to the pydantic v1 @validator bug."""
    # In pydantic v2, importing schema.py raises PydanticUserError immediately
    try:
        from src.orders.schema import CreateOrderRequest
        assert CreateOrderRequest is not None
    except Exception as e:
        pytest.fail(f"Import failed (pydantic v2 migration bug): {e}")


def test_valid_order_item():
    from src.orders.schema import OrderItemSchema
    item = OrderItemSchema(product_id="prod_1", quantity=2, unit_price=9.99)
    assert item.quantity == 2
