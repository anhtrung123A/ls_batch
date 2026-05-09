from app.infrastructure.db import db_cursor
from app.models.user_model import UserCreateInput


class UsersRepository:
    def __init__(self, connection):
        self.connection = connection

    def is_email_exists(self, email: str) -> bool:
        with db_cursor(self.connection) as cursor:
            cursor.execute("SELECT 1 FROM users WHERE email = %s LIMIT 1", (email,))
            return cursor.fetchone() is not None

    def create(self, payload: UserCreateInput) -> int:
        query = """
            INSERT INTO users (full_name, email, phone, role, password_hash, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, 4, %s, 1, NOW(), NOW())
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(
                query,
                (payload.full_name, payload.email, payload.phone, payload.password_hash),
            )
            return int(cursor.lastrowid)
