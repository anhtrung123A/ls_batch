from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Payroll:
    id: int
    status: int


@dataclass(frozen=True)
class PayrollAmounts:
    base_amount: Decimal
    teaching_amount: Decimal
    kpi_amount: Decimal
    bonus_amount: Decimal
    deduction_amount: Decimal
    gross_amount: Decimal
    net_amount: Decimal
