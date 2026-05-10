import calendar
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.payroll_item_model import PayrollItem
from app.models.payroll_model import PayrollAmounts
from app.models.user_model import PayrollUser
from app.repositories.payroll_activity_repository import PayrollActivityRepository
from app.repositories.payroll_repository import PayrollRepository
from app.repositories.payroll_user_repository import PayrollUserRepository
from app.repositories.salary_config_repository import SalaryConfigRepository
from app.services.email_service import EmailService
from app.services.payroll_calculation_service import PayrollCalculationService


@dataclass(frozen=True)
class PayrollContext:
    month: int
    year: int
    start_date: date
    end_date: date


@dataclass(frozen=True)
class PayrollProcessResult:
    status: str
    payroll_id: int | None = None
    reason: str | None = None


class PayrollGenerationService:
    def __init__(self, connection, email_service: EmailService):
        self.connection = connection
        self.email_service = email_service
        self.calc_service = PayrollCalculationService()
        self.payroll_user_repository = PayrollUserRepository(connection)
        self.salary_config_repository = SalaryConfigRepository(connection)
        self.payroll_repository = PayrollRepository(connection)
        self.payroll_activity_repository = PayrollActivityRepository(connection)

    @staticmethod
    def resolve_payroll_context() -> PayrollContext:
        month_env = os.getenv("PAYROLL_MONTH")
        year_env = os.getenv("PAYROLL_YEAR")
        if month_env and year_env:
            month = int(month_env)
            year = int(year_env)
        else:
            today = datetime.utcnow().date()
            first_day_this_month = today.replace(day=1)
            target_day = first_day_this_month - timedelta(days=1)
            month = target_day.month
            year = target_day.year
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
        return PayrollContext(month=month, year=year, start_date=start_date, end_date=end_date)

    def get_active_users(self) -> list[PayrollUser]:
        return self.payroll_user_repository.get_active_payroll_users()

    def process_user(self, user_id: int, context: PayrollContext) -> PayrollProcessResult:
        salary_config = self.salary_config_repository.get_active_salary_config(user_id, context.start_date, context.end_date)
        if salary_config is None:
            return PayrollProcessResult(status="skipped", reason="No active salary config.")

        existing = self.payroll_repository.get_existing_payroll(user_id, context.month, context.year)
        if existing and existing.status != 1:
            return PayrollProcessResult(status="skipped", reason=f"Payroll already exists with non-draft status={existing.status}.")

        if existing:
            payroll_id = existing.id
            self.payroll_repository.reset_draft_payroll(payroll_id, salary_config.id)
        else:
            payroll_id = self.payroll_repository.create_payroll_draft(user_id, salary_config.id, context.month, context.year)

        base_amount = salary_config.base_salary
        self.payroll_repository.insert_payroll_item(self.calc_service.build_base_item(payroll_id, base_amount))

        teaching_amount = Decimal("0")
        if salary_config.salary_type in (2, 4):
            teaching_count = self.payroll_activity_repository.count_completed_sessions(user_id, context.start_date, context.end_date)
            teaching_amount, teaching_item = self.calc_service.calculate_teaching_amount(salary_config, teaching_count)
            if teaching_item is not None:
                self.payroll_repository.insert_payroll_item(self._with_payroll_id(teaching_item, payroll_id))

        kpi_amount = Decimal("0")
        if salary_config.salary_type in (3, 4):
            staff_id = self.payroll_user_repository.get_staff_id_by_user_id(user_id)
            if staff_id is not None:
                kpi = self.payroll_activity_repository.get_sales_kpi_totals(staff_id, context.month, context.year)
                kpi_amount, kpi_item = self.calc_service.calculate_kpi_amount(salary_config, kpi)
                if kpi_item is not None:
                    self.payroll_repository.insert_payroll_item(self._with_payroll_id(kpi_item, payroll_id))

        amounts = self.calc_service.calculate_payroll_amounts(
            base_amount=base_amount,
            teaching_amount=teaching_amount,
            kpi_amount=kpi_amount,
        )
        self.payroll_repository.update_payroll_amounts(payroll_id, amounts)
        self._send_payroll_email(user_id, context.month, context.year, amounts)
        return PayrollProcessResult(status="created", payroll_id=payroll_id)

    @staticmethod
    def _with_payroll_id(item: PayrollItem, payroll_id: int) -> PayrollItem:
        return PayrollItem(
            payroll_id=payroll_id,
            item_type=item.item_type,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=item.amount,
            description=item.description,
        )

    def _send_payroll_email(self, user_id: int, month: int, year: int, amounts: PayrollAmounts):
        contact = self.payroll_user_repository.get_user_contact(user_id)
        if contact is None or not contact.email:
            return
        self.email_service.send_payroll_generated(
            to_email=contact.email,
            full_name=contact.full_name or "User",
            month=month,
            year=year,
            base_amount=self._format_vnd(amounts.base_amount),
            teaching_amount=self._format_vnd(amounts.teaching_amount),
            kpi_amount=self._format_vnd(amounts.kpi_amount),
            gross_amount=self._format_vnd(amounts.gross_amount),
            net_amount=self._format_vnd(amounts.net_amount),
        )

    @staticmethod
    def _format_vnd(amount: Decimal) -> str:
        rounded = int(amount.quantize(Decimal("1")))
        sign = "-" if rounded < 0 else ""
        number = f"{abs(rounded):,}".replace(",", ".")
        return f"{sign}{number} VND"
