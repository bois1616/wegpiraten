from pathlib import Path
from loguru import logger  # Zentrales Logging-System

from module.invoice_processor import InvoiceProcessor
from module.config import Config  # Für Zugriff auf die Konfiguration

# --- Main ---
if __name__ == "__main__":
    # Pfad zur YAML-Konfigurationsdatei bestimmen
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"

    # Konfiguration laden, um Log-Verzeichnis zu bestimmen
    config = Config()
    config.load(config_path)
    prj_root = Path(config.data["structure"]["prj_root"])
    logs_dir = prj_root / config.data["structure"]["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "rechnung.log"

    # Loguru-Konfiguration: Logdatei im gewünschten Verzeichnis und Konsolenausgabe
    logger.add(str(log_file), rotation="10 MB", retention="10 days", level="INFO")
    logger.info("Starte Rechnungsprozess...")

    try:
        processor = InvoiceProcessor(config_path)
        processor.run()
        logger.success("Rechnungsprozess erfolgreich abgeschlossen.")
    except Exception as e:
        logger.exception(f"Fehler im Rechnungsprozess: {e}")