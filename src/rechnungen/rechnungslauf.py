import sys
from pathlib import Path
from loguru import logger

from module import Config, InvoiceProcessor, InvoiceFilter



def main():
    """
    Einstiegspunkt für den Rechnungsprozess.
    Lädt die Konfiguration, initialisiert Filter und startet die Verarbeitung.
    """
    # Pfad zur YAML-Konfigurationsdatei bestimmen
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"

    # Abrechnungsmonat als Argument übergeben
    # TODO: Später über GUI oder Web-Formular ein ganzes Filter-Objekt übergeben

    if len(sys.argv) > 1:
        invoice_month = sys.argv[1]
    else:
        print("Bitte Abrechnungsmonat als Argument übergeben (z.B. 08.2025)")
        invoice_month = "08.2025"
        # sys.exit(1)

    filter_obj = InvoiceFilter(invoice_month=invoice_month)

    # Konfiguration laden, um Log-Verzeichnis zu bestimmen
    config_obj = Config()
    config_obj.load(config_path)

    # Log-Verzeichnis und Logdatei konfigurieren
    logs_dir = Path(config_obj.data["structure"]["prj_root"]) / config_obj.data["structure"]["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "Rechnung.log"

    # Loguru-Konfiguration: Logdatei im gewünschten Verzeichnis und Konsolenausgabe
    logger.add(str(log_file), rotation="10 MB", retention="10 days", level="INFO")
    logger.info("Starte Rechnungsprozess...")

    try:
        # Die Entitäten und erwarteten Spalten werden jetzt segmentiert aus der config geladen
        # InvoiceContext wird im InvoiceProcessor genutzt
        processor = InvoiceProcessor(config=config_obj, filter=filter_obj)
        processor.run()
        logger.success("Rechnungsprozess erfolgreich abgeschlossen.")
    except Exception as e:
        logger.exception(f"Fehler im Rechnungsprozess: {e}")

if __name__ == "__main__":
    main()


