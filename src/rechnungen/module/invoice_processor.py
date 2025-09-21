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
from module.invoice_filter import InvoiceFilter
from module.utils import (
    clear_path,
    zip_invoices,
    temporary_docx,
    format_date,
)
from module.entity import LegalPerson, PrivatePerson

class InvoiceProcessor:
    """
    Fassade für den Gesamtprozess der Rechnungserstellung.
    Koordiniert das Laden der Daten, die Rechnungserstellung, PDF-Generierung und die Zusammenfassung.
    """

    def __init__(self, config: Config, filter: InvoiceFilter):
        self.config = config
        self.filter = filter
        self.data_loader = DataLoader(self.config, self.filter)
        self.invoice_factory = InvoiceFactory(self.config)

    def run(self):
        logger.info(f"Starte Rechnungsprozess mit folgenden Filtern: {self.filter}")

        # Konfigurationswerte auslesen
        env: dict = self.config.data["structure"]
        project_root = Path(env["prj_root"])
        tmp_path: Path = project_root / Path(env["tmp_path"])
        output_path: Path = project_root / Path(env["output_path"])

        clear_path(tmp_path)
        logger.debug(f"Temporäres Verzeichnis {tmp_path} geleert.")

        source = project_root / env["data_path"] / self.config.data["db_name"]
        sheet_name: Optional[str] = self.config.data.get("sheet_name")
        logger.debug(f"Lade Daten aus {source}, Blatt: {sheet_name or 'aktiv'}")

        # Daten kommen bereits komplett gefiltert aus dem DataLoader
        invoice_data: pd.DataFrame = self.data_loader.load_data(source, 
                                                                sheet_name, 
                                                                )
        logger.info(f"{len(invoice_data)} Datensätze nach Filterung gefunden.")

        self.data_loader.check_data_consistency(invoice_data)
        logger.info("Daten erfolgreich geladen und geprüft.")

        service_provider_obj = self.invoice_factory.provider
        # TODO: Prüfen, was die str Konversion eines Entity-Objekts macht
        logger.debug(f"Empfänger der Rechnungen: {service_provider_obj}")

        # Zur Erzeugung einer Übersicht über den gesamten Rechnungsprozess
        summary_contexts = []
        # Zur Archivierung aller Rechnungen aus diesem Lauf
        all_invoices: List[Path] = []

        # Gruppierung nach Zahlungsdienstleister (ZDNR)
        payer_grouped = invoice_data.groupby("ZDNR")
        for payer_id, payer_data in payer_grouped:
            payer_row = payer_data.iloc[0]

            logger.info(
                f"Verarbeite Zahlungsdienstleister: {payer_row.get('ZD_Name',
                                                                   payer_id)}"
            )
            # Für eine konsolidierte PDF aller Rechnungen eines ZD (Payer)
            invoice_group: List[Path] = []            

            payer_obj = LegalPerson(
                name=payer_row.get("ZD_Name", ""),
                street=payer_row.get("ZD_Strasse", ""),
                zip=payer_row.get("ZD_PLZ", ""),
                city=payer_row.get("ZD_Ort", ""),
                iban=payer_row.get("ZD_IBAN", None),
                key=payer_id
            )
           
            # Gruppierung nach Klient
            client_grouped = payer_data.groupby("Klient-Nr.")
            for client_id, client_details in client_grouped:
                
                client_row = client_details.iloc[0]

                client_obj = PrivatePerson(
                    first_name=client_row.get("CL_Vorname", ""),
                    last_name=client_row.get("CL_Nachname", ""),
                    street=client_row.get("CL_Strasse", ""),
                    zip_city=client_row.get("CL_PLZ_Ort", ""),
                    birth_date=client_row.get("CL_Geburtsdatum", None),
                    key=client_id
                )

                invoice_id = self.invoice_factory.create_invoice_id(
                    client_id=client_id,
                    invoice_month=self.filter.invoice_month
                )
                
                # Initialer Kontext für die Rechnung. Wird in format_fields erweitert
                # wird in format_fields erweitert
                invoice_context = InvoiceContext(
                    invoice_id=invoice_id,
                    invoice_date=pd.Timestamp.now(),
                    inv_month=self.filter.invoice_month,
                    payer=payer_obj,
                    service_provider=service_provider_obj,
                    client=client_obj,
                    config=self.config,
                )
                
                rendered_invoice = self.invoice_factory.render_invoice(
                    invoice_context=invoice_context,
                    client_details=client_details,
                )

                with temporary_docx() as docx_path:
                    # Rechnung als DOCX zwischenspeichern
                    rendered_invoice.save(docx_path)
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
            logger.info(f"PDFs für ZDNR {payer_id} zusammengeführt.")
        # Excel-Übersicht erzeugen
        DocumentUtils.create_summary(
            self.config, 
            summary_contexts, 
            format_date(invoice_context.start_inv_period), 
            format_date(invoice_context.end_inv_period), 
        )
        logger.info("Rechnungsübersicht als Excel-Datei erstellt.")

        zip_invoices(
            all_invoices,
            output_path
            / f"Rechnungen_{format_date(invoice_context.start_inv_period)}_bis_{format_date(invoice_context.end_inv_period)}.zip",
        )
        logger.success("Alle Rechnungsdokumente wurden erfolgreich archiviert.")


if __name__ == "__main__":
    print("InvoiceProcessor Modul. Nicht direkt ausführbar.")
