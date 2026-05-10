import xml.etree.ElementTree as ET
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO


class BaseExcelParserService(ABC):
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    def parse_rows(self, file_bytes: bytes):
        rows_data = []
        skip_cols = {c.upper() for c in self.skip_columns()}
        with zipfile.ZipFile(BytesIO(file_bytes), "r") as archive:
            shared_strings = self._read_shared_strings(archive)
            sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            rows = sheet_root.findall(".//a:sheetData/a:row", self.ns)

            for row in rows:
                row_index = int(row.attrib.get("r", "0"))
                if row_index < self.start_row():
                    continue

                col_map = {}
                for cell in row.findall("a:c", self.ns):
                    cell_ref = cell.attrib.get("r", "")
                    col = self._extract_column(cell_ref)
                    if not self._is_in_range(col):
                        continue
                    if col.upper() in skip_cols:
                        continue
                    col_map[col] = self._read_cell_value(cell, shared_strings)

                rows_data.append(self.map_row(row_index, col_map))

        return rows_data

    @abstractmethod
    def start_row(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def column_start(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def column_end(self) -> str:
        raise NotImplementedError

    def skip_columns(self) -> list[str] | tuple[str, ...] | set[str]:
        return []

    @abstractmethod
    def map_row(self, row_index: int, col_map: dict[str, str | None]):
        raise NotImplementedError

    def _is_in_range(self, col: str) -> bool:
        idx = self._column_to_index(col)
        return self._column_to_index(self.column_start()) <= idx <= self._column_to_index(self.column_end())

    @staticmethod
    def _column_to_index(col: str) -> int:
        result = 0
        for ch in col.upper():
            result = result * 26 + (ord(ch) - ord("A") + 1)
        return result

    @staticmethod
    def _extract_column(cell_ref: str) -> str:
        letters = []
        for ch in cell_ref:
            if ch.isalpha():
                letters.append(ch)
            else:
                break
        return "".join(letters)

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared_strings = []
        for si in root.findall("a:si", self.ns):
            texts = [t.text or "" for t in si.findall(".//a:t", self.ns)]
            shared_strings.append("".join(texts))
        return shared_strings

    def _read_cell_value(self, cell, shared_strings: list[str]):
        cell_type = cell.attrib.get("t")
        value_node = cell.find("a:v", self.ns)
        if cell_type == "inlineStr":
            inline_text_nodes = cell.findall(".//a:is//a:t", self.ns)
            if inline_text_nodes:
                return "".join((node.text or "") for node in inline_text_nodes)
            return None

        if value_node is not None:
            raw = value_node.text
            if cell_type == "s" and raw is not None:
                try:
                    return shared_strings[int(raw)]
                except (ValueError, IndexError):
                    return raw
            return raw

        text_node = cell.find(".//a:t", self.ns)
        if text_node is not None:
            return text_node.text
        return None
