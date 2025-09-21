from pathlib import Path
from typing import List
import pandas as pd
from loguru import logger

from module.config import Config
from module.data_loader import DataLoader
from module.document_utils import DocumentUtils
from module.invoice_factory import InvoiceFactory
from module.invoice_context import InvoiceContext
from module.invoice_filter import InvoiceFilter
from module.utils import clear_path, zip_invoices, temporary_docx, get_month_period
from module.entity import LegalPerson, PrivatePerson

class InvoiceProcessor:
    """
    Koordiniert den Gesamtprozess der Rechnungserstellung:
    - Daten laden und prüfen
    - Rechnungen und PDFs erzeugen
    - Zusammenfassungen und ZIP-Archiv erstellen
    """

    def __init__(self, config: Config, filter: InvoiceFilter):
        self.config = config
        self.filter = filter
        self.data_loader = DataLoader(config, filter)
        self.invoice_factory = InvoiceFactory(config)

    def run(self):
        logger.info(f"Starte Rechnungsprozess mit Filter: {self.filter}")

        env = self.config.data["structure"]
        project_root = Path(env["prj_root"])
        tmp_path = project_root / env["tmp_path"]
        output_path = project_root / env["output_path"]

        clear_path(tmp_path)
        logger.debug(f"Temporäres Verzeichnis {tmp_path} geleert.")

        source = project_root / env["data_path"] / self.config.data["db_name"]
        sheet_name = self.config.data.get("sheet_name")
        logger.debug(f"Lade Daten aus {source}, Blatt: {sheet_name or 'aktiv'}")

        invoice_data = self.data_loader.load_data(source, sheet_name)
        logger.info(f"{len(invoice_data)} Datensätze nach Filterung gefunden.")

        self.data_loader.check_data_consistency(invoice_data)
        logger.info("Daten erfolgreich geladen und geprüft.")

        service_provider_obj = self.invoice_factory.provider
        logger.debug(f"Empfänger der Rechnungen: {service_provider_obj}")

        # Zeitraum für den gesamten Rechnungsprozess einmal berechnen
        start_period, end_period = get_month_period(self.filter.invoice_month)
        start_inv_period = start_period.strftime("%d.%m.%Y")
        end_inv_period = end_period.strftime("%d.%m.%Y")

        summary_contexts = []
        all_invoices: List[Path] = []

        # Positionsspalten aus der Config auslesen
        position_columns = [
            col["name"]
            for col in self.config.get_expected_columns().get("general", [])
            if col.get("is_position", False)
        ]
        sum_columns = [
            col["name"]
            for col in self.config.get_expected_columns().get("general", [])
            if col.get("sum", False)
        ]

        # Gruppierung nach Zahlungsdienstleister (ZDNR)
        for payer_id, payer_data in invoice_data.groupby("ZDNR"):
            payer_row = payer_data.iloc[0]
            logger.info(f"Verarbeite Zahlungsdienstleister: {payer_row.get('ZD_Name', payer_id)}")
            invoices_for_payer: List[Path] = []

            payer_obj = LegalPerson(
                name=payer_row.get("ZD_Name", ""),
                street=payer_row.get("ZD_Strasse", ""),
                zip=payer_row.get("ZD_PLZ", ""),
                city=payer_row.get("ZD_Ort", ""),
                iban=payer_row.get("ZD_IBAN", None),
                key=payer_id
            )

            # Kontext für die Zusammenführung der PDFs pro ZDNR
            payer_context = InvoiceContext(
                data={
                    "payer": payer_obj,
                    "start_inv_period": start_inv_period,
                    "end_inv_period": end_inv_period,
                }
            )

            for client_id, client_details in payer_data.groupby("Klient-Nr."):
                client_row = client_details.iloc[0]
                client_obj = PrivatePerson(
                    first_name=client_row.get("CL_Vorname", ""),
                    last_name=client_row.get("CL_Nachname", ""),
                    street=client_row.get("CL_Strasse", ""),
                    zip_city=client_row.get("CL_PLZ_Ort", ""),
                    birth_date=client_row.get("CL_Geburtsdatum", None),
                    key=str(client_id)
                )

                invoice_id = self.invoice_factory.create_invoice_id(
                    client_id=str(client_id),
                    invoice_month=self.filter.invoice_month
                )

                # Positionen für die Rechnung: Nur die in der Config-Datei als solche markierten Spalten
                positionen = client_details[position_columns].to_dict("records")

                # Summenfelder berechnen und eindeutig benennen für die in der Config-Datei als "sum" markierten Spalten
                summe_felder = {
                    f"summe_{col.lower()}": client_details[col].sum() for col in sum_columns if col in client_details.columns
                }

                invoice_context = InvoiceContext(
                    data={
                        "invoice_id": invoice_id,
                        "invoice_date": pd.Timestamp.now(),
                        "inv_month": self.filter.invoice_month,
                        "start_inv_period": start_inv_period,
                        "end_inv_period": end_inv_period,
                        "payer": payer_obj,
                        "service_provider": service_provider_obj,
                        "client": client_obj,
                        "config": self.config,
                        "Positionen": positionen,
                        **summe_felder
                    }
                )

                rendered_invoice = self.invoice_factory.render_invoice(
                    invoice_context=invoice_context,
                    client_details=client_details,
                )

                with temporary_docx() as docx_path:
                    rendered_invoice.save(docx_path)
                    logger.debug(f"Temporäre Rechnung gespeichert: {docx_path}")
                    named_pdf = DocumentUtils.docx_to_pdf(
                        docx_path,
                        docx_path.with_suffix(".pdf"),
                        invoice_context
                    )
                    invoices_for_payer.append(named_pdf)
                    all_invoices.append(named_pdf)
                summary_contexts.append(invoice_context)

            DocumentUtils.merge_pdfs(invoices_for_payer, payer_context, output_path=output_path)
            logger.info(f"PDFs für ZDNR {payer_id} zusammengeführt.")

        DocumentUtils.create_summary(
            config=self.config,
            summary_contexts=summary_contexts,
            start_inv_period=start_inv_period,
            end_inv_period=end_inv_period,
        )
        logger.info("Rechnungsübersicht als Excel-Datei erstellt.")

        zip_invoices(
            all_invoices,
            output_path / f"Rechnungen_{start_inv_period}_bis_{end_inv_period}.zip",
        )
        logger.success("Alle Rechnungsdokumente wurden erfolgreich archiviert.")

if __name__ == "__main__":
    print("InvoiceProcessor Modul. Nicht direkt ausführbar.")
