"""Notification dispatcher — routes to email or SMS."""
import logging
from .email import send_email

logger = logging.getLogger(__name__)


def dispatch_welcome_email(user_email: str, user_name: str) -> dict:
    """Send a welcome email to a new user."""
    subject = f"Welcome to the platform, {user_name}!"
    body = (
        f"Hi {user_name},\n\n"
        "Thanks for signing up. Your account is ready.\n\n"
        "Best,\nThe Team"
    )
    return send_email(user_email, subject, body)


def dispatch_password_reset(user_email: str, reset_token: str) -> dict:
    """Send a password reset email."""
    subject = "Reset your password"
    body = (
        f"Click this link to reset your password:\n"
        f"https://app.example.com/reset?token={reset_token}\n\n"
        "This link expires in 1 hour."
    )
    return send_email(user_email, subject, body)


def dispatch_order_confirmation(user_email: str, order_id: str, total: float) -> dict:
    """Send an order confirmation email."""
    subject = f"Order confirmation #{order_id}"
    body = f"Your order #{order_id} for ${total:.2f} has been confirmed."
    return send_email(user_email, subject, body)
