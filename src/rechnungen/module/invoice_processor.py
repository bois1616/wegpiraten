from pathlib import Path
from typing import List, Optional

import pandas as pd  # Für Datenmanipulation
from loguru import logger  # Zentrales Logging-System
from module.config import Config  # Singleton-Konfiguration
from module.data_loader import DataLoader  # Datenbank-Lader
from module.document_utils import DocumentUtils  # PDF/Excel Hilfsfunktionen
from module.invoice_factory import InvoiceFactory  # Rechnungserstellung
from module.utils import clear_path, zip_docs  # Hilfsfunktionen für Dateimanagement


class InvoiceProcessor:
    """
    Fassade für den Gesamtprozess der Rechnungserstellung.
    Koordiniert das Laden der Daten, die Rechnungserstellung, PDF-Generierung und die Zusammenfassung.
    """

    def __init__(self, config_path: Path):
        """
        Initialisiert den Prozessor mit dem Pfad zur Konfigurationsdatei.

        Args:
            config_path (Path): Pfad zur YAML-Konfigurationsdatei.
        """
        self.config = Config()
        self.config.load(config_path)
        self.data_loader = DataLoader(self.config)
        self.invoice_factory = InvoiceFactory(self.config)

    def run(self, abrechnungsmonat: str = "2025-08"):
        """
        Führt den gesamten Rechnungsprozess für einen Abrechnungsmonat aus.

        Args:
            abrechnungsmonat (str): Abrechnungsmonat im Format 'YYYY-MM'.
        """
        logger.info(f"Starte Rechnungsprozess für Abrechnungsmonat {abrechnungsmonat}.")

        # Konfigurationswerte auslesen
        env = self.config.data["structure"]
        project_root = Path(env["prj_root"])
        tmp_path: Path = Path(env["tmp_path"])
        output_path: Path = Path(env["output_path"])

        # Temporäres Verzeichnis leeren
        clear_path(tmp_path)
        logger.debug(f"Temporäres Verzeichnis {tmp_path} geleert.")

        # Datenbankpfad zusammensetzen
        data_path: Path = project_root / env["data_path"]
        db_name: str = self.config.data["db_name"]
        sheet_name: Optional[str] = self.config.data.get("sheet_name")

        # Daten aus Excel laden und prüfen
        invoice_data: pd.DataFrame = self.data_loader.load_data(
            data_path / db_name, sheet_name, abrechnungsmonat
        )
        self.data_loader.check_data_consistency(invoice_data)
        logger.info("Daten erfolgreich geladen und geprüft.")

        summary_rows = []
        # Gruppierung nach Zahlungsdienstleister (ZDNR)
        zd_grouped = invoice_data.groupby("ZDNR")
        for zdnr, zd_data in zd_grouped:
            logger.info(f"Verarbeite Zahlungsdienstleister: {zd_data['ZD_Name'].iloc[0]}")
            invoice_group: List[Path] = []
            # Gruppierung nach Klient
            client_grouped = zd_data.groupby("Klient-Nr.")
            for client_id, client_details in client_grouped:
                # Rechnung und aktualisierte Daten erzeugen
                formatted_invoice, updated_data = self.invoice_factory.format_invoice(
                    client_details
                )
                re_nr: str = updated_data["Rechnungsnummer"].iloc[0]
                docx_path: Path = tmp_path / f"Rechnung_{re_nr}.docx"
                # Rechnung als DOCX speichern
                formatted_invoice.save(docx_path)
                logger.debug(f"Rechnung gespeichert: {docx_path}")
                # DOCX in PDF konvertieren
                DocumentUtils.docx_to_pdf(docx_path, _ := docx_path.with_suffix(".pdf"))
                logger.debug(f"PDF erzeugt: {_}")
                invoice_group.append(_)
                # Zusammenfassungsdaten für die Excel-Übersicht sammeln
                summary_rows.append(
                    {
                        "Rechnungsnummer": re_nr,
                        "Klient-Nr.": client_id,
                        "ZDNR": zdnr,
                        "ZD_Name": updated_data["ZD_Name"].iloc[0],
                        "Summe_Kosten": updated_data["Summe_Kosten"].iloc[0],
                        "Rechnungsdatum": updated_data["Rechnungsdatum"].iloc[0],
                    }
                )
            # Alle PDFs für diesen ZD zusammenführen
            DocumentUtils.merge_pdfs(invoice_group, str(zdnr), abrechnungsmonat)
            logger.info(f"PDFs für ZDNR {zdnr} zusammengeführt.")
            break  # TODO: Wieder rausnehmen, wenn mehrere ZD unterstützt werden
        # Excel-Übersicht erzeugen
        DocumentUtils.create_summary(self.config, summary_rows, abrechnungsmonat)
        logger.info("Rechnungsübersicht als Excel-Datei erstellt.")
        # Alle Rechnungs-DOCX als ZIP archivieren
        zip_docs(tmp_path, output_path / f"Rechnungen_{abrechnungsmonat}.zip")
        logger.success("Alle Rechnungsdokumente wurden erfolgreich archiviert.")
