import sys
from pathlib import Path
from loguru import logger

# Importiere die Pydantic-basierten Konfigurations- und Prozessorklassen
from module.config import Config  # Pydantic-basierte Singleton-Konfiguration
from module.invoice_processor import InvoiceProcessor  # Erwartet Pydantic-Konfiguration
from module.invoice_filter import InvoiceFilter  # Erwartet typisierte Filterdaten


def main() -> None:
    """
    Einstiegspunkt für den Rechnungsprozess.
    Lädt die Konfiguration (validiert mit Pydantic), initialisiert Filter und startet die Verarbeitung.
    Nutzt ausschließlich Pydantic-Modelle für Konfiguration und Filter.
    """
    # Pfad zur YAML-Konfigurationsdatei bestimmen (typisiert mit pathlib.Path)
    config_path: Path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"

    # Abrechnungsmonat als Argument übergeben
    # TODO: Später über GUI oder Web-Formular ein ganzes Filter-Objekt übergeben
    if len(sys.argv) > 1:
        invoice_month: str = sys.argv[1]
    else:
        print("Bitte Abrechnungsmonat als Argument übergeben (z.B. 08.2025)")
        invoice_month = "08.2025"
        # sys.exit(1)

    # Filter-Objekt für die Rechnungsverarbeitung (kann später erweitert werden)
    filter_obj: InvoiceFilter = InvoiceFilter(invoice_month=invoice_month)

    # Konfiguration laden und validieren (Pydantic übernimmt die Validierung)
    config_obj: Config = Config()
    config_obj.load(config_path)

    # Zugriff auf die Struktur-Konfiguration über das Pydantic-Modell
    structure = config_obj.get_structure()  # Gibt ein StructureConfig-Pydantic-Modell zurück

    # Log-Verzeichnis und Logdatei konfigurieren, Pfade werden typisiert ausgelesen
    if structure.logs is None:
        raise ValueError("structure.logs darf nicht None sein!")
    logs_dir: Path = Path(structure.prj_root) / structure.logs
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file: Path = logs_dir / "Rechnung.log"

    # Loguru-Konfiguration: Logdatei im gewünschten Verzeichnis und Konsolenausgabe
    logger.add(str(log_file), rotation="10 MB", retention="10 days", level="INFO")
    logger.info("Starte Rechnungsprozess...")

    try:
        # Die Entitäten und erwarteten Spalten werden jetzt segmentiert aus der config geladen
        # InvoiceProcessor erhält die validierte Pydantic-Konfiguration
        processor: InvoiceProcessor = InvoiceProcessor(config=config_obj, filter=filter_obj)
        processor.run()
        logger.success("Rechnungsprozess erfolgreich abgeschlossen.")
    except Exception as e:
        logger.exception(f"Fehler im Rechnungsprozess: {e}")


if __name__ == "__main__":
    main()


