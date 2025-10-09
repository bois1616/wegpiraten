# importiere ein Batch von reporting sheets in die Datenbank
# nutzt die config.py für die Pfade
# Die Daten werden in invoice_data gespeichert, ohne Rechnungsnummer
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
# timesheet_entries, wenn invoice_data bereits Rechnungsbelege abbildet.
#  Alternativ kann invoice_data als staging genutzt werden und ein nachgelagerter 
# Prozess normalisiert in ein Faktentableau.

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import sqlite3
from loguru import logger
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, ValidationError

from pydantic_models.data.invoice_row_model import InvoiceRowModel
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
    direct_time: float
    indirect_time: float
    billable_hours: float
    hourly_rate: Optional[float] = None
    total_hours: Optional[float] = None
    total_costs: Optional[float] = None


class TimeSheetsImporter:
    """
    Liest ausgefüllte Aufwandserfassungs-Sheets, validiert jede Positionszeile
    gegen InvoiceRowModel, schreibt sie in die SQLite-DB und exportiert zusätzlich
    eine Sammeldatei der importierten Daten.
    """

    _INSERT_FIELDS: tuple[str, ...] = (
        "client_id",
        "employee_id",
        "service_date",
        "service_type",
        "travel_time",
        "direct_time",
        "indirect_time",
        "billable_hours",
        "hourly_rate",
        "total_hours",
        "total_costs",
    )
    

    def __init__(self, config: Config, profile: Optional[TimeSheetImportProfile] = None):
        self.config = config
        self.profile = profile or self._build_profile_from_config(config)

        prj_root = Path(self.config.structure.prj_root)
        data_dir = prj_root / (getattr(self.config.structure, "local_data_path", None) or "data")
        self.db_path = data_dir / self.config.database.sqlite_db_name
        self.output_dir = ensure_dir(prj_root / (getattr(self.config.structure, "output_path", None) or "output"))

        cfg_imports_path = (
            getattr(self.config.structure, "imports_path", None)
            or self.config.get("structure.imports_path", None)
        )
        default_windows = Path(r"C:\Users\micro\OneDrive\Shared\Beatus\Wegpiraten Unterlagen\data_imports")
        fallback_local = prj_root / "data_imports"

        # Kandidatenliste: nimm den ersten existierenden Pfad
        candidates: List[Optional[Path]] = [
            Path(cfg_imports_path) if cfg_imports_path else None,
            default_windows,
            fallback_local,
        ]
        self.source_dir = ensure_dir(choose_existing_path(candidates, fallback_local))
        self.imported_dir = ensure_dir(self.source_dir / "importiert")

        logger.info(f"DB: {self.db_path}")
        logger.info(f"Quelle: {self.source_dir}")
        logger.info(f"Importiert-Ordner: {self.imported_dir}")
        logger.info(
            f"Sheet: {self.profile.sheet_name}, Range: "
            f"{self.profile.table_range.start_row}-{self.profile.table_range.end_row}"
        )

    @staticmethod
    def _build_profile_from_config(config: Config) -> TimeSheetImportProfile:
        return TimeSheetImportProfile.from_config(config.templates)

    def discover_excel_files(self) -> List[Path]:
        files = sorted(p for p in self.source_dir.glob("*.xlsx") if p.is_file())
        logger.info(f"{len(files)} Excel-Dateien entdeckt.")
        return files

    def _read_header(self, ws: Worksheet) -> Dict[str, object]:
        cells = self.profile.header_cells
        return {
            "employee_fullname": ws[cells.employee_name].value,
            "employee_id": ws[cells.emp_id].value,
            "reporting_month": ws[cells.reporting_month].value,
            "allowed_hours_per_month": ws[cells.allowed_hours_per_month].value,
            "service_type": ws[cells.service_type].value,
            "short_code": ws[cells.short_code].value,
            "client_id": ws[cells.client_id].value,
        }

    def _read_rows(self, ws: Worksheet, header: Dict[str, object]) -> List[InvoiceRowModel]:
        rng = self.profile.table_range
        mp = self.profile.row_mapping

        rows: List[InvoiceRowModel] = []
        for row_idx in range(rng.start_row, rng.end_row + 1):
            v_date = ws[f"{mp.service_date_col}{row_idx}"].value
            v_travel = ws[f"{mp.travel_time_col}{row_idx}"].value
            v_direct = ws[f"{mp.direct_time_col}{row_idx}"].value
            v_indirect = ws[f"{mp.indirect_time_col}{row_idx}"].value
            v_billable = ws[f"{mp.billable_hours_col}{row_idx}"].value

            service_date = to_date(v_date)
            travel = to_float(v_travel) or 0.0
            direct = to_float(v_direct) or 0.0
            indirect = to_float(v_indirect) or 0.0
            billable = to_float(v_billable)

            if service_date is None and (travel + direct + indirect) == 0.0:
                continue

            payload = {
                "client_id": str(header.get("client_id") or "").strip(),
                "employee_id": str(header.get("employee_id") or "").strip(),
                "service_date": service_date or date.today(),
                "service_type": str(header.get("service_type") or "").strip(),
                "travel_time": travel,
                "direct_time": direct,
                "indirect_time": indirect,
                "billable_hours": billable,
            }

            try:
                rows.append(InvoiceRowModel(**payload))
            except ValidationError as exc:
                logger.error(f"Zeile {row_idx}: Validierungsfehler: {exc}")

        return rows

    def _row_params(self, record: InvoiceRowModel) -> tuple[Any, ...]:
        data = record.model_dump()
        data["service_date"] = record.service_date.isoformat()
        return tuple(data.get(column) for column in self._INSERT_FIELDS)

    def _import_rows(self, rows: Iterable[InvoiceRowModel]) -> int:
        sql = f"""
        INSERT INTO invoice_data (
            {', '.join(self._INSERT_FIELDS)}
        ) VALUES ({', '.join(['?'] * len(self._INSERT_FIELDS))})
        """
        count = 0
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            try:
                for record in rows:
                    cur.execute(sql, self._row_params(record))
                    count += 1
                conn.commit()
            except Exception:
                conn.rollback()
                logger.exception("Import fehlgeschlagen, Transaktion zurückgerollt.")
                raise
        return count

    def _move_to_imported(self, file_path: Path) -> Path:
        """
        Verschiebt die verarbeitete Datei in das Unterverzeichnis 'importiert'.
        Bei Namenskollision wird ein Zeitstempel angehängt.
        """
        target = self.imported_dir / file_path.name
        if target.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = self.imported_dir / f"{file_path.stem}_{stamp}{file_path.suffix}"
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
        wb = load_workbook(file_path, data_only=True)
        if self.profile.sheet_name:
            assert self.profile.sheet_name in wb.sheetnames, f"Sheet '{self.profile.sheet_name}' fehlt in {file_path.name}."
            ws = wb[self.profile.sheet_name]
        else:
            ws = wb.active

        header = self._read_header(ws)
        month_str = to_year_month_str(header.get("reporting_month"))

        # Minimalprüfung Header (prüfe einmal und dann traue)
        assert header.get("client_id"), f"client_id im Header fehlt ({file_path.name})"
        assert header.get("employee_id"), f"employee_id im Header fehlt ({file_path.name})"
        assert header.get("service_type") is not None, f"service_type im Header fehlt ({file_path.name})"

        logger.info(
            "Header: client_id=%s, employee_id=%s, service_type=%s, month=%s",
            header.get("client_id"),
            header.get("employee_id"),
            header.get("service_type"),
            month_str or header.get("reporting_month"),
        )

        rows = self._read_rows(ws, header)
        if not rows:
            logger.warning(f"Keine importierbaren Zeilen in {file_path.name} gefunden.")
            moved = self._move_to_imported(file_path)
            return 0, moved, [], month_str

        imported_count = self._import_rows(rows)
        moved = self._move_to_imported(file_path)

        export_rows = [
            ImportedRowExport(
                reporting_month=month_str or "",
                source_file=file_path.name,
                **row.model_dump(),
            )
            for row in rows
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
            except AssertionError as err:
                logger.error(f"Plausibilitätsfehler bei {file_path.name}: {err}")
            except Exception as exc:
                logger.exception(f"Unerwarteter Fehler bei {file_path.name}: {exc}")

        logger.info(f"Batch abgeschlossen. Gesamt importiert: {total}")

        if all_export_rows:
            if not derived_month:
                derived_month = datetime.now().strftime("%Y-%m")
                logger.warning(
                    "reporting_month nicht bestimmbar – verwende %s für den Export-Dateinamen.",
                    derived_month,
                )
            self._export_rows_to_excel(all_export_rows, derived_month)

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