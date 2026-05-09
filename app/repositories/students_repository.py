from app.infrastructure.db import db_cursor
from app.models.student_model import Student


class StudentsRepository:
    def __init__(self, connection):
        self.connection = connection

    def find_without_user(self) -> list[Student]:
        query = """
            SELECT s.id, s.student_code
            FROM students s
            WHERE s.user_id IS NULL
            ORDER BY s.id ASC
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [
                Student(
                    id=int(row["id"]),
                    student_code=row.get("student_code") or f"STD0000{int(row['id'])}",
                )
                for row in rows
            ]

    def link_to_user(self, student_id: int, user_id: int):
        with db_cursor(self.connection) as cursor:
            cursor.execute("UPDATE students SET user_id = %s WHERE id = %s", (user_id, student_id))
