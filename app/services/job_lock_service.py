from app.infrastructure.db import db_cursor


class JobLockService:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self, job_name: str, lock_owner: str, ttl_minutes: int = 15) -> bool:
        query = """
            INSERT INTO batch_job_locks (job_name, locked_at, locked_by, expires_at, created_at, updated_at)
            VALUES (%s, NOW(), %s, DATE_ADD(NOW(), INTERVAL %s MINUTE), NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                locked_at = IF(expires_at < NOW(), VALUES(locked_at), locked_at),
                locked_by = IF(expires_at < NOW(), VALUES(locked_by), locked_by),
                expires_at = IF(expires_at < NOW(), VALUES(expires_at), expires_at),
                updated_at = NOW()
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (job_name, lock_owner, ttl_minutes))

        with db_cursor(self.connection) as cursor:
            cursor.execute(
                "SELECT locked_by, expires_at >= NOW() AS active FROM batch_job_locks WHERE job_name = %s",
                (job_name,),
            )
            row = cursor.fetchone()
            return bool(row and row["active"] and row["locked_by"] == lock_owner)

    def release(self, job_name: str, lock_owner: str | None = None):
        with db_cursor(self.connection) as cursor:
            if lock_owner:
                cursor.execute("DELETE FROM batch_job_locks WHERE job_name = %s AND locked_by = %s", (job_name, lock_owner))
            else:
                cursor.execute("DELETE FROM batch_job_locks WHERE job_name = %s", (job_name,))
