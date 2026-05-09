from app.infrastructure.db import db_cursor
from app.models.lead_model import Lead


class LeadsRepository:
    def __init__(self, connection):
        self.connection = connection

    def find_by_converted_student_id(self, student_id: int) -> Lead | None:
        query = """
            SELECT id, full_name, phone, email
            FROM leads
            WHERE converted_to = %s
            LIMIT 1
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (student_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Lead(
                id=int(row["id"]),
                full_name=(row.get("full_name") or "").strip(),
                phone=(row.get("phone") or None),
                email=(row.get("email") or None),
            )
