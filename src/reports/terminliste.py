"""Monatliche Terminlisten für die zuständigen Mitarbeitenden."""

import sqlite3
from datetime import date
from pathlib import Path
from urllib.parse import quote

from loguru import logger
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from pydantic import BaseModel

from shared_modules.config import Config
from shared_modules.month_period import get_month_period
from shared_modules.utils import ensure_dir


class Employee(BaseModel):
    """Mitarbeitende aus den Stammdaten, unabhängig vom Timesheet-Schalter."""

    emp_id: str
    first_name: str | None
    last_name: str | None


class ReportAppointment(BaseModel):
    """Fälliger Bericht mit der abgeleiteten Zuständigkeit."""

    report_id: str
    mandate_id: str
    due_date: date
    report_form: str | None
    status: str | None
    notes: str | None
    index_child: str | None
    service_type: str | None
    requester: str | None
    employee_id: str | None
    primary_count: int
    existing_mandate: str | None


_SQL = """
WITH primary_employees AS (
    SELECT mandate_id, MIN(employee_id) AS employee_id, COUNT(*) AS primary_count
    FROM relation_mandate_emp WHERE role='P' GROUP BY mandate_id
)
SELECT r.report_id, r.mandate_id, date(r.due_date) AS due_date,
    r.report_form, r.status, r.notes,
    m.last_name || ' ' || m.first_name AS index_child,
    st.code AS service_type, sr.name AS requester,
    p.employee_id, COALESCE(p.primary_count, 0) AS primary_count,
    m.mandate_id AS existing_mandate
FROM report r
LEFT JOIN v_mandate m ON m.mandate_id=r.mandate_id
LEFT JOIN service_types st ON st.service_type_id=m.service_type_id
LEFT JOIN service_requester sr ON sr.service_requester_id=m.service_requester_id
LEFT JOIN primary_employees p ON p.mandate_id=r.mandate_id
WHERE date(r.due_date) BETWEEN ? AND ?
    AND COALESCE(r.status, '') NOT IN ('erledigt', 'entfällt')
ORDER BY date(r.due_date), r.mandate_id, r.report_id
"""


def create_terminlisten(config: Config, reporting_month: str) -> list[Path]:
    """Erstellt je Mitarbeitenden eine Excel-Datei; unzuordenbare Termine nur melden."""
    period = get_month_period(reporting_month)
    month = period.start.strftime("%Y-%m")
    db_path = config.get_db_path()
    if not db_path.is_file():
        raise FileNotFoundError(f"SQLite-Datenbank fehlt: {db_path}. Zuerst import-master ausführen.")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        employees = [
            Employee.model_validate(dict(row))
            for row in conn.execute(
                "SELECT emp_id,first_name,last_name FROM employees ORDER BY last_name,first_name,emp_id"
            )
        ]
        appointments = [
            ReportAppointment.model_validate(dict(row))
            for row in conn.execute(_SQL, (period.start.date().isoformat(), period.end.date().isoformat()))
        ]
    grouped: dict[str, list[ReportAppointment]] = {employee.emp_id: [] for employee in employees}
    skipped = 0
    for appointment in appointments:
        reason = None
        if appointment.existing_mandate is None:
            reason = "Auftrag fehlt in den Stammdaten"
        elif appointment.primary_count == 0:
            reason = "keine Person mit Rolle P"
        elif appointment.primary_count > 1:
            reason = "mehrere Personen mit Rolle P"
        elif appointment.employee_id not in grouped:
            reason = "Person mit Rolle P fehlt in den Mitarbeiter-Stammdaten"
        if reason:
            logger.warning(
                "Terminliste: Bericht {} / Auftrag {} ausgelassen: {}",
                appointment.report_id,
                appointment.mandate_id,
                reason,
            )
            skipped += 1
            continue
        assert appointment.employee_id is not None
        grouped[appointment.employee_id].append(appointment)

    output = ensure_dir(config.get_output_path() / f"Terminlisten_{month}")
    files: list[Path] = []
    for employee in employees:
        path = output / f"Terminliste_{month}_{quote(employee.emp_id, safe='')}.xlsx"
        _write_excel(employee, grouped[employee.emp_id], path, month)
        files.append(path)
        logger.info("Terminliste geschrieben: {} ({} Termine)", path, len(grouped[employee.emp_id]))
    logger.info(
        "Terminlisten {}: {} Dateien, {} Termine, {} ausgelassen",
        month,
        len(files),
        len(appointments) - skipped,
        skipped,
    )
    return files


def _write_excel(employee: Employee, appointments: list[ReportAppointment], path: Path, month: str) -> None:
    """Schreibt eine filterbare und druckbare Liste mit echten Excel-Datumswerten."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Termine"
    sheet.append([f"Terminliste {month}"])
    sheet.append([f"{employee.last_name or ''} {employee.first_name or ''} ({employee.emp_id})".strip()])
    sheet.append(["Offene Berichte und Einträge ohne Status, fällig in diesem Monat."])
    sheet.append(
        [
            "Fällig am",
            "Auftrag",
            "Indexkind",
            "Leistungsart",
            "Leistungsbesteller",
            "Berichtsform",
            "Status",
            "Notizen",
            "Bericht-ID",
        ]
    )
    for appointment in appointments:
        sheet.append(
            [
                appointment.due_date,
                appointment.mandate_id,
                appointment.index_child,
                appointment.service_type,
                appointment.requester,
                appointment.report_form,
                appointment.status,
                appointment.notes,
                appointment.report_id,
            ]
        )
    if not appointments:
        sheet.append(["Keine fälligen Berichte."])
    # Freitext bleibt Text, auch wenn er mit einem Formelzeichen beginnt.
    for row in sheet:
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    sheet["A1"].font = Font(name="Arial", size=16, bold=True)
    for cell in sheet[4]:
        cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2E4057")
    for row_number in range(5, 5 + len(appointments)):
        sheet.cell(row_number, 1).number_format = "dd.mm.yyyy"
    for column, width in enumerate((14, 14, 26, 20, 26, 22, 14, 45, 14), 1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    for row_number in (1, 2, 3):
        sheet.merge_cells(start_row=row_number, start_column=1, end_row=row_number, end_column=9)
    sheet.freeze_panes = "C5"
    sheet.auto_filter.ref = f"A4:I{max(4, 4 + len(appointments))}"
    sheet.print_title_rows = "1:4"
    sheet.print_area = f"A1:I{sheet.max_row}"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    workbook.save(path)
    workbook.close()
