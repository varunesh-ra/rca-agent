# notification-service

Dispatches transactional notifications (email via SendGrid, SMS via Twilio).

## Bug (planted for RCA demo)

A refactor commit changed `os.environ.get("SENDGRID_API_KEY", "")` to
`os.environ["SENDGRID_API_KEY"]` in `src/notifications/email.py`.
This causes a `KeyError` in staging where the env var is not set.

Note: This service is intentionally NOT registered in service_repo_map — the
sub-agent discovery path will be exercised during the RCA demo.
