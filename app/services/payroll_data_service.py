import calendar
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.infrastructure.db import db_cursor
from app.models.payroll_item_model import PayrollItem
from app.models.payroll_model import Payroll, PayrollAmounts
from app.models.salary_config_model import SalaryConfig
from app.models.staff_kpi_record_model import StaffKpiAggregate
from app.models.user_model import PayrollUser, PayrollUserContact


@dataclass(frozen=True)
class PayrollContext:
    month: int
    year: int
    start_date: date
    end_date: date


class PayrollDataService:
    def __init__(self, connection):
        self.connection = connection

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

    def get_active_payroll_users(self) -> list[PayrollUser]:
        query = """
            SELECT id, role
            FROM users
            WHERE is_active = 1
              AND role IN (2, 3)
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [PayrollUser(id=int(r["id"]), role=int(r["role"])) for r in rows]

    def get_user_contact(self, user_id: int) -> PayrollUserContact | None:
        query = "SELECT full_name, email FROM users WHERE id = %s LIMIT 1"
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return PayrollUserContact(full_name=row.get("full_name"), email=row.get("email"))

    def get_active_salary_config(self, user_id: int, start_date: date, end_date: date) -> SalaryConfig | None:
        query = """
            SELECT id, salary_type, base_salary, teaching_rate, converted_lead_rate
            FROM salary_configs
            WHERE user_id = %s
              AND is_active = 1
              AND effective_from <= %s
              AND (effective_to IS NULL OR effective_to >= %s)
            ORDER BY effective_from DESC, id DESC
            LIMIT 1
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (user_id, end_date, start_date))
            row = cursor.fetchone()
            if not row:
                return None
            return SalaryConfig(
                id=int(row["id"]),
                salary_type=int(row["salary_type"]),
                base_salary=Decimal(str(row.get("base_salary") or 0)),
                teaching_rate=Decimal(str(row.get("teaching_rate") or 0)),
                converted_lead_rate=Decimal(str(row.get("converted_lead_rate") or 0)),
            )

    def get_existing_payroll(self, user_id: int, month: int, year: int) -> Payroll | None:
        with db_cursor(self.connection) as cursor:
            cursor.execute(
                "SELECT id, status FROM payrolls WHERE user_id = %s AND month = %s AND year = %s LIMIT 1",
                (user_id, month, year),
            )
            row = cursor.fetchone()
            return Payroll(id=int(row["id"]), status=int(row["status"])) if row else None

    def reset_draft_payroll(self, payroll_id: int, salary_config_id: int):
        with db_cursor(self.connection) as cursor:
            cursor.execute("DELETE FROM payroll_items WHERE payroll_id = %s", (payroll_id,))
            cursor.execute(
                """
                UPDATE payrolls
                SET salary_config_id = %s,
                    base_amount = 0,
                    teaching_amount = 0,
                    kpi_amount = 0,
                    bonus_amount = 0,
                    deduction_amount = 0,
                    gross_amount = 0,
                    net_amount = 0,
                    updated_at = UTC_TIMESTAMP()
                WHERE id = %s
                """,
                (salary_config_id, payroll_id),
            )

    def create_payroll_draft(self, user_id: int, salary_config_id: int, month: int, year: int) -> int:
        query = """
            INSERT INTO payrolls
                (user_id, salary_config_id, month, year, status, generated_at, created_at, updated_at)
            VALUES
                (%s, %s, %s, %s, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP(), UTC_TIMESTAMP())
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (user_id, salary_config_id, month, year))
            return int(cursor.lastrowid)

    def count_completed_sessions(self, teacher_user_id: int, start_date: date, end_date: date) -> int:
        query = """
            SELECT COUNT(1) AS total
            FROM class_sessions
            WHERE teacher_id = %s
              AND status = 3
              AND session_date >= %s
              AND session_date <= %s
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (teacher_user_id, start_date, end_date))
            row = cursor.fetchone()
            return int(row["total"] or 0)

    def get_staff_id_by_user_id(self, user_id: int) -> int | None:
        with db_cursor(self.connection) as cursor:
            cursor.execute("SELECT id FROM staff WHERE user_id = %s LIMIT 1", (user_id,))
            row = cursor.fetchone()
            return int(row["id"]) if row else None

    def get_sales_kpi_totals(self, staff_id: int, month: int, year: int) -> StaffKpiAggregate:
        query = """
            SELECT
                COALESCE(SUM(quantity), 0) AS total_qty,
                COALESCE(SUM(total_amount), 0) AS total_amount,
                COALESCE(SUM(quantity * unit_amount), 0) AS qty_unit_amount
            FROM staff_kpi_records
            WHERE staff_id = %s
              AND month = %s
              AND year = %s
              AND type = 1
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (staff_id, month, year))
            row = cursor.fetchone()
            quantity = int(row["total_qty"] or 0)
            total_amount = Decimal(str(row["total_amount"] or 0))
            if total_amount <= 0:
                total_amount = Decimal(str(row["qty_unit_amount"] or 0))
            return StaffKpiAggregate(quantity=quantity, total_amount=total_amount)

    def update_payroll_amounts(self, payroll_id: int, amounts: PayrollAmounts):
        query = """
            UPDATE payrolls
            SET base_amount = %s,
                teaching_amount = %s,
                kpi_amount = %s,
                bonus_amount = %s,
                deduction_amount = %s,
                gross_amount = %s,
                net_amount = %s,
                updated_at = UTC_TIMESTAMP()
            WHERE id = %s
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(
                query,
                (
                    amounts.base_amount,
                    amounts.teaching_amount,
                    amounts.kpi_amount,
                    amounts.bonus_amount,
                    amounts.deduction_amount,
                    amounts.gross_amount,
                    amounts.net_amount,
                    payroll_id,
                ),
            )

    def insert_payroll_item(self, item: PayrollItem):
        query = """
            INSERT INTO payroll_items
                (payroll_id, type, quantity, unit_amount, amount, description, created_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(
                query,
                (item.payroll_id, item.item_type, item.quantity, item.unit_amount, item.amount, item.description),
            )
