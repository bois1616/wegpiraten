from pathlib import Path
from loguru import logger

from shared_modules.config import Config
from zeiterfassungen.modules.reporting_factory import ReportingFactory
from zeiterfassungen.modules.reporting_processor import ReportingProcessor


def main() -> None:
    """
    Einstiegspunkt für das Anlegen eines neuen Berichtsmonats.
    Lädt die zentrale Konfiguration (validiert mit Pydantic), initialisiert Factory und Processor
    und startet die Verarbeitung. Nutzt ausschließlich Pydantic-Modelle für Konfiguration und Daten.
    Die Datenquelle ist die SQLite-Datenbank aus der Konfiguration.
    """

    # Pfad zur YAML-Konfigurationsdatei bestimmen
    config_path: Path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config: Config = Config(config_path)  # Singleton, lädt und validiert die Konfiguration, initialisiert Logger

    # Zugriff auf die Struktur-Konfiguration über das Pydantic-Modell
    structure = config.structure
    assert structure.prj_root, "Projektwurzel fehlt in der Config!"

    # Die Pfade werden direkt aus dem Pydantic-Modell gelesen
    prj_root: Path = Path(structure.prj_root)
    output_path: Path = prj_root / (structure.output_path or "output")
    template_path: Path = prj_root / (structure.template_path or "templates")
    local_data_path: Path = prj_root / (structure.local_data_path or "data")

    # Zugriff auf die SQLite-Datenbank aus der Konfiguration
    db_name: str = config.database.sqlite_db_name
    assert db_name, "SQLite-Datenbankname fehlt in der Config!"
    db_path: Path = local_data_path / db_name
    assert db_path.exists(), f"SQLite-Datenbank nicht gefunden: {db_path}"

    # Initialisiere die Factory und den Processor mit der geprüften Config
    factory = ReportingFactory(config)
    processor = ReportingProcessor(config, factory)

    # Monat für die Erfassungsbögen festlegen (z.B. als YYYY-MM)
    reporting_month: str = "2025-10"

    # Ausführung der Verarbeitung mit typisierten Pfaden und Monat
    processor.run(reporting_month, output_path, template_path)


if __name__ == "__main__":
    main()

"""
Vorschläge für weitere Modelle:
- Ein Modell für die Monats-Konfiguration (z.B. MonthConfig), das alle relevanten Einstellungen für einen Berichtsmonat kapselt.
- Ein Modell für die Reporting-Parameter (z.B. ReportingParams), um alle Laufzeitparameter typisiert zu übergeben.
- Ein Modell für die Ergebnisstruktur (z.B. ReportingResult), um die erzeugten Dateien und Statusmeldungen zu kapseln.
- Ein Modell für die Fehlerbehandlung (z.B. ErrorReport), um Fehler strukturiert zu erfassen und zu reporten.
"""