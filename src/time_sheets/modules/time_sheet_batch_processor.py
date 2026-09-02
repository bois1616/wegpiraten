from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger

from pydantic_models.data.header_data_model import HeaderDataModel
from shared_modules.config import Config
from shared_modules.internal_client import INTERNAL_CLIENT_ID
from shared_modules.utils import ensure_dir
from time_sheets.modules.client_data import (
    ClientEmployeePairStatus,
    build_pair_diagnostics,
    load_active_client_headers,
    load_internal_timesheet_headers,
)
from time_sheets.modules.time_sheet_factory import TimeSheetFactory


class TimeSheetBatchProcessor:
    """
    Erzeugt Arbeitszeiterfassungs-Sheets für einen Monat.
    Nutzt das statische HeaderDataModel für Validierung und IDE-Unterstützung.
    """

    def __init__(self, config: Config, reporting_factory: TimeSheetFactory):
        self.config: Config = config
        self.reporting_factory: TimeSheetFactory = reporting_factory

        structure = self.config.structure
        prj_root = Path(structure.prj_root)

        self.output_dir: Path = ensure_dir(prj_root / (structure.output_path or "output"))
        self.template_dir: Path = ensure_dir(prj_root / (structure.template_path or "templates"))
        self.log_dir: Path = ensure_dir(prj_root / (getattr(structure, "log_path", None) or ".logs"))

        data_dir = prj_root / (structure.local_data_path or "data")
        self.db_path: Path = data_dir / self.config.database.sqlite_db_name

    def get_sheet_password(self) -> str:
        """
        Holt das Excel-Blattschutz-Passwort sicher aus der Umgebung (.env), entschlüsselt falls nötig.
        Gibt SHEET_PASSWORD_ENC (verschlüsselt) oder SHEET_PASSWORD (Klartext) zurück.

        Returns:
            str: Das entschlüsselte oder im Klartext gespeicherte Passwort.

        Raises:
            RuntimeError: Wenn kein Passwort gefunden werden kann.
        """
        pw = self.config.get_decrypted_secret("SHEET_PASSWORD_ENC")
        if not pw:
            pw = self.config.get_secret("SHEET_PASSWORD")
        if not pw:
            logger.error(
                "Excel-Blattschutz-Passwort nicht gesetzt! Bitte .env mit SHEET_PASSWORD_ENC oder SHEET_PASSWORD anlegen."
            )
            raise RuntimeError("Excel-Blattschutz-Passwort fehlt.")
        return pw

    def load_client_data(self, reporting_month: str) -> List[HeaderDataModel]:
        """
        Lädt alle im Monat aktiven Clients mitsamt Mitarbeiterdaten
        sowie die Sonstige-Aufwände-Datensätze für MA mit TS=WAHR.
        """
        client_headers = load_active_client_headers(self.db_path, reporting_month)
        internal_headers = load_internal_timesheet_headers(self.db_path)
        return client_headers + internal_headers

    def _write_pair_report(
        self,
        pair_diagnostics: List[ClientEmployeePairStatus],
        creation_status: Dict[Tuple[str, str], Tuple[bool, str]],
        internal_created: int,
        internal_total: int,
        reporting_month: str,
    ) -> Path:
        """
        Schreibt einen Report (Markdown + xlsx) über JEDES Klient-Mitarbeiter-Paar
        aus relation_client_emp: ob dafür ein Timesheet erzeugt wurde, und falls
        nicht, aus welchem Grund. Klärt Abweichungen zwischen "Anzahl Paare" und
        "Anzahl erzeugter Timesheets" eindeutig, analog zum Fehlerprotokoll des
        Timesheet-Imports.
        """
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_path = self.log_dir / f"timesheet_generierung_{reporting_month}_{stamp}.md"
        report_xlsx_path = self.log_dir / f"timesheet_generierung_{reporting_month}_{stamp}.xlsx"

        rows: List[Dict[str, object]] = []
        created_count = 0
        for entry in pair_diagnostics:
            if entry.included:
                success, detail = creation_status.get(
                    (entry.client_id, entry.employee_id), (False, "nicht verarbeitet")
                )
                status = "Erstellt" if success else "Fehler bei Erstellung"
                reason = detail
                if success:
                    created_count += 1
            else:
                status = "Übersprungen"
                reason = "; ".join(entry.reasons)
            rows.append(
                {
                    "client_id": entry.client_id,
                    "employee_id": entry.employee_id,
                    "klient": entry.client_name,
                    "mitarbeiter": entry.employee_name,
                    "status": status,
                    "begruendung": reason,
                }
            )

        lines: List[str] = [
            "# Timesheet-Generierung Report",
            "",
            f"- Erfassungsmonat: {reporting_month}",
            f"- Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Klient-Mitarbeiter-Paare gesamt (relation_client_emp): {len(pair_diagnostics)}",
            f"- davon Timesheet erzeugt: {created_count}",
            f"- davon übersprungen/fehlgeschlagen: {len(pair_diagnostics) - created_count}",
            f"- Sonstige-Aufwendungen-Timesheets erzeugt (employees.ts, nicht in Tabelle unten): "
            f"{internal_created}/{internal_total}",
            f"- **Gesamt erzeugte Timesheet-Dateien: {created_count + internal_created}** "
            f"({created_count} Klient-Paare + {internal_created} Sonstige Aufwendungen)",
            "",
            "| client_id | employee_id | Klient | Mitarbeiter | Status | Begründung |",
            "|---|---|---|---|---|---|",
        ]
        for row in rows:
            begruendung = str(row["begruendung"]).replace("\n", " ").replace("|", "/")
            lines.append(
                f"| {row['client_id']} | {row['employee_id']} | {row['klient']} | {row['mitarbeiter']} | "
                f"{row['status']} | {begruendung} |"
            )
        report_path.write_text("\n".join(lines), encoding="utf-8")

        df_report = pd.DataFrame(rows)
        with pd.ExcelWriter(report_xlsx_path, engine="openpyxl") as writer:
            df_report.to_excel(writer, sheet_name="timesheet_generierung", index=False)

        logger.info("Generierungs-Report geschrieben: {}", report_path)
        logger.info("Generierungs-Report geschrieben: {}", report_xlsx_path)
        return report_path

    def run(
        self, reporting_month: str, output_path: Optional[Path] = None, template_path: Optional[Path] = None
    ) -> None:
        target_output = ensure_dir(output_path or self.output_dir)
        target_template = template_path or self.template_dir

        reporting_month_dt = datetime.strptime(reporting_month, "%Y-%m")
        pair_diagnostics = build_pair_diagnostics(self.db_path, reporting_month)
        header_data = self.load_client_data(reporting_month)
        sheet_password = self.get_sheet_password()

        creation_status: Dict[Tuple[str, str], Tuple[bool, str]] = {}
        internal_created = 0
        internal_total = 0

        for header_record in header_data:
            is_internal = header_record.client_id == INTERNAL_CLIENT_ID
            internal_total += 1 if is_internal else 0
            try:
                filename = self.reporting_factory.create_reporting_sheet(
                    header_data=header_record,
                    reporting_month_dt=reporting_month_dt,
                    output_path=target_output,
                    template_path=target_template,
                    sheet_password=sheet_password,
                )
                logger.info(
                    "AZ-Erfassungsbogen erzeugt für {employee} ({short_code}, Client-ID: {client_id}) -> {file}".format(
                        employee=f"{header_record.employee_first_name or ''} {header_record.employee_last_name or ''}".strip(),
                        short_code=header_record.short_code,
                        client_id=header_record.client_id,
                        file=filename,
                    )
                )
                if is_internal:
                    internal_created += 1
                else:
                    creation_status[(header_record.client_id, header_record.employee_id)] = (True, filename.name)
            except Exception as exc:
                logger.error(f"Fehler beim Erstellen des Sheets für Client {header_record.client_id}: {exc}")
                if not is_internal:
                    creation_status[(header_record.client_id, header_record.employee_id)] = (False, str(exc))

        self._write_pair_report(
            pair_diagnostics,
            creation_status,
            internal_created=internal_created,
            internal_total=internal_total,
            reporting_month=reporting_month,
        )


if __name__ == "__main__":
    config_path = Path(__file__).parents[3] / ".config" / "wegpiraten_config.yaml"
    config = Config(config_path)
    factory = TimeSheetFactory(config)
    processor = TimeSheetBatchProcessor(config, factory)
    processor.run("2025-08")
