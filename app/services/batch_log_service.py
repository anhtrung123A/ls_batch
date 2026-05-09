from datetime import datetime

from app.infrastructure.db import db_cursor


class BatchLogService:
    RUNNING = 1
    SUCCESS = 2
    FAILED = 3
    SKIPPED = 4

    ITEM_SUCCESS = 1
    ITEM_FAILED = 2
    ITEM_SKIPPED = 3

    def __init__(self, connection):
        self.connection = connection

    def start_execution(self, job_name: str, triggered_by: int = 2) -> int:
        query = """
            INSERT INTO batch_job_executions (job_name, status, triggered_by, started_at, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW(), NOW())
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (job_name, self.RUNNING, triggered_by))
            return cursor.lastrowid

    def create_skipped_execution(self, job_name: str, triggered_by: int, error_message: str) -> int:
        query = """
            INSERT INTO batch_job_executions
                (job_name, status, triggered_by, started_at, finished_at, duration_ms, error_message, created_at, updated_at)
            VALUES
                (%s, %s, %s, NOW(), NOW(), 0, %s, NOW(), NOW())
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (job_name, self.SKIPPED, triggered_by, error_message))
            return cursor.lastrowid

    def finish_execution(
        self,
        execution_id: int,
        status: int,
        started_at: datetime,
        error_message: str | None = None,
        error_trace: str | None = None,
    ):
        duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        query = """
            UPDATE batch_job_executions
            SET status = %s,
                finished_at = NOW(),
                duration_ms = %s,
                error_message = %s,
                error_trace = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (status, duration_ms, error_message, error_trace, execution_id))

    def log_item(self, execution_id: int, target_type: str, target_id: int, status: int, error_message: str | None = None):
        query = """
            INSERT INTO batch_job_items (execution_id, target_type, target_id, status, error_message, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """
        with db_cursor(self.connection) as cursor:
            cursor.execute(query, (execution_id, target_type, target_id, status, error_message))
