from datetime import date
from decimal import Decimal

from app.infrastructure.db import db_cursor
from app.models.staff_kpi_record_model import StaffKpiAggregate


class PayrollActivityRepository:
    def __init__(self, connection):
        self.connection = connection

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
