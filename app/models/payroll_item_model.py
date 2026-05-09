from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PayrollItem:
    payroll_id: int
    item_type: int
    quantity: Decimal
    unit_amount: Decimal
    amount: Decimal
    description: str
