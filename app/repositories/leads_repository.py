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

    def get_all_phones(self) -> list[str]:
        with db_cursor(self.connection) as cursor:
            cursor.execute("SELECT phone FROM leads WHERE phone IS NOT NULL AND TRIM(phone) <> ''")
            rows = cursor.fetchall()
            return [str(row["phone"]) for row in rows if row.get("phone") is not None]

    def create_lead(
        self,
        full_name: str,
        phone: str | None,
        email: str | None,
        source: int | None,
        campaign: str | None,
        interest: str | None,
        note: str | None,
    ) -> int:
        query = """
            INSERT INTO leads
                (full_name, phone, email, source, campaign, interest, status, note, updated_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, 1, %s, UTC_TIMESTAMP())
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(
                query,
                (
                    full_name.strip(),
                    phone.strip() if phone else None,
                    email.strip().lower() if email else None,
                    source,
                    campaign.strip() if campaign else None,
                    interest.strip() if interest else None,
                    note.strip() if note else None,
                ),
            )
            return int(cursor.lastrowid)
