from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger

from pydantic_models.data.header_data_model import HeaderDataModel
from shared_modules.config import Config
from shared_modules.utils import ensure_dir
from time_sheets.modules.client_data import load_active_client_headers
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
        und validiert sie gegen HeaderDataModel.
        """
        return load_active_client_headers(self.db_path, reporting_month)

    def run(
        self, reporting_month: str, output_path: Optional[Path] = None, template_path: Optional[Path] = None
    ) -> None:
        target_output = ensure_dir(output_path or self.output_dir)
        target_template = template_path or self.template_dir

        reporting_month_dt = datetime.strptime(reporting_month, "%Y-%m")
        header_data = self.load_client_data(reporting_month)
        sheet_password = self.get_sheet_password()

        for header_record in header_data:
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
            except Exception as exc:
                logger.error(f"Fehler beim Erstellen des Sheets für Client {header_record.client_id}: {exc}")


if __name__ == "__main__":
    config_path = Path(__file__).parents[3] / ".config" / "wegpiraten_config.yaml"
    config = Config(config_path)
    factory = TimeSheetFactory(config)
    processor = TimeSheetBatchProcessor(config, factory)
    processor.run("2025-08")
