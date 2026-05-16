# payment-service

Handles card charging and payment processing via Stripe.

## Bug (planted for RCA demo)

A recent "perf" commit removed the null-guard in `processor.py:charge_card`, causing
`AttributeError: 'NoneType' object has no attribute 'total'` when `_fetch_order`
returns `None` for expired session orders.
