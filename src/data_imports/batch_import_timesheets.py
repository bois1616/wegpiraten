# importiere ein Batch von reporting sheets in die Datenbank
# nutzt die config.py für die Pfade
# Die Daten werden in service_data gespeichert (Rohdaten für die Rechnungserstellung)
# Nutzt reporting_row_model.py für die Datenstruktur
# #
# Gemeinsames Profil: Die Klassen HeaderCells, RowMapping, TableRange und
# ReportingImportProfile kapseln Zellen- und Spaltenbezüge sowie den Datenbereich.
# Diese Strukturen sollten idealerweise in ein gemeinsames Modul
# (z.B. zeiterfassungen/modules/reporting_sheet_profile.py) ausgelagert und
# sowohl in ReportingFactory (Erstellung) als auch hier (Import) genutzt werden.
# So bleibt die Logik synchron.
# Konsistenz mit create_reporting_sheet:
# Die verwendeten Header-Zellen (C5, G5, C6, C7, G7, C8, G8) entsprechen den in
# create_reporting_sheet beschriebenen Feldern.
# Bei Änderungen am Template muss nur HeaderCells angepasst werden.
# Robustheit:
# Einmalige Prüfungen (DB-Pfad, Sheet-Existenz, notwendige Header-Felder)
# mit assert (“prüfe einmal und dann traue”).
# Zeilen werden defensiv konvertiert und validiert.
# Transaktionale Inserts mit Rollback bei Fehler.
# Pfade: Vorerst wird ein fixer Windows-Pfad als Quelle verwendet.
# Wenn dieser nicht existiert, wird auf einen dynamischen Pfad aus der Config
# (structure.imports_path) oder schließlich prj_root/data_imports zurückgefallen.
# Die verarbeiteten Dateien werden in ein Unterverzeichnis importiert verschoben,
#  welches bei Bedarf angelegt wird.
# Pydantic:
# Konsequent für Profil und Datenmodelle. Erweiterbar um weitere Felder (z.B. Notizen aus Spalte G/H).
# Weiter normalisieren?
# Ja, sinnvoll wäre eine Normalisierung der Positionen in eine eigene Tabelle
# timesheet_entries, wenn service_data bereits Rohdaten abbildet.
#  Alternativ kann service_data als staging genutzt werden und ein nachgelagerter
# Prozess normalisiert in ein Faktentableau.

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from loguru import logger
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, ValidationError

from pydantic_models.data.invoice_row_model import InvoiceRowModel
from pydantic_models.data.row_mapping import RowMapping
from pydantic_models.data.timesheet_import_profile import TimeSheetImportProfile
from shared_modules.config import Config
from shared_modules.utils import (
    choose_existing_path,
    ensure_dir,
    to_date,
    to_float,
    to_year_month_str,
)


class ImportedRowExport(BaseModel):
    """
    Erweiterung des InvoiceRowModel um Kontextinformationen für den Sammel-Export.
    """

    reporting_month: str
    source_file: str
    client_id: str
    employee_id: str
    service_date: date
    service_type: str
    travel_time: float
    travel_distance: float = 0.0
    direct_time: float
    indirect_time: float
    billable_hours: float
    notes: Optional[str] = None
    hourly_rate: Optional[float] = None
    total_hours: Optional[float] = None
    total_costs: Optional[float] = None


class ImportErrorEntry(BaseModel):
    """Ein einzelner Fehlerfall für das Import-Fehlerprotokoll."""

    timestamp: str
    source_file: str
    category: str
    message: str
    row_number: Optional[int] = None


class TimeSheetsImporter:
    """
    Liest ausgefüllte Aufwandserfassungs-Sheets, validiert jede Positionszeile
    gegen InvoiceRowModel, schreibt sie in service_data und exportiert zusätzlich
    eine Sammeldatei der importierten Daten.
    """

    _INSERT_FIELDS: tuple[str, ...] = (
        "client_id",
        "employee_id",
        "service_date",
        "service_type",
        "travel_time",
        "travel_distance",
        "direct_time",
        "indirect_time",
        "notes",
        "source_file",
        "reporting_month",
    )

    _HEADER_LABELS_WITH_KM: Dict[str, str] = {
        "service_time_col": "uhrzeit",
        "service_date_col": "datum",
        "travel_time_col": "fahrtzeit",
        "travel_distance_col": "km",
        "direct_time_col": "direkter fallkontakt",
        "indirect_time_col": "indirekte fallbearbeitung",
        "billable_hours_col": "stunden",
        "notes_col": "notizen",
    }

    _HEADER_LABELS_NO_KM: Dict[str, str] = {
        "service_time_col": "uhrzeit",
        "service_date_col": "datum",
        "travel_time_col": "fahrtzeit",
        "travel_distance_col": "direkter fallkontakt",
        "direct_time_col": "indirekte fallbearbeitung",
        "indirect_time_col": "stunden",
        "billable_hours_col": "notizen",
    }

    def __init__(self, config: Config, profile: Optional[TimeSheetImportProfile] = None):
        self.config = config
        self.profile = profile or self._build_profile_from_config(config)
        self.masterdata_stem = Path(self.config.database.db_name or "").stem

        prj_root = Path(self.config.structure.prj_root)
        data_dir = prj_root / (getattr(self.config.structure, "local_data_path", None) or "data")
        self.db_path = data_dir / self.config.database.sqlite_db_name
        self.output_dir = ensure_dir(prj_root / (getattr(self.config.structure, "output_path", None) or "output"))

        cfg_imports_path = getattr(self.config.structure, "imports_path", None) or self.config.get(
            "structure.imports_path", None
        )
        cfg_done_path = getattr(self.config.structure, "done_path", None) or self.config.get(
            "structure.done_path", None
        )
        default_import = prj_root / "import"
        fallback_local = prj_root / "data_imports"
        default_windows = Path(r"C:\Users\micro\OneDrive\Shared\Beatus\Wegpiraten Unterlagen\data_imports")

        # Kandidatenliste: nimm den ersten existierenden Pfad
        candidates: List[Optional[Path]] = [
            Path(cfg_imports_path) if cfg_imports_path else None,
            default_import,
            fallback_local,
            default_windows,
        ]
        self.source_dir = ensure_dir(choose_existing_path(candidates, default_import))
        self.done_dir = ensure_dir(Path(cfg_done_path) if cfg_done_path else (prj_root / "done"))

        logger.info(f"DB: {self.db_path}")
        logger.info(f"Quelle: {self.source_dir}")
        logger.info(f"Done-Ordner: {self.done_dir}")
        logger.info(
            f"Sheet: {self.profile.sheet_name}, Range: "
            f"{self.profile.table_range.start_row}-{self.profile.table_range.end_row}"
        )

        self._error_entries: List[ImportErrorEntry] = []
        self._valid_client_ids: set[str] = set()
        self._valid_employee_ids: set[str] = set()

        self._ensure_service_data_table()
        self._refresh_fk_cache()

    @staticmethod
    def _build_profile_from_config(config: Config) -> TimeSheetImportProfile:
        return TimeSheetImportProfile.from_config(config.templates)

    def _record_error(
        self,
        source_file: str,
        category: str,
        message: str,
        row_number: Optional[int] = None,
    ) -> None:
        entry = ImportErrorEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source_file=source_file,
            category=category,
            message=message,
            row_number=row_number,
        )
        self._error_entries.append(entry)
        row_suffix = f" (Zeile {row_number})" if row_number is not None else ""
        logger.error("{}{}: {}", source_file, row_suffix, message)

    def _fetch_reference_values(self, table: str, column: str) -> set[str]:
        sql = f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL"
        values: set[str] = set()
        try:
            with sqlite3.connect(self.db_path) as conn:
                for row in conn.execute(sql):
                    value = row[0]
                    if value is None:
                        continue
                    normalized = str(value).strip()
                    if normalized:
                        values.add(normalized)
        except sqlite3.OperationalError as exc:
            self._record_error(
                "SYSTEM",
                "Referenzdaten",
                f"Referenztabelle {table}.{column} nicht lesbar: {exc}",
            )
        return values

    def _refresh_fk_cache(self) -> None:
        self._valid_client_ids = self._fetch_reference_values("clients", "client_id")
        self._valid_employee_ids = self._fetch_reference_values("employees", "emp_id")

    def _validate_header_foreign_keys(self, header: Dict[str, object], source_file: str) -> bool:
        client_id = str(header.get("client_id") or "").strip()
        if not client_id:
            self._record_error(source_file, "Header", "client_id fehlt im Header.")
            return False
        if client_id not in self._valid_client_ids:
            self._record_error(
                source_file,
                "FK-Fehler",
                f"client_id '{client_id}' existiert nicht in den Stammdaten (clients.client_id).",
            )
            return False

        employee_id = str(header.get("employee_id") or "").strip()
        if employee_id and employee_id not in self._valid_employee_ids:
            self._record_error(
                source_file,
                "FK-Fehler",
                f"employee_id '{employee_id}' existiert nicht in den Stammdaten (employees.emp_id).",
            )
            return False

        service_type = str(header.get("service_type") or "").strip()
        if not service_type:
            self._record_error(
                source_file,
                "FK-Fehler",
                "service_type konnte für den Client nicht aus den Stammdaten ermittelt werden.",
            )
            return False
        return True

    def _write_error_report(self) -> Optional[Path]:
        if not self._error_entries:
            return None
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_path = self.output_dir / f"timesheet_import_fehler_{stamp}.md"
        report_xlsx_path = self.output_dir / f"timesheet_import_fehler_{stamp}.xlsx"
        lines: List[str] = [
            "# Fehlerprotokoll Timesheet-Import",
            "",
            f"- Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Anzahl Fehler: {len(self._error_entries)}",
            "",
            "| Zeitpunkt | Datei | Zeile | Kategorie | Fehler |",
            "|---|---|---:|---|---|",
        ]
        for entry in self._error_entries:
            row_number = str(entry.row_number) if entry.row_number is not None else "-"
            safe_message = entry.message.replace("\n", " ").replace("|", "/")
            lines.append(
                f"| {entry.timestamp} | {entry.source_file} | {row_number} | {entry.category} | {safe_message} |"
            )
        report_path.write_text("\n".join(lines), encoding="utf-8")
        df_errors = pd.DataFrame(
            [
                {
                    "zeitpunkt": entry.timestamp,
                    "datei": entry.source_file,
                    "zeile": entry.row_number,
                    "kategorie": entry.category,
                    "fehler": entry.message,
                }
                for entry in self._error_entries
            ]
        )
        with pd.ExcelWriter(report_xlsx_path, engine="openpyxl") as writer:
            df_errors.to_excel(writer, sheet_name="fehlerprotokoll", index=False)

        logger.warning("Fehlerprotokoll geschrieben: {}", report_path)
        logger.warning("Fehlerprotokoll geschrieben: {}", report_xlsx_path)
        return report_path

    def discover_excel_files(self) -> List[Path]:
        files: List[Path] = []
        for path in sorted(p for p in self.source_dir.glob("*.xlsx") if p.is_file()):
            if self.masterdata_stem and path.stem.startswith(self.masterdata_stem):
                logger.info(f"Überspringe Stammdatendatei im Import: {path.name}")
                continue
            files.append(path)
        logger.info(f"{len(files)} Excel-Dateien entdeckt.")
        return files

    def _ensure_service_data_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS service_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            employee_id TEXT,
            service_date TEXT NOT NULL,
            service_type TEXT NOT NULL,
            travel_time REAL,
            travel_distance REAL,
            direct_time REAL,
            indirect_time REAL,
            notes TEXT,
            source_file TEXT,
            reporting_month TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(client_id),
            FOREIGN KEY (employee_id) REFERENCES employees(emp_id)
        )
        """
        deduplicate_sql = """
        DELETE FROM service_data
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM service_data
            GROUP BY client_id, service_date, employee_id
        )
        """
        drop_legacy_unique_index_sql = """
        DROP INDEX IF EXISTS idx_service_data_client_date
        """
        unique_index_sql = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_service_data_client_date_employee
        ON service_data (client_id, service_date, employee_id)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(sql)
            # Bestehende Dubletten bereinigen, bevor der eindeutige Index gesetzt wird.
            conn.execute(deduplicate_sql)
            conn.execute(drop_legacy_unique_index_sql)
            conn.execute(unique_index_sql)
            conn.commit()

    @staticmethod
    def _normalize_label(value: object) -> str:
        return " ".join(str(value or "").strip().lower().split())

    def _get_header_label(self, ws: Worksheet, column: str) -> str:
        row_idx = self.profile.table_range.start_row
        value = ws[f"{column}{row_idx}"].value
        return self._normalize_label(value)

    def _resolve_service_type(self, client_id: Optional[str]) -> Optional[str]:
        if not client_id:
            return None
        sql = """
        SELECT st.code
        FROM clients c
        LEFT JOIN service_types st ON c.service_type = st.service_type_id
        WHERE c.client_id = ?
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(sql, (client_id,)).fetchone()
        if row and row[0]:
            return str(row[0]).strip()
        return None

    def _resolve_employee_id(self, client_id: Optional[str]) -> Optional[str]:
        if not client_id:
            return None
        sql = "SELECT employee_id FROM clients WHERE client_id = ?"
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(sql, (client_id,)).fetchone()
        if row and row[0]:
            return str(row[0]).strip()
        return None

    def _determine_row_mapping(self, ws: Worksheet) -> Optional[tuple[RowMapping, bool]]:
        mp = self.profile.row_mapping

        def read_labels(expected: Dict[str, str]) -> Dict[str, str]:
            labels: Dict[str, str] = {}
            for key in expected:
                column = getattr(mp, key, None)
                if not column:
                    continue
                labels[key] = self._get_header_label(ws, column)
            return labels

        def matches(labels: Dict[str, str], expected: Dict[str, str]) -> bool:
            for key, expected_label in expected.items():
                column = getattr(mp, key, None)
                if not column:
                    continue
                if labels.get(key) != expected_label:
                    return False
            return True

        expected = {
            "service_time_col": "uhrzeit",
            "service_date_col": "datum",
            "travel_time_col": "fahrtzeit",
            "direct_time_col": "direkter fallkontakt",
            "indirect_time_col": "indirekte fallbearbeitung",
            "notes_col": "notizen",
        }
        if mp.travel_distance_col:
            expected["travel_distance_col"] = "km"
        if mp.billable_hours_col:
            expected["billable_hours_col"] = "stunden"

        labels = read_labels(expected)
        if matches(labels, expected):
            return mp, bool(mp.travel_distance_col)

        if mp.travel_distance_col and mp.billable_hours_col:
            legacy_labels = read_labels(self._HEADER_LABELS_NO_KM)
            if matches(legacy_labels, self._HEADER_LABELS_NO_KM):
                shifted = RowMapping(
                    service_time_col=mp.service_time_col,
                    service_date_col=mp.service_date_col,
                    travel_time_col=mp.travel_time_col,
                    travel_distance_col=mp.travel_distance_col,
                    direct_time_col=mp.travel_distance_col,
                    indirect_time_col=mp.direct_time_col,
                    billable_hours_col=mp.indirect_time_col,
                    notes_col=mp.billable_hours_col,
                )
                return shifted, False

        logger.error(
            "Header-Struktur nicht erkannt. Gefundene Labels: {}",
            labels,
        )
        return None

    def _read_header(self, ws: Worksheet) -> Dict[str, object]:
        cells = self.profile.header_cells
        employee_id = ws[cells.emp_id].value  # type: ignore[union-attr]
        client_id = ws[cells.client_id].value  # type: ignore[union-attr]
        allowed_hours = ws[cells.allowed_hours_per_month].value  # type: ignore[union-attr]

        client_id_str = str(client_id).strip() if client_id is not None else ""
        if not client_id_str:
            client_id_str = ""

        service_type = self._resolve_service_type(client_id_str or None)
        resolved_employee_id = self._resolve_employee_id(client_id_str or None)
        if not employee_id:
            employee_id = resolved_employee_id
        employee_id_str = str(employee_id).strip() if employee_id is not None else ""

        return {
            "employee_fullname": ws[cells.employee_name].value,  # type: ignore[union-attr]
            "employee_id": employee_id_str or None,
            "reporting_month": ws[cells.reporting_month].value,  # type: ignore[union-attr]
            "allowed_hours_per_month": allowed_hours,
            "service_type": service_type,
            "short_code": ws[cells.short_code].value,  # type: ignore[union-attr]
            "client_id": client_id_str or None,
        }

    def _read_rows(
        self,
        ws: Worksheet,
        header: Dict[str, object],
        row_mapping: RowMapping,
        has_travel_distance: bool,
        reporting_month: Optional[str],
        source_file: str,
    ) -> List[Dict[str, Any]]:
        rng = self.profile.table_range
        mp = row_mapping

        rows: List[Dict[str, Any]] = []
        for row_idx in range(rng.start_row, rng.end_row + 1):
            v_date = ws[f"{mp.service_date_col}{row_idx}"].value
            v_travel = ws[f"{mp.travel_time_col}{row_idx}"].value
            v_distance = (
                ws[f"{mp.travel_distance_col}{row_idx}"].value
                if has_travel_distance and mp.travel_distance_col
                else None
            )
            v_direct = ws[f"{mp.direct_time_col}{row_idx}"].value
            v_indirect = ws[f"{mp.indirect_time_col}{row_idx}"].value
            v_billable = ws[f"{mp.billable_hours_col}{row_idx}"].value if mp.billable_hours_col else None
            v_notes = ws[f"{mp.notes_col}{row_idx}"].value if mp.notes_col else None

            service_date = to_date(v_date)
            travel = to_float(v_travel) or 0.0
            distance = to_float(v_distance) or 0.0
            direct = to_float(v_direct) or 0.0
            indirect = to_float(v_indirect) or 0.0
            billable = to_float(v_billable)

            if service_date is None and (travel + direct + indirect) == 0.0:
                continue

            employee_id = header.get("employee_id")
            employee_id_str = str(employee_id).strip() if employee_id is not None else ""
            payload = {
                "client_id": str(header.get("client_id") or "").strip(),
                "employee_id": employee_id_str or "UNBEKANNT",
                "service_date": service_date or date.today(),
                "service_type": str(header.get("service_type") or "").strip(),
                "travel_time": travel,
                "direct_time": direct,
                "indirect_time": indirect,
                "billable_hours": billable,
            }

            try:
                validated = InvoiceRowModel(**payload)
                rows.append(
                    {
                        "client_id": validated.client_id,
                        "employee_id": employee_id_str or None,
                        "service_date": validated.service_date,
                        "service_type": validated.service_type,
                        "travel_time": validated.travel_time,
                        "travel_distance": distance,
                        "direct_time": validated.direct_time,
                        "indirect_time": validated.indirect_time,
                        "billable_hours": validated.billable_hours,
                        "notes": str(v_notes).strip() if v_notes is not None else None,
                        "source_file": source_file,
                        "reporting_month": reporting_month or "",
                        "_source_row": row_idx,
                    }
                )
            except ValidationError as exc:
                short_errors = "; ".join(
                    f"{'.'.join(str(loc) for loc in error.get('loc', []))}: {error.get('msg', 'ungültig')}"
                    for error in exc.errors()
                )
                self._record_error(
                    source_file,
                    "Validierung",
                    f"Validierungsfehler: {short_errors or str(exc)}",
                    row_number=row_idx,
                )

        return rows

    def _row_params(self, record: Dict[str, Any]) -> tuple[Any, ...]:
        data = record.copy()
        if isinstance(data.get("service_date"), date):
            data["service_date"] = data["service_date"].isoformat()
        return tuple(data.get(column) for column in self._INSERT_FIELDS)

    def _import_rows(self, rows: Iterable[Dict[str, Any]], source_file: str) -> tuple[int, List[Dict[str, Any]]]:
        sql = f"""
        INSERT INTO service_data (
            {", ".join(self._INSERT_FIELDS)}
        ) VALUES ({", ".join(["?"] * len(self._INSERT_FIELDS))})
        ON CONFLICT(client_id, service_date, employee_id) DO UPDATE SET
            employee_id = excluded.employee_id,
            service_type = excluded.service_type,
            travel_time = excluded.travel_time,
            travel_distance = excluded.travel_distance,
            direct_time = excluded.direct_time,
            indirect_time = excluded.indirect_time,
            notes = excluded.notes,
            source_file = excluded.source_file,
            reporting_month = excluded.reporting_month
        """
        count = 0
        imported_rows: List[Dict[str, Any]] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.cursor()
            for record in rows:
                try:
                    cur.execute(sql, self._row_params(record))
                    count += 1
                    imported_rows.append(record)
                except sqlite3.IntegrityError as exc:
                    self._record_error(
                        source_file,
                        "FK-Fehler",
                        f"Datenbank-Constraint verletzt: {exc}",
                        row_number=record.get("_source_row"),
                    )
                except sqlite3.DatabaseError as exc:
                    self._record_error(
                        source_file,
                        "DB-Fehler",
                        f"Zeile konnte nicht gespeichert werden: {exc}",
                        row_number=record.get("_source_row"),
                    )
            conn.commit()
        return count, imported_rows

    def _move_to_done(self, file_path: Path) -> Path:
        """
        Verschiebt die verarbeitete Datei in das Verzeichnis 'done'.
        Bei Namenskollision wird ein Zeitstempel angehängt.
        """
        target = self.done_dir / file_path.name
        if target.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = self.done_dir / f"{file_path.stem}_{stamp}{file_path.suffix}"
        file_path.replace(target)
        return target

    def _export_rows_to_excel(self, export_rows: List[ImportedRowExport], reporting_month: str) -> Path:
        """
        Schreibt alle importierten Zeilen als Sammeldatei ins Output-Verzeichnis.
        Stellt sicher, dass der Monatsname gesetzt ist; andernfalls wird der Fehler protokolliert
        und als ValueError weitergereicht.
        """
        if not reporting_month:
            logger.error("Export abgebrochen: reporting_month wurde nicht ermittelt.")
            raise ValueError("reporting_month darf für den Export nicht leer sein.")
        out_file = self.output_dir / f"importierte_daten_{reporting_month}.xlsx"
        df = pd.DataFrame(
            [
                {
                    **row.model_dump(exclude={"service_date"}),
                    "service_date": row.service_date.isoformat(),
                }
                for row in export_rows
            ]
        )
        with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="importierte_daten", index=False)
        logger.info(f"Export-Datei geschrieben: {out_file}")
        return out_file

    def process_file(self, file_path: Path) -> tuple[int, Path, List[ImportedRowExport], Optional[str]]:
        logger.info(f"Verarbeite: {file_path.name}")
        try:
            wb = load_workbook(file_path, data_only=True)
        except Exception as exc:
            self._record_error(file_path.name, "Datei", f"Datei konnte nicht gelesen werden: {exc}")
            return 0, file_path, [], None
        if self.profile.sheet_name:
            if self.profile.sheet_name not in wb.sheetnames:
                self._record_error(
                    file_path.name,
                    "Struktur",
                    f"Sheet '{self.profile.sheet_name}' fehlt in der Datei.",
                )
                return 0, file_path, [], None
            ws = wb[self.profile.sheet_name]
        else:
            ws = wb.active
            if ws is None:
                self._record_error(file_path.name, "Struktur", "Kein aktives Sheet gefunden.")
                return 0, file_path, [], None

        header = self._read_header(ws)
        month_str = to_year_month_str(header.get("reporting_month"))
        mapping = self._determine_row_mapping(ws)
        if mapping is None:
            self._record_error(file_path.name, "Struktur", "Header-Struktur ungültig.")
            return 0, file_path, [], month_str
        row_mapping, has_travel_distance = mapping

        if not self._validate_header_foreign_keys(header, file_path.name):
            logger.warning("Datei {} wegen Header-/FK-Fehlern übersprungen.", file_path.name)
            return 0, file_path, [], month_str

        if not header.get("employee_id"):
            logger.warning("employee_id fehlt im Header – Import erfolgt ohne employee_id ({})", file_path.name)

        logger.info(
            "Header: client_id={}, employee_id={}, service_type={}, month={}",
            header.get("client_id"),
            header.get("employee_id"),
            header.get("service_type"),
            month_str or header.get("reporting_month"),
        )

        rows = self._read_rows(ws, header, row_mapping, has_travel_distance, month_str, file_path.name)
        if not rows:
            logger.warning("Keine importierbaren Zeilen in {} gefunden – Datei bleibt im Import.", file_path.name)
            return 0, file_path, [], month_str

        imported_count, imported_rows = self._import_rows(rows, file_path.name)
        if imported_count == 0:
            logger.warning("Keine gültigen Zeilen aus {} gespeichert – Datei bleibt im Import.", file_path.name)
            return 0, file_path, [], month_str
        moved = self._move_to_done(file_path)

        export_rows = [
            ImportedRowExport(**{k: v for k, v in row.items() if k != "_source_row"}) for row in imported_rows
        ]

        logger.info(f"{imported_count} Zeilen importiert aus {file_path.name}. Verschoben nach {moved.name}")
        return imported_count, moved, export_rows, month_str

    def run(self, reporting_month: Optional[str] = None) -> int:
        """
        Führt den Batch-Import aus und schreibt eine Sammel-Excel-Datei ins Output-Verzeichnis:
        output/importierte_daten_{reporting_month}.xlsx

        - Wenn reporting_month None ist, wird er aus der ersten verarbeiteten Datei (Header) abgeleitet.
        - Gibt die Gesamtanzahl importierter Zeilen zurück.
        """
        files = self.discover_excel_files()
        total = 0
        all_export_rows: List[ImportedRowExport] = []
        derived_month: Optional[str] = reporting_month

        for file_path in files:
            try:
                count, _, export_rows, month_str = self.process_file(file_path)
                total += count
                all_export_rows.extend(export_rows)
                if derived_month is None and month_str:
                    derived_month = month_str
            except ValueError as err:
                self._record_error(file_path.name, "Struktur", str(err))
            except Exception as exc:
                self._record_error(file_path.name, "Unerwartet", f"Datei konnte nicht verarbeitet werden: {exc}")

        logger.info(f"Batch abgeschlossen. Gesamt importiert: {total}")

        if all_export_rows:
            if not derived_month:
                derived_month = datetime.now().strftime("%Y-%m")
                logger.warning(
                    "reporting_month nicht bestimmbar – verwende {} für den Export-Dateinamen.",
                    derived_month,
                )
            self._export_rows_to_excel(all_export_rows, derived_month)
        self._write_error_report()

        return total


def main() -> None:
    """
    Einstiegspunkt:
    - Lädt zentrale Config (Pydantic-validiert).
    - Initialisiert Importer.
    - Führt den Batch-Import aus und schreibt Sammel-Excel ins Output-Verzeichnis.
    """
    config_path = Path(__file__).parents[2] / ".config" / "wegpiraten_config.yaml"
    config = Config(config_path)  # Singleton, lädt und validiert, setzt Logging

    importer = TimeSheetsImporter(config)
    importer.run()  # optional: importer.run("2025-10")


if __name__ == "__main__":
    main()
