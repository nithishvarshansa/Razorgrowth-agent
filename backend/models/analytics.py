from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedOrder:
    id: str
    status: str | None
    amount: int | None
    currency: str | None
    customer_id: str | None
    product_id: str | None
    product_name: str | None
    created_at: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedPayment:
    id: str
    order_id: str | None
    status: str | None
    amount: int | None
    currency: str | None
    customer_id: str | None
    created_at: int | None
    success: bool
    failed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
