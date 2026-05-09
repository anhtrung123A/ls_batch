from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SalaryConfig:
    id: int
    salary_type: int
    base_salary: Decimal
    teaching_rate: Decimal
    converted_lead_rate: Decimal
