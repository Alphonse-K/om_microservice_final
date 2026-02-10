import csv
from io import StringIO
from openpyxl import Workbook
from io import BytesIO



def export_csv_from_dicts(rows, columns):
    buffer = StringIO()
    writer = csv.writer(buffer)

    # Headers
    writer.writerow([col[0] for col in columns])

    for row in rows:
        writer.writerow(
            [row[col[1]] for col in columns]
        )
    
    buffer.seek(0)
    return buffer

def export_excel_from_dicts(rows: list[dict], columns: list, sheet_name: str):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Header
    ws.append([col[0] for col in columns])

    # Rows
    for row in rows:
        ws.append([row[col[1]] for col in columns])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
