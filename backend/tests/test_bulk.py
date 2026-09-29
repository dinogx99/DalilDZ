import io

from openpyxl import Workbook
import pytest

from app.services.bulk import parse_bulk_file


def test_xlsx_bulk_import():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["company_name", "rc", "nif", "website", "wilaya"])
    sheet.append(["SYNTHETIC XLSX COMPANY", "16B1234567", "", "", "Oran"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    rows = parse_bulk_file(buffer.getvalue())
    assert rows[0]["company_name"] == "SYNTHETIC XLSX COMPANY"
    assert rows[0]["rc"] == "16B1234567"


def test_bulk_row_limit():
    rows = ["company_name,rc"] + [f"SYNTHETIC {i},16B{i:07d}" for i in range(4)]
    with pytest.raises(ValueError, match="BULK_ROW_LIMIT_EXCEEDED"):
        parse_bulk_file("\n".join(rows).encode(), max_rows=2)
