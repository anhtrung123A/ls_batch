from app.models.lead_import_model import LeadImportFailure, LeadImportFileResult, LeadImportRow
from app.repositories.leads_repository import LeadsRepository


class LeadImportService:
    def __init__(self, leads_repository: LeadsRepository):
        self.leads_repository = leads_repository
        self._existing_phone_set = {
            self._normalize_phone(p)
            for p in self.leads_repository.get_all_phones()
            if self._normalize_phone(p)
        }

    def import_rows(self, file_key: str, rows: list[LeadImportRow]) -> LeadImportFileResult:
        success = 0
        skipped = 0
        failed = 0
        failures: list[LeadImportFailure] = []

        for row in rows:
            reason = self._validate_row(row)
            if reason:
                skipped += 1
                failures.append(LeadImportFailure(file=file_key, row=row.row_number, reason=reason))
                continue

            normalized_phone = self._normalize_phone(row.phone)
            if normalized_phone and normalized_phone in self._existing_phone_set:
                skipped += 1
                failures.append(LeadImportFailure(file=file_key, row=row.row_number, reason=f"Duplicate phone: {row.phone}"))
                continue

            try:
                source_value = self._parse_source(row.source_id)
                self.leads_repository.create_lead(
                    full_name=row.full_name.strip(),
                    phone=row.phone.strip() if row.phone else None,
                    email=row.email.strip().lower() if row.email else None,
                    source=source_value,
                    campaign=row.campaign,
                    interest=row.interest,
                    note=row.note,
                )
                if normalized_phone:
                    self._existing_phone_set.add(normalized_phone)
                success += 1
            except Exception as ex:
                failed += 1
                failures.append(LeadImportFailure(file=file_key, row=row.row_number, reason=str(ex)))

        return LeadImportFileResult(success=success, skipped=skipped, failed=failed, failures=failures)

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
    def _validate_row(row: LeadImportRow) -> str | None:
        if row.full_name is None or row.full_name.strip() == "":
            return "Full name is required."
        return None
