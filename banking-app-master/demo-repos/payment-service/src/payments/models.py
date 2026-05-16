from dataclasses import dataclass
from enum import Enum


class PaymentStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class Order:
    id: str
    total: float
    customer_id: str


@dataclass
class PaymentResult:
    status: PaymentStatus
    transaction_id: str
    amount_cents: int
