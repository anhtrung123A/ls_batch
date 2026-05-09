import json
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from io import BytesIO

import boto3
from botocore.config import Config

from app.constants.jobs import JOB_CREATE_LEADS_FROM_EXCEL
from app.infrastructure.config import Settings
from app.jobs.base_batch_job import BaseBatchJob
from app.models.batch_models import JobStats
from app.repositories.leads_repository import LeadsRepository


@dataclass
class LeadRow:
    row_number: int
    full_name: str | None
    phone: str | None
    email: str | None
    source_id: str | None
    campaign: str | None
    interest: str | None
    note: str | None


class CreateLeadsFromExcelJob(BaseBatchJob):
    """
    How to run this job:
    - Local/manual: `python scripts/run_job.py create_leads_from_excel --trigger manual`
    - In Docker container and also write logs to `docker logs`:
      `docker exec batch sh -lc "cd /app && /usr/local/bin/python3 scripts/run_job.py create_leads_from_excel --trigger manual >> /proc/1/fd/1 2>> /proc/1/fd/2"`
    """

    JOB_NAME = JOB_CREATE_LEADS_FROM_EXCEL

    def __init__(self, connection, settings: Settings, lock_owner: str = "batch-container"):
        super().__init__(connection=connection, job_name=self.JOB_NAME, lock_owner=lock_owner)
        self.settings = settings
        self.leads_repository = LeadsRepository(connection)
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )

    def process(self, execution_id: int) -> JobStats:
        stats = JobStats()
        failure_details: list[dict] = []
        existing_phone_set = {self._normalize_phone(p) for p in self.leads_repository.get_all_phones() if self._normalize_phone(p)}

        object_keys = self._list_excel_files()
        self.logger.info("Found %s excel files in s3://%s/%s", len(object_keys), self.settings.s3_bucket, self.settings.s3_leads_prefix)

        for key in object_keys:
            try:
                data = self.s3.get_object(Bucket=self.settings.s3_bucket, Key=key)["Body"].read()
                rows = self._parse_excel_rows(data)
                file_success = 0
                file_failed = 0
                file_skipped = 0

                for row in rows:
                    row_data = {
                        "full_name": row.full_name,
                        "phone": row.phone,
                        "email": row.email,
                        "source_id": row.source_id,
                        "campaign": row.campaign,
                        "interest": row.interest,
                        "note": row.note,
                    }
                    self.logger.info(
                        json.dumps(
                            {
                                "file": key,
                                "row": row.row_number,
                                "data": row_data,
                            },
                            ensure_ascii=False,
                        )
                    )

                    try:
                        reason = self._validate_row(row)
                        if reason:
                            file_skipped += 1
                            stats.skipped += 1
                            failure_details.append({"file": key, "row": row.row_number, "reason": reason})
                            continue

                        normalized_phone = self._normalize_phone(row.phone)
                        if normalized_phone and normalized_phone in existing_phone_set:
                            file_skipped += 1
                            stats.skipped += 1
                            failure_details.append(
                                {"file": key, "row": row.row_number, "reason": f"Duplicate phone: {row.phone}"}
                            )
                            continue

                        source_value = self._parse_source(row.source_id)
                        lead_id = self.leads_repository.create_lead(
                            full_name=row.full_name.strip(),
                            phone=row.phone.strip() if row.phone else None,
                            email=row.email.strip().lower() if row.email else None,
                            source=source_value,
                            campaign=row.campaign,
                            interest=row.interest,
                            note=row.note,
                        )
                        self.connection.commit()
                        if normalized_phone:
                            existing_phone_set.add(normalized_phone)

                        file_success += 1
                        stats.created += 1
                        self.logger.info(
                            json.dumps(
                                {"file": key, "row": row.row_number, "lead_id": lead_id, "status": "created"},
                                ensure_ascii=False,
                            )
                        )
                    except Exception as row_ex:
                        self.connection.rollback()
                        file_failed += 1
                        stats.failed += 1
                        failure_details.append({"file": key, "row": row.row_number, "reason": str(row_ex)})

                if file_failed == 0:
                    self.mark_item_success(execution_id, "s3_object", 0)
                else:
                    self.mark_item_failed(execution_id, "s3_object", 0, f"{key}: failed_rows={file_failed}")
                self.connection.commit()
                self.logger.info(
                    "File summary file=%s success=%s skipped=%s failed=%s",
                    key,
                    file_success,
                    file_skipped,
                    file_failed,
                )
            except Exception as ex:
                self.connection.rollback()
                self.mark_item_failed(execution_id, "s3_object", 0, f"{key}: {ex}")
                self.connection.commit()
                stats.failed += 1
                failure_details.append({"file": key, "row": None, "reason": str(ex)})
                self.logger.exception("Failed processing file: %s", key)

        self.logger.info(
            json.dumps(
                {
                    "summary": {
                        "created": stats.created,
                        "skipped": stats.skipped,
                        "failed": stats.failed,
                    },
                    "failed_details": failure_details,
                },
                ensure_ascii=False,
            )
        )
        return stats

    def _list_excel_files(self) -> list[str]:
        keys: list[str] = []
        continuation_token = None

        while True:
            kwargs = {
                "Bucket": self.settings.s3_bucket,
                "Prefix": self.settings.s3_leads_prefix,
                "MaxKeys": 1000,
            }
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = self.s3.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                key = item.get("Key", "")
                if key.lower().endswith(".xlsx") and not key.endswith("/"):
                    keys.append(key)

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")

        return keys

    def _parse_excel_rows(self, file_bytes: bytes) -> list[LeadRow]:
        ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows_data: list[LeadRow] = []

        with zipfile.ZipFile(BytesIO(file_bytes), "r") as archive:
            shared_strings = self._read_shared_strings(archive, ns)
            sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            rows = sheet_root.findall(".//a:sheetData/a:row", ns)

            for row in rows:
                row_index = int(row.attrib.get("r", "0"))
                if row_index < 3:
                    continue

                col_map = {}
                for cell in row.findall("a:c", ns):
                    cell_ref = cell.attrib.get("r", "")
                    col = self._extract_column(cell_ref)
                    col_map[col] = self._read_cell_value(cell, shared_strings, ns)

                rows_data.append(
                    LeadRow(
                        row_number=row_index,
                        full_name=col_map.get("A"),
                        phone=col_map.get("B"),
                        email=col_map.get("C"),
                        source_id=col_map.get("D"),
                        campaign=col_map.get("F"),
                        interest=col_map.get("G"),
                        note=col_map.get("H"),
                    )
                )

        return rows_data

    @staticmethod
    def _read_shared_strings(archive: zipfile.ZipFile, ns: dict) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []

        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared_strings = []
        for si in root.findall("a:si", ns):
            texts = [t.text or "" for t in si.findall(".//a:t", ns)]
            shared_strings.append("".join(texts))
        return shared_strings

    @staticmethod
    def _read_cell_value(cell, shared_strings: list[str], ns: dict):
        cell_type = cell.attrib.get("t")
        value_node = cell.find("a:v", ns)
        if value_node is None:
            return None

        raw = value_node.text
        if cell_type == "s" and raw is not None:
            try:
                return shared_strings[int(raw)]
            except (ValueError, IndexError):
                return raw
        return raw

    @staticmethod
    def _extract_column(cell_ref: str) -> str:
        letters = []
        for ch in cell_ref:
            if ch.isalpha():
                letters.append(ch)
            else:
                break
        return "".join(letters)

    @staticmethod
    def _normalize_phone(phone: str | None) -> str | None:
        if phone is None:
            return None
        value = "".join(ch for ch in str(phone).strip() if ch.isdigit())
        return value or None

    @staticmethod
    def _parse_source(source_id: str | None) -> int | None:
        if source_id is None or str(source_id).strip() == "":
            return None
        value = int(str(source_id).strip())
        if value < 1 or value > 5:
            raise ValueError(f"Invalid source_id: {source_id}")
        return value

    @staticmethod
    def _validate_row(row: LeadRow) -> str | None:
        if row.full_name is None or row.full_name.strip() == "":
            return "Full name is required."
        return None
