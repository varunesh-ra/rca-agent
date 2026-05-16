# order-service

Manages order creation, validation, and lifecycle.

## Bug (planted for RCA demo)

A dependency upgrade to Pydantic v2 was made without migrating validators.
`src/orders/schema.py` still uses the Pydantic v1 `@validator` decorator which was
removed in v2, causing `PydanticUserError` on import.
