from datetime import date
from decimal import Decimal

from app.infrastructure.db import db_cursor
from app.models.salary_config_model import SalaryConfig


class SalaryConfigRepository:
    def __init__(self, connection):
        self.connection = connection

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
