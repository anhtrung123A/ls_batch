from app.models.lead_import_model import LeadImportRow
from app.services.base_excel_parser_service import BaseExcelParserService


class ExcelLeadParserService(BaseExcelParserService):
    def start_row(self) -> int:
        return 3

    def column_start(self) -> str:
        return "A"

    def column_end(self) -> str:
        return "H"

    def skip_columns(self) -> set[str]:
        return {"E"}

    def map_row(self, row_index: int, col_map: dict[str, str | None]) -> LeadImportRow:
        return LeadImportRow(
            row_number=row_index,
            full_name=col_map.get("A"),
            phone=col_map.get("B"),
            email=col_map.get("C"),
            source_id=col_map.get("D"),
            campaign=col_map.get("F"),
            interest=col_map.get("G"),
            note=col_map.get("H"),
        )
