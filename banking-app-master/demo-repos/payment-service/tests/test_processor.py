"""Tests for payment processor — note: null case NOT tested (the bug)."""
import pytest
from src.payments.models import Order, PaymentStatus
from src.payments.processor import charge_card
from src.payments.exceptions import PaymentError
from unittest.mock import patch, MagicMock


@patch("src.payments.processor.stripe")
def test_charge_card_success(mock_stripe):
    mock_intent = MagicMock()
    mock_intent.id = "pi_test_123"
    mock_stripe.PaymentIntent.create.return_value = mock_intent

    order = Order(id="ORD-001", total=50.00, customer_id="cust_1")
    result = charge_card(order, "pm_test_visa")
    assert result.status == PaymentStatus.SUCCESS
    assert result.amount_cents == 5000


def test_charge_card_zero_total():
    order = Order(id="ORD-002", total=0.0, customer_id="cust_1")
    with pytest.raises(PaymentError, match="Invalid order total"):
        charge_card(order, "pm_test_visa")


# Missing test: test_charge_card_none_order — this is the bug!
# def test_charge_card_none_order():
#     with pytest.raises(PaymentError):
#         charge_card(None, "pm_test_visa")
