#!/usr/bin/env bash
# setup_git_history.sh
# ─────────────────────────────────────────────────────────────────────────────
# Creates git history for all 3 demo repos with:
#   commit 1: "feat: initial implementation" (GOOD version — bug NOT present)
#   commit 2: the regressing commit          (BAD version — bug introduced)
#
# After running this, the script prints the HEAD SHA for each repo.
# You MUST update demo-repos/payment-service, order-service SHAs in:
#   rca-agent/rca_agent/adapters/cicd/mock_fixtures.py
#
# Usage: cd demo-repos && bash setup_git_history.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"

git_setup() {
    git init -b main
    git config user.email "demo@rca-agent.dev"
    git config user.name "RCA Demo"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. payment-service
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setting up payment-service ==="
cd "$DEMO_DIR/payment-service"
git_setup

# GOOD version: null guard present
cat > src/payments/processor.py << 'PYEOF'
"""Payment processor — charge card and record transaction."""
import logging
from .models import Order, PaymentResult, PaymentStatus
from .exceptions import PaymentError

logger = logging.getLogger(__name__)
STRIPE_MULTIPLIER = 100  # convert dollars to cents


def charge_card(order: Order, payment_method_id: str) -> PaymentResult:
    """Charge the customer card for the given order."""
    if order is None:
        raise PaymentError("Order not found or session expired")
    if order.total <= 0:
        raise PaymentError(f"Invalid order total: {order.total}")
    amount_cents = order.total * STRIPE_MULTIPLIER
    try:
        import stripe
        intent = stripe.PaymentIntent.create(
            amount=int(amount_cents),
            currency="usd",
            payment_method=payment_method_id,
            confirm=True,
        )
        logger.info("Charged %s cents for order %s", int(amount_cents), order.id)
        return PaymentResult(
            status=PaymentStatus.SUCCESS,
            transaction_id=intent.id,
            amount_cents=int(amount_cents),
        )
    except Exception as e:
        raise PaymentError(str(e)) from e
PYEOF

git add .
git commit -m "feat: initial payment processor implementation"

# BAD version: null guard removed
cat > src/payments/processor.py << 'PYEOF'
"""Payment processor — charge card and record transaction."""
import logging
from .models import Order, PaymentResult, PaymentStatus
from .exceptions import PaymentError

logger = logging.getLogger(__name__)
STRIPE_MULTIPLIER = 100  # convert dollars to cents


def charge_card(order: Order, payment_method_id: str) -> PaymentResult:
    """Charge the customer card for the given order."""
    # PERF: removed null guard to streamline hot path
    amount_cents = order.total * STRIPE_MULTIPLIER  # AttributeError if order is None
    if amount_cents <= 0:
        raise PaymentError(f"Invalid order total: {order.total}")
    try:
        import stripe
        intent = stripe.PaymentIntent.create(
            amount=int(amount_cents),
            currency="usd",
            payment_method=payment_method_id,
            confirm=True,
        )
        logger.info("Charged %s cents for order %s", int(amount_cents), order.id)
        return PaymentResult(
            status=PaymentStatus.SUCCESS,
            transaction_id=intent.id,
            amount_cents=int(amount_cents),
        )
    except Exception as e:
        raise PaymentError(str(e)) from e
PYEOF

git add .
git commit -m "perf: streamline charge_card hot path"
PAYMENT_SHA=$(git rev-parse HEAD)
echo "payment-service HEAD SHA: $PAYMENT_SHA"

# ─────────────────────────────────────────────────────────────────────────────
# 2. order-service
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setting up order-service ==="
cd "$DEMO_DIR/order-service"
git_setup

# GOOD version: pydantic v1 style with pydantic < 2 pinned
cat > src/orders/schema.py << 'PYEOF'
"""Order request/response schemas — Pydantic models (v1 compatible)."""
from pydantic import BaseModel, field_validator


class OrderItemSchema(BaseModel):
    product_id: str
    quantity: int
    unit_price: float

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("unit_price")
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
PYEOF

git add .
git commit -m "feat: initial order schema with field validators"

# BAD version: downgraded to @validator (pydantic v1 style) after v2 upgrade
cat > src/orders/schema.py << 'PYEOF'
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
PYEOF

# Also bump pydantic version in pyproject.toml
sed -i 's/pydantic>=1.10,<2/pydantic>=2.6.0/' pyproject.toml 2>/dev/null || true

git add .
git commit -m "chore: upgrade dependencies, pydantic to v2"
ORDER_SHA=$(git rev-parse HEAD)
echo "order-service HEAD SHA: $ORDER_SHA"

# ─────────────────────────────────────────────────────────────────────────────
# 3. notification-service
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setting up notification-service ==="
cd "$DEMO_DIR/notification-service"
git_setup

# GOOD version: safe env var access with .get()
cat > src/notifications/email.py << 'PYEOF'
"""Email dispatcher using SendGrid."""
import os
import logging

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> dict:
    """Send a transactional email via SendGrid."""
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if not api_key:
        raise EnvironmentError("SENDGRID_API_KEY environment variable is not set")
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email="noreply@example.com",
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )
        response = sg.send(message)
        logger.info("Email sent to %s, status=%s", to, response.status_code)
        return {"status_code": response.status_code, "to": to, "subject": subject}
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        raise
PYEOF

git add .
git commit -m "feat: initial email dispatcher with safe env var access"

# BAD version: direct dict access causes KeyError
cat > src/notifications/email.py << 'PYEOF'
"""Email dispatcher using SendGrid."""
import os
import logging

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> dict:
    """Send a transactional email via SendGrid."""
    api_key = os.environ["SENDGRID_API_KEY"]  # KeyError if env var not set!
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email="noreply@example.com",
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )
        response = sg.send(message)
        logger.info("Email sent to %s, status=%s", to, response.status_code)
        return {"status_code": response.status_code, "to": to, "subject": subject}
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        raise
PYEOF

git add .
git commit -m "refactor: simplify env var access"
NOTIF_SHA=$(git rev-parse HEAD)
echo "notification-service HEAD SHA: $NOTIF_SHA"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo "Git history created. Next steps:"
echo ""
echo "1. Update mock_fixtures.py with these SHAs:"
echo "   payment-service:      $PAYMENT_SHA"
echo "   order-service:        $ORDER_SHA"
echo "   notification-service: $NOTIF_SHA"
echo ""
echo "2. Push repos to GitHub (see push_to_github.sh)"
echo ""
echo "3. Run: python demo_seed_data.py"
echo "========================================================"
