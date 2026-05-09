import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime

from app.models.batch_models import JobStats
from app.services.batch_log_service import BatchLogService
from app.services.job_lock_service import JobLockService


class BaseBatchJob(ABC):
    triggered_by = 2
    lock_ttl_minutes = 15

    def __init__(self, connection, job_name: str, lock_owner: str = "batch-container"):
        self.connection = connection
        self.job_name = job_name
        self.lock_owner = lock_owner
        self.batch_log = BatchLogService(connection)
        self.job_lock = JobLockService(connection)
        self.logger = logging.getLogger(f"batch.{job_name}")

    def run(self, triggered_by: int | None = None) -> JobStats:
        trigger = triggered_by if triggered_by is not None else self.triggered_by
        self.logger.info("Starting job")
        if not self.job_lock.acquire(self.job_name, self.lock_owner, ttl_minutes=self.lock_ttl_minutes):
            self.batch_log.create_skipped_execution(
                self.job_name,
                trigger,
                "Skipped because lock is active.",
            )
            self.connection.commit()
            self.logger.warning("Skipped because lock is active")
            return JobStats(skipped=1)

        started_at = datetime.utcnow()
        execution_id = self.batch_log.start_execution(self.job_name, triggered_by=trigger)

        try:
            stats = self.process(execution_id)
            status = BatchLogService.SUCCESS if stats.failed == 0 else BatchLogService.FAILED
            self.batch_log.finish_execution(execution_id, status, started_at)
            self.connection.commit()
            self.logger.info(
                "Job finished: created=%s skipped=%s failed=%s",
                stats.created,
                stats.skipped,
                stats.failed,
            )
            return stats
        except Exception as ex:
            self.connection.rollback()
            self.batch_log.finish_execution(
                execution_id,
                BatchLogService.FAILED,
                started_at,
                str(ex),
                traceback.format_exc(),
            )
            self.connection.commit()
            self.logger.exception("Job failed with unhandled exception")
            raise
        finally:
            self.job_lock.release(self.job_name)
            self.connection.commit()
            self.logger.info("Lock released")

    @abstractmethod
    def process(self, execution_id: int) -> JobStats:
        raise NotImplementedError

    def mark_item_success(self, execution_id: int, target_type: str, target_id: int):
        self.batch_log.log_item(execution_id, target_type, target_id, BatchLogService.ITEM_SUCCESS)

    def mark_item_skipped(self, execution_id: int, target_type: str, target_id: int, error_message: str):
        self.batch_log.log_item(execution_id, target_type, target_id, BatchLogService.ITEM_SKIPPED, error_message)

    def mark_item_failed(self, execution_id: int, target_type: str, target_id: int, error_message: str):
        self.batch_log.log_item(execution_id, target_type, target_id, BatchLogService.ITEM_FAILED, error_message)
