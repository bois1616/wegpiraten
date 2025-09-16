from pathlib import Path
from typing import List, Optional
from datetime import datetime

import pandas as pd  # Für Datenmanipulation
from loguru import logger  # Zentrales Logging-System
from .config import Config  # Singleton-Konfiguration
from .data_loader import DataLoader  # Datenbank-Lader
from .document_utils import DocumentUtils  # PDF/Excel Hilfsfunktionen
from .invoice_factory import InvoiceFactory  # Rechnungserstellung
from .utils import (
    clear_path,
    zip_invoices,
    temporary_docx,
    format_date,
)  # Hilfsfunktionen für Dateimanagement


class InvoiceProcessor:
    """
    Fassade für den Gesamtprozess der Rechnungserstellung.
    Koordiniert das Laden der Daten, die Rechnungserstellung, PDF-Generierung und die Zusammenfassung.
    """

    def __init__(self, config: Config, start_inv_period: str, end_inv_period: str):
        """
        Initialisiert den Prozessor mit der Konfiguration und dem Leistungszeitraum.

        Args:
            config (Config): Konfigurationsobjekt.
            start_inv_period (str): Startdatum Leistungszeitraum (YYYY-MM-DD).
            end_inv_period (str): Enddatum Leistungszeitraum (YYYY-MM-DD).
        """
        self.config = config
        self.data_loader = DataLoader(self.config)
        self.invoice_factory = InvoiceFactory(self.config)
        self.start_inv_period = start_inv_period
        self.end_inv_period = end_inv_period

    def run(self):
        """
        Führt den gesamten Rechnungsprozess für den angegebenen Leistungszeitraum aus.
        """
        logger.info(
            f"Starte Rechnungsprozess für Leistungszeitraum {self.start_inv_period} bis {self.end_inv_period}."
        )

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
            data_path / db_name, sheet_name, self.start_inv_period, self.end_inv_period
        )
        self.data_loader.check_data_consistency(invoice_data)
        logger.info("Daten erfolgreich geladen und geprüft.")

        # Filter nach Leistungszeitraum
        invoice_data = invoice_data[
            (invoice_data["Leistungsdatum"] >= self.start_inv_period)
            & (invoice_data["Leistungsdatum"] <= self.end_inv_period)
        ]

        summary_rows = []
        # Gruppierung nach Zahlungsdienstleister (ZDNR)
        all_invoices: List[Path] = []  # Liste für alle erzeugten PDFs

        zd_grouped = invoice_data.groupby("ZDNR")
        for zdnr, zd_data in zd_grouped:
            logger.info(
                f"Verarbeite Zahlungsdienstleister: {zd_data['ZD_Name'].iloc[0]}"
            )
            invoice_group: List[Path] = []
            # Gruppierung nach Klient
            client_grouped = zd_data.groupby("Klient-Nr.")
            for client_id, client_details in client_grouped:
                # Rechnung und aktualisierte Daten erzeugen
                formatted_invoice, updated_data = self.invoice_factory.format_invoice(
                    client_details,
                    start_inv_period=format_date(self.start_inv_period),
                    end_inv_period=format_date(self.end_inv_period),
                )
                re_nr: str = updated_data["Rechnungsnummer"].iloc[0]
                with temporary_docx() as docx_path:
                    # Rechnung als DOCX zwischenspeichern
                    formatted_invoice.save(docx_path)
                    logger.debug(f"Temporäre Rechnung gespeichert: {docx_path}")
                    # DOCX in PDF konvertieren und nach Vorgabe benennen
                    named_pdf = DocumentUtils.docx_to_pdf(
                        docx_path,
                        docx_path.with_suffix(".pdf"),
                        client_id=client_id,
                        start_inv_period=format_date(self.start_inv_period),
                        end_inv_period=format_date(self.end_inv_period),
                    )
                    invoice_group.append(named_pdf)
                    all_invoices.append(named_pdf)  # PDF zur Gesamtliste hinzufügen
                # Zusammenfassungsdaten für die Excel-Übersicht sammeln
                summary_rows.append(
                    {
                        "Rechnungsnummer": re_nr,
                        "Klient-Nr.": client_id,
                        "ZDNR": zdnr,
                        "ZD_Name": updated_data["ZD_Name"].iloc[0],
                        "Summe_Kosten": updated_data["Summe_Kosten"].iloc[0],
                        "Rechnungsdatum": updated_data["Rechnungsdatum"].iloc[0],
                        "start_inv_period": format_date(self.start_inv_period),
                        "end_inv_period": format_date(self.end_inv_period),
                    }
                )
            # Alle PDFs für diesen ZD zusammenführen
            DocumentUtils.merge_pdfs(
                invoice_group, zdnr, format_date(self.start_inv_period), format_date(self.end_inv_period),
                output_path=output_path,
            )
            logger.info(f"PDFs für ZDNR {zdnr} zusammengeführt.")
            break  # TODO: Wieder rausnehmen, wenn mehrere ZD unterstützt werden
        # Excel-Übersicht erzeugen
        DocumentUtils.create_summary(
            self.config, summary_rows, format_date(self.start_inv_period), format_date(self.end_inv_period)
        )
        logger.info("Rechnungsübersicht als Excel-Datei erstellt.")

        # Jetzt die persistenten PDFs archivieren
        zip_invoices(
            all_invoices,
            output_path
            / f"Rechnungen_{format_date(self.start_inv_period)}_bis_{format_date(self.end_inv_period)}.zip",
        )
        logger.success("Alle Rechnungsdokumente wurden erfolgreich archiviert.")


if __name__ == "__main__":
    print("InvoiceProcessor Modul. Nicht direkt ausführbar.")
