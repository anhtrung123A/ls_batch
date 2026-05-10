"""
How to run this job:
- Local/manual: `python scripts/run_job.py create_leads_from_excel --trigger manual`
- In Docker container and also write logs to `docker logs`:
  `docker exec batch sh -lc "cd /app && /usr/local/bin/python3 scripts/run_job.py create_leads_from_excel --trigger manual >> /proc/1/fd/1 2>> /proc/1/fd/2"`
"""

import json

from app.constants.jobs import JOB_CREATE_LEADS_FROM_EXCEL
from app.infrastructure.config import Settings
from app.infrastructure.minio_client import MinioClient
from app.jobs.base_batch_job import BaseBatchJob
from app.models.batch_models import JobStats
from app.models.lead_import_model import LeadImportFailure
from app.repositories.leads_repository import LeadsRepository
from app.services.excel_lead_parser_service import ExcelLeadParserService
from app.services.lead_import_service import LeadImportService


class CreateLeadsFromExcelJob(BaseBatchJob):
    JOB_NAME = JOB_CREATE_LEADS_FROM_EXCEL

    def __init__(self, connection, settings: Settings, lock_owner: str = "batch-container"):
        super().__init__(connection=connection, job_name=self.JOB_NAME, lock_owner=lock_owner)
        self.settings = settings
        self.minio_client = MinioClient(settings)
        self.parser_service = ExcelLeadParserService()
        self.import_service = LeadImportService(LeadsRepository(connection))

    def process(self, execution_id: int) -> JobStats:
        stats = JobStats()
        all_failures: list[LeadImportFailure] = []

        object_keys = self.minio_client.list_excel_keys()
        self.logger.info("Found %s excel files in s3://%s/%s", len(object_keys), self.settings.s3_bucket, self.settings.s3_leads_prefix)

        for key in object_keys:
            try:
                data = self.minio_client.read_object_bytes(key)
                rows = self.parser_service.parse_rows(data)
                result = self.import_service.import_rows(key, rows)
                self.connection.commit()

                stats.created += result.success
                stats.skipped += result.skipped
                stats.failed += result.failed
                all_failures.extend(result.failures)

                if result.failed == 0:
                    self.mark_item_success(execution_id, "s3_object", 0)
                else:
                    self.mark_item_failed(execution_id, "s3_object", 0, f"{key}: failed_rows={result.failed}")
                self.connection.commit()

                self.logger.info("File summary file=%s success=%s skipped=%s failed=%s", key, result.success, result.skipped, result.failed)
            except Exception as ex:
                self.connection.rollback()
                self.mark_item_failed(execution_id, "s3_object", 0, f"{key}: {ex}")
                self.connection.commit()
                stats.failed += 1
                all_failures.append(LeadImportFailure(file=key, row=None, reason=str(ex)))
                self.logger.exception("Failed processing file: %s", key)

        self.logger.info(
            json.dumps(
                {
                    "summary": {"created": stats.created, "skipped": stats.skipped, "failed": stats.failed},
                    "failed_details": [{"file": f.file, "row": f.row, "reason": f.reason} for f in all_failures],
                },
                ensure_ascii=False,
            )
        )
        return stats
