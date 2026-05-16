"""Notification service config."""
import os


class NotificationConfig:
    """Read config from environment variables."""
    sendgrid_api_key: str = os.environ.get("SENDGRID_API_KEY", "")
    twilio_sid: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
    twilio_token: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_email: str = os.environ.get("FROM_EMAIL", "noreply@example.com")
    from_phone: str = os.environ.get("FROM_PHONE", "+15550000000")


config = NotificationConfig()
