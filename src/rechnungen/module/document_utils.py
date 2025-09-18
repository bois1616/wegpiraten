import subprocess
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
from loguru import logger
from .config import Config
from openpyxl.styles import Font
from openpyxl.worksheet.table import Table, TableStyleInfo
from PyPDF2 import PdfMerger
from .entity import JuristischePerson, PrivatePerson
from .invoice_context import InvoiceContext


class DocumentUtils:
    """
    Statische Hilfsklasse für Dokumentenoperationen:
    - DOCX nach PDF konvertieren
    - PDFs zusammenführen
    - Rechnungsübersicht als Excel-Tabelle erstellen
    """

    @staticmethod
    def docx_to_pdf(docx_path: Path, pdf_path: Path, invoice_context: InvoiceContext):
        """
        Konvertiert eine DOCX-Datei in eine PDF-Datei mit LibreOffice und benennt sie ggf. nach Vorgabe um.

        Args:
            docx_path (Path): Pfad zur DOCX-Datei.
            pdf_path (Path): Pfad zur Ausgabedatei (PDF).
            invoice_context (InvoiceContext): Kontextobjekt mit allen Rechnungsdaten.
        """
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(pdf_path.parent),
                str(docx_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        # LibreOffice erzeugt die PDF mit dem gleichen Namen wie die DOCX, nur mit .pdf-Endung
        generated_pdf = docx_path.with_suffix(".pdf")
        # Dateinamen mit Entitäten und Leistungszeitraum
        zdnr = invoice_context.zahlungsdienstleister.kennung
        start_inv_period = invoice_context.start_inv_period
        end_inv_period = invoice_context.end_inv_period
        if zdnr and start_inv_period and end_inv_period:
            target_name = f"Rechnung_{zdnr}_{start_inv_period}_bis_{end_inv_period}.pdf"
            target_pdf = pdf_path.parent / target_name
            os.rename(generated_pdf, target_pdf)
            logger.debug(f"PDF umbenannt: {target_pdf.name}")
            return target_pdf
        else:
            logger.info(f"Dokument erzeugt: {generated_pdf.name}")
            return generated_pdf

    @staticmethod
    def merge_pdfs(pdf_files: List[Path], invoice_context: InvoiceContext, output_path: Path = None):
        """
        Führt mehrere PDF-Dateien zu einer einzigen zusammen.

        Args:
            pdf_files (List[Path]): Liste der PDF-Dateipfade.
            invoice_context (InvoiceContext): Kontextobjekt mit Zahlungsdienstleister und Zeitraum.
            output_path (Path, optional): Zielverzeichnis für die Sammel-PDF.
        """
        if not pdf_files:
            logger.warning("Keine PDF-Dateien zum Zusammenführen gefunden.")
            return
        merger = PdfMerger()
        for pdf_file in pdf_files:
            merger.append(pdf_file)
        # Zielverzeichnis bestimmen
        if output_path is None:
            output_path = pdf_files[0].parent
        zd_entity = invoice_context.zahlungsdienstleister
        start_inv_period = invoice_context.start_inv_period
        end_inv_period = invoice_context.end_inv_period
        merged_pdf_path = output_path / f"Rechnungen_{zd_entity.name}_{start_inv_period}_bis_{end_inv_period}.pdf"
        merger.write(merged_pdf_path)
        merger.close()
        logger.info(f"Zusammengefasste PDF gespeichert: {merged_pdf_path}")

    @staticmethod
    def create_summary(config: Config, summary_contexts: List[InvoiceContext], start_inv_period: str, end_inv_period: str):
        """
        Erstellt eine Excel-Datei mit der Rechnungsübersicht.

        Args:
            config (Config): Konfiguration mit Pfadangaben.
            summary_contexts (List[InvoiceContext]): Liste der Kontextobjekte für die Rechnungsübersicht.
            start_inv_period (str): Startdatum Leistungszeitraum.
            end_inv_period (str): Enddatum Leistungszeitraum.
        """
        output_path: Path = Path(config.data["structure"]["output_path"])
        summary_rows = [ctx.as_dict() for ctx in summary_contexts]
        summary_df = pd.DataFrame(summary_rows)
        summary_file = output_path / f"Rechnungsuebersicht_{start_inv_period}_bis_{end_inv_period}.xlsx"
        with pd.ExcelWriter(summary_file, engine="openpyxl") as writer:
            summary_df.to_excel(writer, index=False, sheet_name="Rechnungsübersicht")
            worksheet = writer.sheets["Rechnungsübersicht"]
            # Spalten dynamisch aus der config holen
            zd_columns = [col["name"] for col in config.data["expected_columns"].get("zd", [])]
            cl_columns = [col["name"] for col in config.data["expected_columns"].get("cl", [])]
            allg_columns = [col["name"] for col in config.data["expected_columns"].get("allgemein", [])]
            all_columns = zd_columns + cl_columns + allg_columns
            end_col_idx = len(summary_df.columns)
            end_col_letter = chr(64 + end_col_idx)
            table_ref = f"A1:{end_col_letter}{len(summary_df) + 1}"
            tab = Table(displayName="Rechnungsübersicht", ref=table_ref)
            tab.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium9",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False,
            )
            worksheet.add_table(tab)
            # Formatierung und Summen für die Kosten-Spalte
            if "summe_kosten" in summary_df.columns:
                kosten_col_idx = int(summary_df.columns.get_loc("summe_kosten")) + 1
                kosten_col_letter = chr(64 + kosten_col_idx) # A=1, B=2, ...
                for row in range(2, len(summary_df) + 2):
                    worksheet[f"{kosten_col_letter}{row}"].number_format = '#,##0.00 "CHF"'
                total_row_idx = len(summary_df) + 2
                worksheet[f"A{total_row_idx}"] = "Gesamt"
                worksheet[f"{kosten_col_letter}{total_row_idx}"] = (
                    f"=SUM({kosten_col_letter}2:{kosten_col_letter}{total_row_idx - 1})"
                )
                worksheet[f"{kosten_col_letter}{total_row_idx}"].number_format = '#,##0.00 "CHF"'
                bold_font = Font(bold=True)
                for col in range(1, end_col_idx + 1):
                    worksheet.cell(row=total_row_idx, column=col).font = bold_font
        logger.info(f"Rechnungsübersicht gespeichert: {summary_file}")

if __name__ == "__main__":
    print("DocumentUtils Modul. Nicht direkt ausführbar.")
