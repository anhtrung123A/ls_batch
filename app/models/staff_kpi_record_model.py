from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StaffKpiAggregate:
    quantity: int
    total_amount: Decimal
