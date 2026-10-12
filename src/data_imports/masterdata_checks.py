"""Nachbearbeitbare Stammdatenhinweise, unabhängig von Excel-Formelcaches."""

import re
import sqlite3
from datetime import date

from pydantic import BaseModel

from shared_modules.accordix import FIELD_VALUE_LISTS, parse_db_date, validate_coded_value
from shared_modules.assignment_periods import assignment_window_sql


class CheckFinding(BaseModel):
    """Ein Datenbefund mit nachvollziehbarer Herkunft."""

    table: str
    key: str
    source_row: int | None
    message: str
    invariant: int | None = None


def check_masterdata(conn: sqlite3.Connection, payer_ids: list[str], today: date | None = None) -> list[CheckFinding]:
    """Prüft fachliche Zusatzdaten als Hinweise; ändert keine Eingaben."""
    current_day = today or date.today()
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    result: list[CheckFinding] = []

    def add(table: str, key: str, row: int | None, message: str, invariant: int | None = None) -> None:
        result.append(CheckFinding(table=table, key=key, source_row=row, message=message, invariant=invariant))

    for field in ("payer_id", "service_requester_id", "tenant_id", "service_type_id"):
        for key, row in conn.execute(
            f"SELECT mandate_id,source_row FROM mandate WHERE mandate_id<>'SA' AND COALESCE({field},'')=''"
        ):
            add("mandate", key, row, f"Pflichtverweis {field} fehlt")
    for key, row, count in conn.execute(
        "SELECT m.mandate_id,m.source_row,(SELECT count(*) FROM relation_mandate_emp r "
        "WHERE r.mandate_id=m.mandate_id AND r.role='P' AND "
        + assignment_window_sql()
        + ") FROM mandate m WHERE m.mandate_id<>'SA'",
        (current_day.isoformat(), current_day.isoformat()),
    ):
        if count != 1:
            add(
                "mandate",
                key,
                row,
                "Keine primäre Betreuungsperson" if count == 0 else "Mehrere primäre Betreuungspersonen",
                41,
            )
    for key, row, mandate, due, status, completed, form in conn.execute(
        "SELECT report_id,source_row,mandate_id,due_date,status,completed_date,report_form FROM report"
    ):
        if not mandate:
            add("report", key, row, "Auftragsverweis fehlt (berechnete Auftrag-Nr prüfen)", 38)
        due_date = parse_db_date(due)
        if not due_date:
            add("report", key, row, "Fälligkeit fehlt oder ist ungültig")
        elif status == "offen" and due_date < current_day:
            add("report", key, row, "Bericht ist überfällig und noch offen", 39)
        if status == "erledigt" and not parse_db_date(completed):
            add("report", key, row, "Erledigt-Datum fehlt oder ist ungültig", 40)
        if (
            form == "Abschlussbericht"
            and conn.execute("SELECT 1 FROM mandate WHERE predecessor_mandate_id=?", (mandate,)).fetchone()
        ):
            add("report", key, row, "Abschlussbericht auf einem Auftrag mit Nachfolger", 49)
        if status and status not in ("offen", "erledigt", "entfällt"):
            add("report", key, row, "Berichtsstatus weicht von der Werteliste ab")
    for key, row, payer, end, planned, reason, custom in conn.execute(
        "SELECT b.mandate_id || '/' || b.person_id,b.source_row,m.payer_id,b.end_date,b.is_leaving_reason_planned,b.leaving_reason,b.custom_leaving_reason FROM mandate_person b LEFT JOIN mandate m ON m.mandate_id=b.mandate_id"
    ):
        if payer not in payer_ids or not end:
            continue
        if planned not in ("Ja", "Nein"):
            add("mandate_person", key, row, "Austritt geplant: Ja/Nein fehlt oder ist ungültig")
        if planned == "Nein" and not reason:
            add("mandate_person", key, row, "Ungeplanter Austritt ohne Austrittsgrund")
        if planned == "Nein" and reason == "Anderer" and not custom:
            add("mandate_person", key, row, "Anderer Austrittsgrund ohne Freitext")
    for table, pk, fields in (
        ("person", "person_id", ("gender", "uma_umf", "spoken_language", "canton_of_residence")),
        ("mandate", "mandate_id", ("allocation",)),
        ("mandate_person", "mandate_id || '/' || person_id", ("leaving_reason", "after_leave_situation")),
    ):
        for field in fields:
            if field not in FIELD_VALUE_LISTS:
                continue
            for key, row, value in conn.execute(f"SELECT {pk},source_row,{field} FROM {table}"):
                if validate_coded_value(field, value):
                    add(table, key, row, f"{field}: Schreibweise weicht von der Werteliste ab")
    for table, pk, date_fields in (
        ("mandate", "mandate_id", ("start_date", "end_date")),
        ("mandate_person", "mandate_id || '/' || person_id", ("start_date", "end_date")),
        ("placement", "placement_id", ("start_date", "end_date")),
        ("relation_mandate_emp", "mandate_id || '/' || employee_id", ("valid_from", "valid_to")),
    ):
        if table not in tables:
            continue
        start_field, end_field = date_fields
        for key, row, start, end in conn.execute(f"SELECT {pk},source_row,{start_field},{end_field} FROM {table}"):
            first, last = parse_db_date(start), parse_db_date(end)
            if start and not first or end and not last:
                add(table, key, row, "Datumsangabe ist ungültig")
            elif first and last and last < first:
                add(table, key, row, "Enddatum liegt vor dem Beginn")
    for table, pk, email_field in (
        ("related_person", "related_person_id", "email"),
        ("masterdata_contact_person", "contact_person_id", "email"),
        ("payer", "payer_id", "billing_email"),
    ):
        if table not in tables or email_field not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
            continue
        for key, row, value in conn.execute(
            f"SELECT {pk},source_row,{email_field} FROM {table} WHERE COALESCE({email_field},'')<>''"
        ):
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
                add(table, key, row, "E-Mail-Schreibweise prüfen")
    if "person_related_person" in tables:
        for key, row, person, adult, role, guardian in conn.execute(
            "SELECT relationship_id,source_row,person_id,related_person_id,role,is_legal_guardian FROM person_related_person"
        ):
            if not person or not adult:
                add("person_related_person", key, row, "Kind- oder Bezugspersonverweis fehlt")
            if role not in ("Mutter", "Vater", "Beistand", "Pflegeperson", "Bezugsperson", "Sonstige"):
                add("person_related_person", key, row, "Beziehungsrolle fehlt oder ist unbekannt")
            if guardian not in (None, "", "Ja", "Nein", "Unbekannt"):
                add("person_related_person", key, row, "Sorgeberechtigung muss Ja/Nein/Unbekannt sein")
    if "placement" in tables:
        for key, row in conn.execute("SELECT placement_id,source_row FROM placement WHERE COALESCE(person_id,'')=''"):
            add("placement", key, row, "Kindverweis fehlt")
    if "relation_mandate_emp" in tables:
        for key, row in conn.execute(
            "SELECT mandate_id || '/' || employee_id,source_row FROM relation_mandate_emp WHERE COALESCE(mandate_id,'')='' OR COALESCE(employee_id,'')='' OR COALESCE(role,'') NOT IN ('P','S')"
        ):
            add("relation_mandate_emp", key, row, "Auftrag, Mitarbeiter oder Rolle P/S fehlt bzw. ist ungültig")
        for first, row, second in conn.execute(
            "SELECT a.mandate_id || '/' || a.employee_id,a.source_row,b.source_row "
            "FROM relation_mandate_emp a JOIN relation_mandate_emp b ON a.mandate_id=b.mandate_id AND a.rowid<b.rowid "
            "WHERE a.role='P' AND b.role='P' AND COALESCE(a.is_active,1)=1 AND COALESCE(b.is_active,1)=1 "
            "AND COALESCE(date(NULLIF(a.valid_from,'')),'0001-01-01')<=COALESCE(date(NULLIF(b.valid_to,'')),'9999-12-31') "
            "AND COALESCE(date(NULLIF(b.valid_from,'')),'0001-01-01')<=COALESCE(date(NULLIF(a.valid_to,'')),'9999-12-31')"
        ):
            add("relation_mandate_emp", first, row, f"P-Zeitraum überschneidet sich mit Zeile {second}")
    return result
