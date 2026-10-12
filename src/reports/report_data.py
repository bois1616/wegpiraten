"""Gemeinsame Berichtsdaten und Zuständigkeit am Fälligkeitstag."""

import sqlite3
from datetime import date

from pydantic import BaseModel, field_validator

from shared_modules.accordix import parse_db_date


class Employee(BaseModel):
    """Mitarbeitende unabhängig vom Timesheet-Schalter."""

    emp_id: str
    first_name: str | None
    last_name: str | None


class AssignmentPeriod(BaseModel):
    """Eine in der Stammdatenmappe gepflegte Zuordnungsperiode."""

    assignment_id: str
    mandate_id: str | None
    employee_id: str | None
    role: str | None
    valid_from: str | None
    valid_to: str | None


class ReportAppointment(BaseModel):
    """Bericht mit aktueller Auftragsanzeige und datierter Zuständigkeit."""

    report_id: str
    mandate_id: str | None
    due_date: date | None
    report_form: str | None
    status: str | None
    completed_date: date | None
    notes: str | None
    first_name: str | None
    last_name: str | None
    index_child: str | None
    service_type: str | None
    requester: str | None
    contact: str | None
    phone: str | None
    start_date: date | None
    end_date: date | None
    travel_minutes: int | None
    direct_minutes: int | None
    indirect_minutes: int | None
    current_employees: str | None
    existing_mandate: str | None
    employee_id: str | None = None
    primary_count: int = 0
    assignment_basis: str = ""
    assignment_error: str | None = None

    @field_validator("due_date", "completed_date", "start_date", "end_date", mode="before")
    @classmethod
    def parse_dates(cls, value: object) -> date | None:
        """Ungültige Termine bleiben als unzuordenbare Berichte sichtbar."""
        return parse_db_date(value)


def load_report_data(conn: sqlite3.Connection) -> tuple[list[Employee], list[ReportAppointment]]:
    """Liest explizite Berichte; erzeugt keine Termine und schreibt keine Daten."""
    conn.row_factory = sqlite3.Row
    employees = [
        Employee.model_validate(dict(row))
        for row in conn.execute(
            "SELECT emp_id,first_name,last_name FROM employees ORDER BY last_name,first_name,emp_id"
        )
    ]
    contact_columns = {row[1] for row in conn.execute("PRAGMA table_info(masterdata_contact_person)")}
    phone = "ap.phone" if "phone" in contact_columns else "NULL"
    appointments = [
        ReportAppointment.model_validate(dict(row))
        for row in conn.execute(
            f"""SELECT r.report_id,r.mandate_id,r.due_date,r.report_form,r.status,
                r.completed_date,r.notes,m.first_name,m.last_name,
                m.last_name || ' ' || m.first_name AS index_child,
                st.code AS service_type,sr.name AS requester,
                trim(COALESCE(ap.first_name,'') || ' ' || COALESCE(ap.last_name,'')) AS contact,
                {phone} AS phone,m.start_date,m.end_date,
                m.allowed_travel_time AS travel_minutes,m.allowed_direct_effort AS direct_minutes,
                m.allowed_indirect_effort AS indirect_minutes,
                (SELECT group_concat(employee_id,', ') FROM
                  (SELECT DISTINCT employee_id FROM relation_mandate_emp a
                   WHERE a.mandate_id=r.mandate_id AND COALESCE(a.is_active,1)=1
                   AND (NULLIF(a.valid_from,'') IS NULL OR date(a.valid_from)<=date('now'))
                   AND (NULLIF(a.valid_to,'') IS NULL OR date(a.valid_to)>=date('now')))) AS current_employees,
                m.mandate_id AS existing_mandate
            FROM report r LEFT JOIN v_mandate m ON m.mandate_id=r.mandate_id
            LEFT JOIN service_types st ON st.service_type_id=m.service_type_id
            LEFT JOIN service_requester sr ON sr.service_requester_id=m.service_requester_id
            LEFT JOIN masterdata_contact_person ap ON ap.contact_person_id=m.contact_person_id
            ORDER BY r.due_date,r.mandate_id,r.report_id"""
        )
    ]
    history: dict[str, list[AssignmentPeriod]] = {}
    for row in conn.execute(
        "SELECT COALESCE(source_row,rowid) AS assignment_id,mandate_id,employee_id,role,valid_from,valid_to "
        "FROM relation_mandate_emp WHERE COALESCE(is_active,1)=1"
    ):
        values = dict(row)
        values["assignment_id"] = str(values["assignment_id"])
        period = AssignmentPeriod.model_validate(values)
        if period.mandate_id:
            history.setdefault(period.mandate_id, []).append(period)
    for report in appointments:
        _assign(report, history.get(report.mandate_id or "", []))
    return employees, appointments


def _assign(report: ReportAppointment, periods: list[AssignmentPeriod]) -> None:
    """Historienlücken führen niemals zu einem Rückfall auf die heutige Zuordnung."""
    if not report.existing_mandate:
        report.assignment_error = "Auftrag fehlt in den Stammdaten"
        return
    if not report.due_date:
        report.assignment_error = "Fälligkeit fehlt oder ist ungültig"
        return
    matches: list[str] = []
    if periods:
        dated = any(p.valid_from or p.valid_to for p in periods)
        report.assignment_basis = (
            "Zuordnung MA am Fälligkeitstag"
            if dated
            else "Zuordnung MA ohne Datumsgrenzen; historische Zuständigkeit unbekannt"
        )
        for period in periods:
            start, end = parse_db_date(period.valid_from), parse_db_date(period.valid_to)
            if (
                period.role not in (None, "", "P", "S")
                or (period.valid_from and not start)
                or (period.valid_to and not end)
                or (start and end and end < start)
            ):
                report.assignment_error = f"Ungültiger Zuständigkeitszeitraum {period.assignment_id}"
                return
            if period.role == "P" and (not start or start <= report.due_date) and (not end or report.due_date <= end):
                if not period.employee_id:
                    report.assignment_error = f"Mitarbeiter fehlt im Zuständigkeitszeitraum {period.assignment_id}"
                    return
                matches.append(period.employee_id)
    else:
        report.assignment_basis = "Keine Zuordnung MA"
    report.primary_count = len(matches)
    if not matches:
        report.assignment_error = "keine Person mit Rolle P" + (" am Fälligkeitstag" if periods else "")
    elif len(matches) > 1:
        report.assignment_error = "mehrere Personen mit Rolle P" + (" am Fälligkeitstag" if periods else "")
    else:
        report.employee_id = matches[0]


def assignment_problem(report: ReportAppointment, employee_ids: set[str]) -> str | None:
    """Liefert denselben Auslassungsgrund für alle Berichtsausgaben."""
    if report.assignment_error:
        return report.assignment_error
    if report.employee_id not in employee_ids:
        return "Person mit Rolle P fehlt in den Mitarbeiter-Stammdaten"
    return None
