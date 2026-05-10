from dataclasses import dataclass


@dataclass(frozen=True)
class LeadImportRow:
    row_number: int
    full_name: str | None
    phone: str | None
    email: str | None
    source_id: str | None
    campaign: str | None
    interest: str | None
    note: str | None


@dataclass(frozen=True)
class LeadImportFailure:
    file: str
    row: int | None
    reason: str


@dataclass(frozen=True)
class LeadImportFileResult:
    success: int
    skipped: int
    failed: int
    failures: list[LeadImportFailure]
