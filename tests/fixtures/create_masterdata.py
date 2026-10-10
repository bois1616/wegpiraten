"""Erzeugt ein synthetisches Import-Workbook ohne Kunden- oder Sandbox-Daten.

Spaltenstand: finaler Build 10.10.2026. Nur die vom Import benötigten Tabellen;
keine Formeln, Prüfansichten oder Abhängigkeit vom Migrations-Build. Der technische
SA-Auftrag wird durch den Import erzeugt und gehört nicht ins Kunden-Workbook.
"""

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

TABLES: dict[str, tuple[str, tuple[str, ...]]] = {
    "person": (
        "Kinder",
        (
            "person_id",
            "short_code",
            "family_id",
            "social_security_number",
            "last_name",
            "first_name",
            "date_of_birth",
            "gender",
            "uma_umf",
            "spoken_language",
            "canton_of_residence",
            "residence_legal_guardian",
            "notes",
        ),
    ),
    "mandate": (
        "Aufträge",
        (
            "mandate_id",
            "service_type_id",
            "service_requester_id",
            "contact_person_id",
            "payer_id",
            "tenant_id",
            "application_number",
            "start_date",
            "end_date",
            "allowed_travel_time",
            "allowed_direct_effort",
            "allowed_indirect_effort",
            "allocation",
            "notes",
            "predecessor_choice",
            "report_cadence",
            "report_interval_months",
            "predecessor_mandate_id",
        ),
    ),
    "mandate_person": (
        "Betreuungen",
        (
            "mandate_id",
            "person_id",
            "start_date",
            "end_date",
            "is_leaving_reason_planned",
            "leaving_reason",
            "custom_leaving_reason",
            "after_leave_situation",
            "custom_after_leave_situation",
            "is_consultative_adolescent_psychiatric_care",
            "number_of_care_days_per_week",
            "remarks",
        ),
    ),
    "masterdata_contact_person": (
        "Ansprechpersonen",
        ("contact_person_id", "service_requester_id", "gender", "first_name", "last_name", "notes"),
    ),
    "relation_mandate_emp": ("Zuordnung MA", ("mandate_id", "employee_id", "role")),
    "report": (
        "Berichte",
        ("report_id", "mandate_choice", "mandate_id", "report_form", "due_date", "status", "completed_date", "notes"),
    ),
    "service_types": (
        "Leistungstypen",
        (
            "service_type_id",
            "code",
            "description",
            "hourly_rate",
            "km_rate",
            "rundung",
            "from_date",
            "to_date",
            "notes",
        ),
    ),
    "masterdata_service_requester": ("Leistungsbesteller", ("service_requester_id", "name")),
    "masterdata_payer": ("Kostenträger", ("payer_id", "name", "name2", "street", "zip_code", "city", "notes")),
    "masterdata_employee": ("Mitarbeiter", ("employee_id", "first_name", "last_name", "fte", "notes", "TS")),
    "masterdata_tenant": ("Büros", ("tenant_id", "name", "tenant_street", "tenant_zip", "tenant_city", "tenant_iban")),
}


def fixture_records() -> dict[str, list[dict[str, object]]]:
    """Deckt Geschwister, Parallelauftrag, Folgeauftrag, Vertretung und Austritt ab."""
    persons = [
        {
            "person_id": "C9001",
            "first_name": "Testkind",
            "last_name": "Alpha",
            "short_code": "TeAl",
            "family_id": "Testfamilie",
            "date_of_birth": datetime(2014, 1, 1),
        },
        {
            "person_id": "C9002",
            "first_name": "Testkind",
            "last_name": "Beta",
            "short_code": "TeBe",
            "family_id": "Testfamilie",
            "date_of_birth": datetime(2018, 1, 1),
        },
        {
            "person_id": "C9003",
            "first_name": "Testkind",
            "last_name": "Gamma",
            "short_code": "TeGa",
            "date_of_birth": datetime(2012, 1, 1),
        },
    ]
    for person in persons:
        person.update(gender="w", uma_umf="Nein", canton_of_residence="BE")
    mandates: list[dict[str, object]] = []
    definitions = [
        ("A26091", "ST01", datetime(2026, 6, 1), datetime(2026, 9, 30), None),
        ("A26092", "ST01", datetime(2026, 10, 1), datetime(2026, 12, 31), "A26091"),
        ("A26093", "ST04", datetime(2026, 7, 1), datetime(2026, 12, 31), None),
        ("A26094", "ST01", datetime(2026, 1, 1), datetime(2026, 5, 31), None),
    ]
    for index, (mid, service, start, end, predecessor) in enumerate(definitions, 1):
        row: dict[str, object] = {
            "mandate_id": mid,
            "service_type_id": service,
            "service_requester_id": "SR900",
            "contact_person_id": "AP900",
            "payer_id": "P1000",
            "tenant_id": "T900",
            "application_number": f"260101{index:03d}",
            "start_date": start,
            "end_date": end,
            "allowed_travel_time": 0.5,
            "allowed_direct_effort": 10,
            "allowed_indirect_effort": 5,
        }
        if predecessor:
            row.update(predecessor_choice=predecessor, predecessor_mandate_id=predecessor)
        mandates.append(row)
    cares: list[dict[str, object]] = [
        {"mandate_id": mid, "person_id": pid, "start_date": datetime(2026, 6, 1)}
        for mid in ("A26091", "A26092")
        for pid in ("C9001", "C9002")
    ]
    cares += [
        {"mandate_id": "A26093", "person_id": "C9001", "start_date": datetime(2026, 7, 1)},
        {
            "mandate_id": "A26094",
            "person_id": "C9003",
            "start_date": datetime(2026, 1, 1),
            "end_date": datetime(2026, 5, 31),
            "leaving_reason": "Anderer",
            "custom_leaving_reason": "Synthetischer Testaustritt",
        },
    ]
    return {
        "person": persons,
        "mandate": mandates,
        "mandate_person": cares,
        "masterdata_contact_person": [
            {
                "contact_person_id": "AP900",
                "service_requester_id": "SR900",
                "gender": "Frau",
                "first_name": "Test",
                "last_name": "Kontakt",
            }
        ],
        "relation_mandate_emp": [
            {"mandate_id": mid, "employee_id": employee, "role": role}
            for mid, employee, role in [
                ("A26091", "E9001", "P"),
                ("A26091", "E9002", "S"),
                ("A26092", "E9001", "P"),
                ("A26093", "E9002", "P"),
                ("A26094", "E9001", "P"),
            ]
        ],
        "report": [
            {
                "report_id": "R9001",
                "mandate_choice": "A26092",
                "mandate_id": "A26092",
                "report_form": "Bericht",
                "due_date": datetime(2026, 10, 15),
                "status": "offen",
            }
        ],
        "masterdata_employee": [
            {"employee_id": eid, "first_name": "Test", "last_name": name, "TS": ts}
            for eid, name, ts in [("E9001", "Eins", True), ("E9002", "Zwei", True), ("E9003", "OhneBogen", False)]
        ],
        "masterdata_payer": [
            {
                "payer_id": "P1000",
                "name": "Testkostenträger",
                "street": "Testweg 1",
                "zip_code": "3000",
                "city": "Testort",
            }
        ],
        "masterdata_service_requester": [{"service_requester_id": "SR900", "name": "Testbesteller"}],
        "masterdata_tenant": [
            {
                "tenant_id": "T900",
                "name": "Teststandort",
                "tenant_street": "Testweg 2",
                "tenant_zip": "3000",
                "tenant_city": "Testort",
            }
        ],
        "service_types": [
            {
                "service_type_id": sid,
                "code": code,
                "description": "Testleistung",
                "hourly_rate": rate,
                "km_rate": 0.7,
                "rundung": 1,
                "from_date": datetime(2026, 1, 1),
            }
            for sid, code, rate in [
                ("ST01", "SPF", 100),
                ("ST04", "UWB (Begleitung Individuell)", 120),
                ("ST999", "SONST", 0),
            ]
        ],
    }


def create_workbook(path: Path) -> Path:
    """Schreibt die kleine, formelfreie Importfixture an den angegebenen Pfad."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    records = fixture_records()
    for name, (title, columns) in TABLES.items():
        sheet = workbook.create_sheet(title)
        sheet.cell(1, 1, "Synthetische Testdaten, keine Kundendaten")
        for column, field in enumerate(columns, 1):
            sheet.cell(2, column, field)
        for number, row in enumerate(records[name], 3):
            for column, field in enumerate(columns, 1):
                cell = sheet.cell(number, column, row.get(field))
                if isinstance(cell.value, datetime):
                    cell.number_format = "DD.MM.YYYY"
        for row in sheet:
            for cell in row:
                cell.font = Font(name="Arial", size=10)
        table = Table(displayName=name, ref=f"A2:{get_column_letter(len(columns))}{sheet.max_row}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        sheet.add_table(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return path
