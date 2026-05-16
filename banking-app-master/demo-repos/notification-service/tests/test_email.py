"""Tests for email dispatcher."""
import pytest
import os
from unittest.mock import patch, MagicMock


def test_send_email_success():
    """Test with mocked SendGrid and env var set."""
    with patch.dict(os.environ, {"SENDGRID_API_KEY": "test-key"}):
        with patch("src.notifications.email.sendgrid") as mock_sg:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_sg.SendGridAPIClient.return_value.send.return_value = mock_response

            from src.notifications.email import send_email
            result = send_email("test@example.com", "Subject", "Body")
            assert result["status_code"] == 202


def test_send_email_missing_env():
    """This test documents the bug — KeyError when SENDGRID_API_KEY is absent."""
    env = {k: v for k, v in os.environ.items() if k != "SENDGRID_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        from src.notifications.email import send_email
        with pytest.raises(KeyError, match="SENDGRID_API_KEY"):
            send_email("test@example.com", "Subject", "Body")
