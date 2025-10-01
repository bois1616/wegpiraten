from pathlib import Path

from module.config import Config
from module.reporting_factory import ReportingFactory, ReportingFactoryConfig
from module.reporting_processor import ReportingProcessor, ReportingConfig, StructureConfig

def main() -> None:
    """
    Einstiegspunkt für das Anlegen eines neuen Berichtsmonats.
    Lädt die Konfiguration (validiert mit Pydantic), initialisiert Factory und Processor
    und startet die Verarbeitung. Nutzt ausschließlich Pydantic-Modelle für Konfiguration.
    """
    # Pfad zur YAML-Konfigurationsdatei bestimmen (typisiert mit pathlib.Path)
    config_path: Path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config: Config = Config()
    config.load(config_path)

    # Zugriff auf die Struktur-Konfiguration über das Pydantic-Modell
    structure: StructureConfig = config.get_structure()

    # Die Pfade werden direkt aus dem Pydantic-Modell gelesen
    prj_root: Path = Path(structure.prj_root)
    output_path: Path = prj_root / (structure.output_path or "output")
    template_path: Path = prj_root / (structure.template_path or "templates")

    reporting_month: str = "2025-09"  # Beispiel: September 2025

    # Erweiterung: ReportingFactory- und ReportingProcessor-Konfiguration auslagern
    # Diese Blöcke prüfen, ob die Konfiguration in der Hauptkonfiguration vorhanden ist,
    # und nutzen ansonsten Defaultwerte der jeweiligen Pydantic-Modelle.

    # ReportingFactoryConfig aus der Hauptkonfiguration extrahieren (falls vorhanden)
    factory_config_data: dict = getattr(config.data, "reporting_factory", {})
    factory_config: ReportingFactoryConfig = ReportingFactoryConfig(**factory_config_data)
    factory: ReportingFactory = ReportingFactory(factory_config)

    # ReportingConfig aus der Hauptkonfiguration extrahieren (falls vorhanden)
    reporting_config_data: dict = getattr(config.data, "reporting_processor", {})
    # Die Struktur wird aus der Hauptkonfiguration übernommen
    reporting_config_data["structure"] = structure
    reporting_config: ReportingConfig = ReportingConfig(**reporting_config_data)
    processor: ReportingProcessor = ReportingProcessor(reporting_config, factory)

    # Ausführung der Verarbeitung
    processor.run(reporting_month, output_path, template_path)

if __name__ == "__main__":
    main()