"""Integration des neuen Schemas ohne Kundendaten."""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml
from openpyxl import Workbook, load_workbook
from pytest import MonkeyPatch

from data_imports.batch_import_timesheets import TimeSheetsImporter
from data_imports.import_masterdata import run_import
from data_imports.legacy_mandates import LegacyMandateResolver
from invoices.modules.invoice_filter import InvoiceFilter
from invoices.modules.invoice_processor import InvoiceProcessor
from shared_modules.config import Config
from shared_modules.month_period import get_month_period
from tests.fixtures.create_masterdata import create_workbook
from time_sheets.modules.client_data import load_active_client_headers, load_internal_timesheet_headers


@pytest.fixture
def imported(tmp_path: Path, monkeypatch: MonkeyPatch) -> Config:
    """Isolierte Config, synthetisches Workbook und eigene DB je Test."""
    root = Path(__file__).resolve().parents[1]
    data = yaml.safe_load((root / ".config/wegpiraten_config.yaml").read_text())
    data["structure"]["prj_root"] = str(tmp_path)
    data["structure"]["template_path"] = str(root / "templates")
    data["database"]["legacy_mandate_mapping"] = "legacy.json"
    data["logging"] = {"log_level": "WARNING", "log_file": str(tmp_path / "test.log")}
    for directory in ("data", "import", "done", "output", ".tmp", ".logs", "graphics"):
        (tmp_path / directory).mkdir()
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data))
    (tmp_path / "legacy.json").write_text(json.dumps({"C9001": ["A26091", "A26092"]}))
    monkeypatch.setattr(Config, "_instance", None)
    config = Config(path)
    run_import(config, create_workbook(tmp_path / "master.xlsx"))
    return config


def test_view_index_budget_sentinel_and_timesheet_headers(imported: Config) -> None:
    """Indexkind kann unbetreut sein; SA hat keine künstliche Person oder Betreuung."""
    with sqlite3.connect(imported.get_db_path()) as conn:
        assert conn.execute(
            "SELECT index_person_id,allowed_travel_time FROM v_mandate WHERE mandate_id='A26093'"
        ).fetchone() == ("C9002", 30)
        assert conn.execute("SELECT count(*) FROM v_mandate").fetchone()[0] == 5
        assert conn.execute("SELECT count(*) FROM mandate_person WHERE mandate_id='SA'").fetchone()[0] == 0
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='clients'").fetchone()
    headers = load_active_client_headers(imported.get_db_path(), "2026-09")
    assert {h.client_id for h in headers} == {"A26091", "A26093"}
    assert len(load_internal_timesheet_headers(imported.get_db_path())) == 2


def test_legacy_renewal_dates_overlap_and_unknown(imported: Config) -> None:
    resolver = LegacyMandateResolver(imported.get_db_path(), Path(imported.structure.prj_root) / "legacy.json")
    assert resolver.resolve("C9001", date(2026, 9, 30)) == ("A26091", False)
    assert resolver.resolve("C9001", date(2026, 10, 1)) == ("A26092", False)
    assert resolver.resolve("SA", date(2026, 9, 1)) == ("SA", False)
    with pytest.raises(ValueError):
        resolver.resolve("C9999", date(2026, 9, 1))
    with sqlite3.connect(imported.get_db_path()) as conn:
        conn.execute("UPDATE mandate SET start_date='2026-09-01' WHERE mandate_id='A26092'")
    with pytest.raises(ValueError):
        resolver.resolve("C9001", date(2026, 9, 1))


def test_timesheet_crosses_renewal_boundary_and_file_failure_is_atomic(imported: Config) -> None:
    importer = TimeSheetsImporter(imported)
    with sqlite3.connect(imported.get_db_path()) as conn:
        conn.execute("UPDATE mandate SET allowed_direct_effort=180 WHERE mandate_id='A26092'")
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet["F5"] = "E9001"
    sheet["F8"] = "C9001"
    sheet["C6"] = datetime(2026, 9, 1)
    sheet["A10"] = "Uhrzeit"
    sheet["B10"] = "Datum"
    sheet["C10"] = "Fahrzeit"
    sheet["D10"] = "Direkter Fallkontakt"
    sheet["E10"] = "Indirekte Fallbearbeitung"
    sheet["H10"] = "Notizen"
    sheet["B11"] = datetime(2026, 9, 30)
    sheet["D11"] = 15
    sheet["H11"] = "Ohne Berechnung"
    sheet["B12"] = datetime(2026, 10, 1)
    sheet["D12"] = 30
    path = importer.source_dir / "crossing.xlsx"
    workbook.save(path)
    count, _, _, _ = importer.process_file(path, "2026-09", get_month_period("2026-09"))
    assert count == 2
    with sqlite3.connect(imported.get_db_path()) as conn:
        rows = conn.execute("SELECT mandate_id,direct_time,notes FROM service_data ORDER BY service_date").fetchall()
    assert rows == [("A26091", 15, "Ohne Berechnung"), ("A26092", 30, None)]
    with sqlite3.connect(imported.get_db_path()) as conn:
        assert conn.execute("SELECT allowed_direct_effort FROM service_data ORDER BY service_date").fetchall() == [
            (600,),
            (180,),
        ]
    processor = InvoiceProcessor(imported, InvoiceFilter(invoice_month="09.2026", client_list=["C9002"]))
    data = processor._load_service_data(get_month_period("2026-09"))
    assert len(data) == 1 and data.iloc[0]["client_id"] == "A26091"
    assert data.iloc[0]["hourly_rate"] == 100
    # Die zweite Datei enthält eine unauflösbare Zeile: auch die erste darf nicht gespeichert werden.
    sheet["B12"] = datetime(2025, 1, 1)
    bad = importer.source_dir / "bad.xlsx"
    workbook.save(bad)
    count, _, _, _ = importer.process_file(bad, "2026-09", get_month_period("2026-09"))
    assert count == 0 and bad.exists()
    with sqlite3.connect(imported.get_db_path()) as conn:
        assert conn.execute("SELECT count(*) FROM service_data").fetchone()[0] == 2


def test_twins_use_workbook_order_and_missing_reference_stays_visible(imported: Config) -> None:
    """Reihenfolge bleibt erhalten; fehlerhafte Verweise verschwinden nicht aus der View."""
    with sqlite3.connect(imported.get_db_path()) as conn:
        conn.execute("UPDATE person SET date_of_birth='2018-01-01' WHERE person_id='C9001'")
        conn.execute("UPDATE person SET source_row=1 WHERE person_id='C9002'")
        assert conn.execute("SELECT index_person_id FROM v_mandate WHERE mandate_id='A26091'").fetchone()[0] == "C9002"
        conn.execute("UPDATE mandate SET contact_person_id='AP_MISSING' WHERE mandate_id='A26091'")
        assert conn.execute("SELECT count(*) FROM v_mandate WHERE mandate_id='A26091'").fetchone()[0] == 1
        assert conn.execute("SELECT sr_ap_last_name FROM v_mandate WHERE mandate_id='A26091'").fetchone()[0] is None


def test_accordix_care_continuation_and_exit_are_not_authorisation_end(imported: Config) -> None:
    """Zwei passende Folgeaufträge melden dieselbe Betreuung einmal; Ende ist echter Austritt."""
    from reports.accordix_report import create_accordix_report

    with sqlite3.connect(imported.get_db_path()) as conn:
        conn.execute("UPDATE mandate SET start_date='2026-09-15' WHERE mandate_id='A26092'")
    output = create_accordix_report(imported, "2026-09")
    sheet = load_workbook(output, data_only=True)["Ambulant"]
    populated = [r for r in sheet.iter_rows(min_row=7, values_only=True) if r[0]]
    assert len(populated) == 3
    assert all(r[18] is None for r in populated)
    with sqlite3.connect(imported.get_db_path()) as conn:
        conn.execute(
            "UPDATE mandate_person SET end_date='2026-09-20', leaving_reason='Anderer', custom_leaving_reason='Testende' WHERE mandate_id='A26092'"
        )
    output = create_accordix_report(imported, "2026-09")
    sheet = load_workbook(output, data_only=True)["Ambulant"]
    populated = [r for r in sheet.iter_rows(min_row=7, values_only=True) if r[0]]
    ended = [r for r in populated if r[18]]
    assert len(ended) == 2
    assert all(r[18] == "20.09.2026" and r[20] == "Anderer" and r[21] == "Testende" for r in ended)


def test_invoice_keeps_zero_charge_position_and_skips_unusable_tariff(
    imported: Config, monkeypatch: MonkeyPatch
) -> None:
    """Kostenfreie Minuten sind sichtbar, erhöhen den Betrag aber nicht."""
    from PyPDF2 import PdfWriter

    from invoices.modules.document_utils import DocumentUtils
    from invoices.modules.invoice_context import InvoiceContext

    TimeSheetsImporter(imported)
    with sqlite3.connect(imported.get_db_path()) as conn:
        conn.executemany(
            """INSERT INTO service_data (mandate_id,employee_id,service_date,service_type,
            direct_time,notes,reporting_month,allowed_direct_effort) VALUES ('A26091','E9001','2026-09-01','SPF',?,?,'2026-09',600)""",
            [(15, "Ohne Berechnung"), (45, None)],
        )
    contexts: list[InvoiceContext] = []

    def fake_pdf(docx_path: Path, pdf_path: Path, context: InvoiceContext) -> Path:
        """PDF-Konverter isolieren; die eigentliche DOCX-Erzeugung läuft unverändert."""
        contexts.append(context)
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with pdf_path.open("wb") as handle:
            writer.write(handle)
        return pdf_path

    monkeypatch.setattr(DocumentUtils, "docx_to_pdf", staticmethod(fake_pdf))
    InvoiceProcessor(imported, InvoiceFilter(invoice_month="09.2026")).run()
    assert len(contexts) == 1
    positions = contexts[0].data["positions"]
    assert len(positions) == 2
    assert [p["Kosten"] for p in positions] == [0, 75]
    assert contexts[0].data["summe_kosten"] == 75
    assert contexts[0].data["client"].social_security_number == ""
    with sqlite3.connect(imported.get_db_path()) as conn:
        conn.execute("UPDATE service_types SET hourly_rate=NULL WHERE service_type_id='ST01'")
    contexts.clear()
    InvoiceProcessor(imported, InvoiceFilter(invoice_month="09.2026")).run()
    assert not contexts


def test_new_timesheet_can_be_filled_and_imported(imported: Config, monkeypatch: MonkeyPatch) -> None:
    """Erzeugung und Import teilen dieselben konfigurierten Kopfzellen und Minutenbudgets."""
    from time_sheets.modules.time_sheet_factory import TimeSheetFactory

    monkeypatch.setenv("SHEET_PASSWORD", "synthetic-test-only")
    factory = TimeSheetFactory(imported)
    headers = factory.fetch_reporting_data("2026-09")
    header = next(h for h in headers if h.client_id == "A26091" and h.employee_id == "E9001")
    path = factory.create_reporting_sheet(header, datetime(2026, 9, 1), output_path=imported.get_imports_path())
    book = load_workbook(path)
    sheet = book.active
    assert sheet is not None
    assert sheet["F8"].value == "A26091"
    sheet["B11"] = datetime(2026, 9, 1)
    sheet["D11"] = 30
    book.save(path)
    importer = TimeSheetsImporter(imported)
    count, _, _, _ = importer.process_file(path, "2026-09", get_month_period("2026-09"))
    assert count == 1
    with sqlite3.connect(imported.get_db_path()) as conn:
        assert conn.execute("SELECT mandate_id,direct_time,allowed_travel_time FROM service_data").fetchone() == (
            "A26091",
            30,
            30,
        )
