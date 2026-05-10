from app.infrastructure.db import db_cursor
from app.models.payroll_item_model import PayrollItem
from app.models.payroll_model import Payroll, PayrollAmounts


class PayrollRepository:
    def __init__(self, connection):
        self.connection = connection

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
