import sys
from pathlib import Path

from loguru import logger  # Zentrales Logging-System
from module.config import Config  # Für Zugriff auf die Konfiguration
from module.invoice_processor import InvoiceProcessor
from module.invoice_context import InvoiceContext  # InvoiceContext importieren
from module.utils import get_month_period, parse_date  # Import aus utils

# --- Main ---
if __name__ == "__main__":
    # Pfad zur YAML-Konfigurationsdatei bestimmen
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"

    # Abrechnungsmonat als Argument übergeben
    if len(sys.argv) > 1:
        abrechnungsmonat_input = sys.argv[1]
    else:
        print("Bitte Abrechnungsmonat als Argument übergeben (z.B. 08.2025)")
        abrechnungsmonat_input = "08.2025"
        # sys.exit(1)

    # Start- und Enddatum aus dem Abrechnungsmonat bestimmen
    start_inv_period_input, end_inv_period_input = get_month_period(abrechnungsmonat_input)

    # Datumsangaben ins interne Format konvertieren
    start_inv_period = parse_date(start_inv_period_input)
    end_inv_period = parse_date(end_inv_period_input)

    # Konfiguration laden, um Log-Verzeichnis zu bestimmen
    config = Config()
    config.load(config_path)
    prj_root = Path(config.data["structure"]["prj_root"])
    logs_dir = prj_root / config.data["structure"]["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "Rechnung.log"

    # Loguru-Konfiguration: Logdatei im gewünschten Verzeichnis und Konsolenausgabe
    logger.add(str(log_file), rotation="10 MB", retention="10 days", level="INFO")
    logger.info("Starte Rechnungsprozess...")

    try:
        # Die Entitäten und erwarteten Spalten werden jetzt segmentiert aus der config geladen
        # InvoiceContext wird im InvoiceProcessor genutzt
        processor = InvoiceProcessor(config, start_inv_period, end_inv_period)
        processor.run()
        logger.success("Rechnungsprozess erfolgreich abgeschlossen.")
    except Exception as e:
        logger.exception(f"Fehler im Rechnungsprozess: {e}")


