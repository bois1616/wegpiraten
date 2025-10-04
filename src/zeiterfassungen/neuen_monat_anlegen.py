from pathlib import Path

# Importiere die zentrale Konfiguration und das Strukturmodell aus dem shared_modules-Paket.
from shared_modules.config import Config, StructureConfig

# Importiere die benötigten Klassen für die Berichtserstellung und -verarbeitung.
from modules.reporting_factory import ReportingFactory, ReportingFactoryConfig
from modules.reporting_processor import ReportingConfig, ReportingProcessor


def main() -> None:
    """
    Einstiegspunkt für das Anlegen eines neuen Berichtsmonats.
    Lädt die Konfiguration (validiert mit Pydantic), initialisiert Factory und Processor
    und startet die Verarbeitung. Nutzt ausschließlich Pydantic-Modelle für Konfiguration.
    """
    # Pfad zur YAML-Konfigurationsdatei bestimmen (typisiert mit pathlib.Path)
    config_path: Path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config: Config = Config()
    config.load(config_path)  # Lädt und validiert die Konfiguration, initialisiert Logger

    # Zugriff auf die Struktur-Konfiguration über das Pydantic-Modell
    structure: StructureConfig = config.get_structure()

    # Die Pfade werden direkt aus dem Pydantic-Modell gelesen
    prj_root: Path = Path(structure.prj_root)
    output_path: Path = prj_root / (structure.output_path or "output")
    template_path: Path = prj_root / (structure.template_path or "templates")

    reporting_month: str = "2025-10"  # Beispiel: September 2025

    # TODO: Erweiterung: ReportingFactory- und ReportingProcessor-Konfiguration auslagern
    # Diese Blöcke prüfen, ob die Konfiguration in der Hauptkonfiguration vorhanden ist,
    # und nutzen ansonsten Defaultwerte der jeweiligen Pydantic-Modelle.

    # ReportingFactoryConfig aus der Hauptkonfiguration extrahieren (falls vorhanden)
    # Die Konfiguration wird als dict ausgelesen und als Pydantic-Modell instanziiert
    factory_config_data: dict = getattr(config.data, "reporting_factory", {})
    factory_config: ReportingFactoryConfig = ReportingFactoryConfig(**factory_config_data)
    factory: ReportingFactory = ReportingFactory(factory_config)

    # ReportingConfig aus der Hauptkonfiguration extrahieren (falls vorhanden)
    # Die Struktur wird aus der Hauptkonfiguration übernommen und als Pydantic-Modell übergeben
    reporting_config_data: dict = getattr(config.data, "reporting_processor", {})
    reporting_config_data["structure"] = structure
    # db_name aus der globalen Konfiguration ergänzen, falls nicht vorhanden
    if "db_name" not in reporting_config_data:
        reporting_config_data["db_name"] = getattr(config.data, "db_name", "Wegpiraten Datenbank.xlsx")
    reporting_config: ReportingConfig = ReportingConfig(**reporting_config_data)
    processor: ReportingProcessor = ReportingProcessor(reporting_config, factory)

    # Ausführung der Verarbeitung mit typisierten Pfaden und Monat
    processor.run(reporting_month, output_path, template_path)


if __name__ == "__main__":
    main()