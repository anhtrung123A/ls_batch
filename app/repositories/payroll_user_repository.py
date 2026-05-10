from app.infrastructure.db import db_cursor
from app.models.user_model import PayrollUser, PayrollUserContact


class PayrollUserRepository:
    def __init__(self, connection):
        self.connection = connection

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

    def get_staff_id_by_user_id(self, user_id: int) -> int | None:
        with db_cursor(self.connection) as cursor:
            cursor.execute("SELECT id FROM staff WHERE user_id = %s LIMIT 1", (user_id,))
            row = cursor.fetchone()
            return int(row["id"]) if row else None
