from pathlib import Path
from module.config import Config
from module.reporting_factory import ReportingFactory, ReportingFactoryConfig
from module.reporting_processor import ReportingProcessor, ReportingConfig

def main():
    # Pfad zur YAML-Konfigurationsdatei bestimmen
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config = Config()
    config.load(config_path)

    # Zugriff auf die Konfigurationsdaten erfolgt jetzt typisiert über das Pydantic-Modell
    structure = config.get_structure()  # Gibt ein StructureConfig-Pydantic-Modell zurück

    # Die Pfade werden direkt aus dem Pydantic-Modell gelesen
    prj_root = Path(structure.prj_root)
    output_path = prj_root / getattr(structure, "output_path", "output")  # Fallback falls output_path nicht gesetzt
    template_path = prj_root / getattr(structure, "template_path", "templates")  # Fallback falls template_path nicht gesetzt

    reporting_month = "2025-09"  # Beispiel: September 2025

    # Initialisierung der ReportingFactory mit Pydantic-Konfiguration
    # Annahme: Die Factory-Konfiguration ist Teil der Hauptkonfiguration oder wird separat geladen
    # Hier als Beispiel aus der Hauptkonfiguration extrahiert:
    factory_config_data = getattr(config.data, "reporting_factory", {})
    factory_config = ReportingFactoryConfig(**factory_config_data)
    factory = ReportingFactory(factory_config)

    # Initialisierung des ReportingProcessors mit Pydantic-Konfiguration
    # Annahme: Die Reporting-Konfiguration ist Teil der Hauptkonfiguration oder wird separat geladen
    reporting_config_data = getattr(config.data, "reporting_processor", {})
    # Die Struktur wird aus der Hauptkonfiguration übernommen
    reporting_config_data["structure"] = structure
    reporting_config = ReportingConfig(**reporting_config_data)
    processor = ReportingProcessor(reporting_config, factory)

    # Ausführung der Verarbeitung
    processor.run(reporting_month, output_path, template_path)

if __name__ == "__main__":
    main()