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
