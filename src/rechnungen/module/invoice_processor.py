from pathlib import Path
from typing import List

import pandas as pd
from jinja2 import Environment
from loguru import logger
from module.config import Config
from module.data_loader import DataLoader
from module.document_utils import DocumentUtils
from module.entity import LegalPerson, PrivatePerson
from module.invoice_context import InvoiceContext
from module.invoice_factory import InvoiceFactory
from module.invoice_filter import InvoiceFilter
from module.utils import clear_path, get_month_period, temporary_docx, zip_invoices, log_exceptions

from .filters import register_filters


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
        # TODO: Prüfen, ob das überhaupt sinnvoll ist. Es wird nur der Monat für die Rechnung benötigt
        start_period, end_period = get_month_period(self.filter.invoice_month)
        start_inv_period = start_period.strftime("%d.%m.%Y")
        end_inv_period = end_period.strftime("%d.%m.%Y")

        invoice_list = []
        all_invoices: List[Path] = []

        # Wird nur beim Rendern der Rechnungstemplates genutzt
        jinja_env = Environment()
        register_filters(jinja_env, self.config.data)

        # Positionsspalten aus der Config auslesen
        position_columns = [
            col["name"]
            for section in self.config.get_expected_columns()
            for col in self.config.get_expected_columns()[section]
            if col.get("is_position", False)
        ]
        sum_columns = [
            col["name"]
            for section in self.config.get_expected_columns()
            for col in self.config.get_expected_columns()[section]
            if col.get("is_position", False) and col.get("sum", False)
        ]

        # Gruppierung nach Zahlungsdienstleister (ZDNR)
        for payer_id, payer_data in invoice_data.groupby("ZDNR"):
            payer_row = payer_data.iloc[0]

            invoices_for_payer: List[Path] = []

            payer_obj = LegalPerson(
                name=payer_row.get("ZD_Name", ""),
                name_2=payer_row.get("ZD_Name2", ""),
                street=payer_row.get("ZD_Strasse", ""),
                zip=payer_row.get("ZD_PLZ", ""),
                city=payer_row.get("ZD_Ort", ""),
                iban=payer_row.get("ZD_IBAN", None),
                key=str(payer_id),
            )

            logger.debug(
                f"Erstelle Rechnungen für Zahlungsdienstleister: {payer_obj.key} (ZDNR: {payer_id}) mit {len(payer_data)} Positionen"
            )

            # Kontext für die Zusammenführung der PDFs pro ZDNR
            payer_context = InvoiceContext(
                data={
                    "payer": payer_obj,
                    "start_inv_period": start_inv_period,
                    "end_inv_period": end_inv_period,
                    "invoice_month": self.filter.invoice_month,
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
                    social_security_number=client_row.get("CL_SozVersNr", ""),
                    key=str(client_id),
                )

                logger.debug(
                    f"Erstelle Rechnung für Klient: {client_obj.name} ({client_obj.key}) mit {len(client_details)} Positionen"
                )

                # Leistungsbesteller und Betreuungstyp aus den Daten holen
                service_requester = client_row.get("Leistungsbesteller", "")
                care_type = client_row.get("Betreuungstyp", "")

                invoice_id = self.invoice_factory.create_invoice_id(
                    client_id=str(client_id), invoice_month=self.filter.invoice_month
                )

                # Nur Felder mit is_position=True aus der Config
                position_columns = [
                    col["name"]
                    for section in self.config.get_expected_columns()
                    for col in self.config.get_expected_columns()[section]
                    if col.get("is_position", False)
                ]
                positions = client_details[position_columns].to_dict("records")

                # Summenfelder: Nur Felder, die sowohl is_position=True als auch sum=True haben
                sum_columns = [
                    col["name"]
                    for section in self.config.get_expected_columns()
                    for col in self.config.get_expected_columns()[section]
                    if col.get("is_position", False) and col.get("sum", False)
                ]
                totals = {
                    f"summe_{col.lower()}": client_details[col].sum()
                    for col in sum_columns
                    if col in client_details.columns
                }

                invoice_context = InvoiceContext(
                    data={
                        "invoice_id": invoice_id,
                        "invoice_date": pd.Timestamp.now(),
                        "invoice_month": self.filter.invoice_month,
                        "start_inv_period": start_inv_period,
                        "end_inv_period": end_inv_period,
                        "service_requester": service_requester,
                        "care_type": care_type,
                        "payer": payer_obj,
                        "service_provider": service_provider_obj,
                        "client": client_obj,
                        # "config": self.config,
                        "positions": positions,
                        **totals,
                    }
                )

                with log_exceptions(f"Fehler bei PDF-Erstellung für Klient {client_id}"):
                    rendered_invoice = self.invoice_factory.render_invoice(
                        invoice_context=invoice_context,
                        jinja_env=jinja_env,
                    )
                    with temporary_docx() as docx_path:
                        rendered_invoice.save(docx_path)
                        named_pdf = DocumentUtils.docx_to_pdf(
                            docx_path, docx_path.with_suffix(".pdf"), invoice_context
                        )
                        invoices_for_payer.append(named_pdf)
                        all_invoices.append(named_pdf)
                    invoice_list.append(invoice_context)

            with log_exceptions(f"Fehler beim Zusammenführen der PDFs für ZDNR {payer_id}"):
                merged_pdf = DocumentUtils.merge_pdfs(
                    invoices_for_payer, payer_context, output_path=output_path
                )
                logger.info(f"PDFs für ZDNR {payer_id} zusammengeführt in {merged_pdf.name}")

        with log_exceptions("Fehler beim Erstellen der Rechnungsübersicht"):
            summary_file = DocumentUtils.create_summary(
                config=self.config,
                invoice_list=invoice_list,
            )
            logger.info(f"Rechnungsübersicht als Excel-Datei {summary_file.name} erstellt")

        with log_exceptions("Fehler beim Archivieren der Rechnungsdokumente"):
            zip_invoices(
                all_invoices,
                output_path / f"Rechnungen_{start_inv_period}_bis_{end_inv_period}.zip",
            )
            logger.success("Alle Rechnungsdokumente wurden erfolgreich archiviert.")


if __name__ == "__main__":
    print("InvoiceProcessor Modul. Nicht direkt ausführbar.")
