"""
How to run this job:
- Local/manual: `python scripts/run_job.py generate_monthly_payroll --trigger manual`
- Local/manual with custom month/year: `PAYROLL_MONTH=4 PAYROLL_YEAR=2026 python scripts/run_job.py generate_monthly_payroll --trigger manual`
- In Docker container and also write logs to `docker logs`:
  `docker exec batch sh -lc "cd /app && PAYROLL_MONTH=4 PAYROLL_YEAR=2026 /usr/local/bin/python3 scripts/run_job.py generate_monthly_payroll --trigger manual >> /proc/1/fd/1 2>> /proc/1/fd/2"`
"""

import json

from app.constants.jobs import JOB_GENERATE_MONTHLY_PAYROLL
from app.jobs.base_batch_job import BaseBatchJob
from app.models.batch_models import JobStats
from app.services.email_service import EmailService
from app.services.payroll_generation_service import PayrollGenerationService


class GenerateMonthlyPayrollJob(BaseBatchJob):
    JOB_NAME = JOB_GENERATE_MONTHLY_PAYROLL

    def __init__(self, connection, email_service: EmailService, lock_owner: str = "batch-container"):
        super().__init__(connection=connection, job_name=self.JOB_NAME, lock_owner=lock_owner)
        self.service = PayrollGenerationService(connection, email_service)

    def process(self, execution_id: int) -> JobStats:
        stats = JobStats()
        failures: list[dict] = []
        context = self.service.resolve_payroll_context()
        users = self.service.get_active_users()

        self.logger.info("Generating payroll for month=%s year=%s users=%s", context.month, context.year, len(users))

        for user in users:
            try:
                result = self.service.process_user(user.id, context)
                if result.status == "skipped":
                    stats.skipped += 1
                    self.mark_item_skipped(execution_id, "payroll_user", user.id, result.reason or "Skipped.")
                else:
                    stats.created += 1
                    self.mark_item_success(execution_id, "payroll", result.payroll_id or 0)
                self.connection.commit()
            except Exception as ex:
                self.connection.rollback()
                self.mark_item_failed(execution_id, "payroll_user", user.id, str(ex))
                self.connection.commit()
                stats.failed += 1
                failures.append({"user_id": user.id, "reason": str(ex)})
                self.logger.exception("Failed generate payroll for user_id=%s", user.id)

        self.logger.info(
            json.dumps(
                {
                    "month": context.month,
                    "year": context.year,
                    "summary": {"created": stats.created, "skipped": stats.skipped, "failed": stats.failed},
                    "failure_details": failures,
                },
                ensure_ascii=False,
            )
        )
        return stats
