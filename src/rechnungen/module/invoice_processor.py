from pathlib import Path
from typing import List, Optional
from datetime import datetime

import pandas as pd
from loguru import logger
from module.config import Config
from module.data_loader import DataLoader
from module.document_utils import DocumentUtils
from module.invoice_factory import InvoiceFactory
from module.invoice_context import InvoiceContext
from module.utils import (
    clear_path,
    zip_invoices,
    temporary_docx,
    format_date,
)
from module.entity import JuristischePerson, PrivatePerson


class InvoiceProcessor:
    """
    Fassade für den Gesamtprozess der Rechnungserstellung.
    Koordiniert das Laden der Daten, die Rechnungserstellung, PDF-Generierung und die Zusammenfassung.
    """

    def __init__(self, config: Config, start_inv_period: str, end_inv_period: str):
        self.config = config
        self.data_loader = DataLoader(self.config)
        self.invoice_factory = InvoiceFactory(self.config)
        self.start_inv_period = start_inv_period
        self.end_inv_period = end_inv_period

    def run(self):
        logger.info(
            f"Starte Rechnungsprozess für Leistungszeitraum {self.start_inv_period} bis {self.end_inv_period}."
        )

        # Konfigurationswerte auslesen
        env = self.config.data["structure"]
        project_root = Path(env["prj_root"])
        tmp_path: Path = Path(env["tmp_path"])
        output_path: Path = Path(env["output_path"])

        clear_path(tmp_path)
        logger.debug(f"Temporäres Verzeichnis {tmp_path} geleert.")

        data_path: Path = project_root / env["data_path"]
        db_name: str = self.config.data["db_name"]
        sheet_name: Optional[str] = self.config.data.get("sheet_name")

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

        summary_contexts = []
        all_invoices: List[Path] = []

        # Gruppierung nach Zahlungsdienstleister (ZDNR)
        zd_grouped = invoice_data.groupby("ZDNR")
        for zdnr, zd_data in zd_grouped:
            logger.info(
                f"Verarbeite Zahlungsdienstleister: {zd_data['ZD_Name'].iloc[0]}"
            )
            invoice_group: List[Path] = []
            zd_entity = JuristischePerson(
                name=zd_data["ZD_Name"].iloc[0],
                strasse=zd_data["ZD_Strasse"].iloc[0],
                plz_ort=zd_data["ZD_PLZ_Ort"].iloc[0],
                iban=zd_data["ZD_IBAN"].iloc[0] if "ZD_IBAN" in zd_data.columns else None,
                zdnr=zdnr
            )
            empfaenger_entity = None
            if "Empfaenger_Name" in zd_data.columns:
                empfaenger_entity = JuristischePerson(
                    name=zd_data["Empfaenger_Name"].iloc[0],
                    strasse=zd_data["Empfaenger_Strasse"].iloc[0],
                    plz_ort=zd_data["Empfaenger_PLZ_Ort"].iloc[0],
                    iban=zd_data["Empfaenger_IBAN"].iloc[0] if "Empfaenger_IBAN" in zd_data.columns else None,
                    kennung=zd_data["Empfaenger_ZDNR"].iloc[0] if "Empfaenger_ZDNR" in zd_data.columns else None
                )

            # Gruppierung nach Klient
            client_grouped = zd_data.groupby("Klient-Nr.")
            for client_id, client_details in client_grouped:
                client_entity = PrivatePerson(
                    vorname=client_details["CL_Vorname"].iloc[0] if "CL_Vorname" in client_details.columns else "",
                    nachname=client_details["CL_Nachname"].iloc[0] if "CL_Nachname" in client_details.columns else "",
                    strasse=client_details["CL_Strasse"].iloc[0] if "CL_Strasse" in client_details.columns else "",
                    plz_ort=client_details["CL_PLZ_Ort"].iloc[0] if "CL_PLZ_Ort" in client_details.columns else "",
                    geburtsdatum=client_details["CL_Geburtsdatum"].iloc[0] if "CL_Geburtsdatum" in client_details.columns else None,
                    kennung=client_id
                )

                invoice_id = self.invoice_factory.create_invoice_id(
                    format_date(self.start_inv_period), client_id
                )

                # Die Summenfelder und *_2f-Felder werden erst in format_invoice berechnet!
                # Also: InvoiceContext erst nach format_invoice erzeugen
                formatted_invoice, updated_data, temp_context = self.invoice_factory.format_invoice(
                    InvoiceContext(
                        rechnungsnummer=invoice_id,
                        rechnungsdatum=pd.Timestamp.now().strftime("%d.%m.%Y"),
                        start_inv_period=format_date(self.start_inv_period),
                        end_inv_period=format_date(self.end_inv_period),
                        zahlungsdienstleister=zd_entity,
                        empfaenger=empfaenger_entity,
                        client=client_entity,
                    ),
                    client_details,
                )

                # Positionen und Summenfelder jetzt aus temp_context übernehmen
                invoice_context = temp_context

                re_nr: str = invoice_context.rechnungsnummer

                with temporary_docx() as docx_path:
                    # Rechnung als DOCX zwischenspeichern
                    formatted_invoice.save(docx_path)
                    logger.debug(f"Temporäre Rechnung gespeichert: {docx_path}")
                    named_pdf = DocumentUtils.docx_to_pdf(
                        docx_path,
                        docx_path.with_suffix(".pdf"),
                        invoice_context
                    )
                    invoice_group.append(named_pdf)
                    all_invoices.append(named_pdf)  # PDF zur Gesamtliste hinzufügen
                # Kontext für die Zusammenfassung speichern
                summary_contexts.append(invoice_context)
            # Alle PDFs für diesen ZD zusammenführen
            DocumentUtils.merge_pdfs(
                invoice_group, invoice_context, output_path=output_path,
            )
            logger.info(f"PDFs für ZDNR {zdnr} zusammengeführt.")
        # Excel-Übersicht erzeugen
        DocumentUtils.create_summary(
            self.config, 
            summary_contexts, 
            format_date(self.start_inv_period), 
            format_date(self.end_inv_period)
        )
        logger.info("Rechnungsübersicht als Excel-Datei erstellt.")

        zip_invoices(
            all_invoices,
            output_path
            / f"Rechnungen_{format_date(self.start_inv_period)}_bis_{format_date(self.end_inv_period)}.zip",
        )
        logger.success("Alle Rechnungsdokumente wurden erfolgreich archiviert.")


if __name__ == "__main__":
    print("InvoiceProcessor Modul. Nicht direkt ausführbar.")
