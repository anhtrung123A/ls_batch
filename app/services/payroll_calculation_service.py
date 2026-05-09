from decimal import Decimal

from app.models.payroll_item_model import PayrollItem
from app.models.payroll_model import PayrollAmounts
from app.models.salary_config_model import SalaryConfig
from app.models.staff_kpi_record_model import StaffKpiAggregate


class PayrollCalculationService:
    @staticmethod
    def build_base_item(payroll_id: int, base_amount: Decimal) -> PayrollItem:
        return PayrollItem(
            payroll_id=payroll_id,
            item_type=1,
            quantity=Decimal("1"),
            unit_amount=base_amount,
            amount=base_amount,
            description="base salary",
        )

    @staticmethod
    def calculate_teaching_amount(salary_config: SalaryConfig, teaching_count: int) -> tuple[Decimal, PayrollItem | None]:
        amount = Decimal(teaching_count) * salary_config.teaching_rate
        if teaching_count <= 0:
            return amount, None
        return amount, PayrollItem(
            payroll_id=0,
            item_type=2,
            quantity=Decimal(teaching_count),
            unit_amount=salary_config.teaching_rate,
            amount=amount,
            description="teaching sessions",
        )

    @staticmethod
    def calculate_kpi_amount(salary_config: SalaryConfig, kpi: StaffKpiAggregate) -> tuple[Decimal, PayrollItem | None]:
        amount = kpi.total_amount if kpi.total_amount > 0 else (Decimal(kpi.quantity) * salary_config.converted_lead_rate)
        if kpi.quantity <= 0:
            return amount, None
        unit_amount = salary_config.converted_lead_rate if salary_config.converted_lead_rate > 0 else (amount / Decimal(kpi.quantity))
        return amount, PayrollItem(
            payroll_id=0,
            item_type=3,
            quantity=Decimal(kpi.quantity),
            unit_amount=unit_amount,
            amount=amount,
            description="converted leads",
        )

    @staticmethod
    def calculate_payroll_amounts(base_amount: Decimal, teaching_amount: Decimal, kpi_amount: Decimal) -> PayrollAmounts:
        bonus_amount = Decimal("0")
        deduction_amount = Decimal("0")
        gross_amount = base_amount + teaching_amount + kpi_amount + bonus_amount - deduction_amount
        net_amount = gross_amount
        return PayrollAmounts(
            base_amount=base_amount,
            teaching_amount=teaching_amount,
            kpi_amount=kpi_amount,
            bonus_amount=bonus_amount,
            deduction_amount=deduction_amount,
            gross_amount=gross_amount,
            net_amount=net_amount,
        )
