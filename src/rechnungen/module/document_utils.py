import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List

import pandas as pd
from loguru import logger
from module.config import Config
from openpyxl.styles import Font
from openpyxl.worksheet.table import Table, TableStyleInfo
from PyPDF2 import PdfMerger


class DocumentUtils:
    """
    Statische Hilfsklasse für Dokumentenoperationen:
    - DOCX nach PDF konvertieren
    - PDFs zusammenführen
    - Rechnungsübersicht als Excel-Tabelle erstellen
    """

    @staticmethod
    def docx_to_pdf(docx_path: Path, pdf_path: Path):
        """
        Konvertiert eine DOCX-Datei in eine PDF-Datei mit LibreOffice.

        Args:
            docx_path (Path): Pfad zur DOCX-Datei.
            pdf_path (Path): Pfad zur Ausgabedatei (PDF).
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
        logger.info(f"DOCX zu PDF konvertiert: {pdf_path}")

    @staticmethod
    def merge_pdfs(pdf_files: List[Path], zdnr: str, abrechnungsmonat: str):
        """
        Führt mehrere PDF-Dateien zu einer einzigen zusammen.

        Args:
            pdf_files (List[Path]): Liste der PDF-Dateipfade.
            zdnr (str): Zahlungsdienstleister-Nummer.
            abrechnungsmonat (str): Abrechnungsmonat im Format 'YYYY-MM'.
        """
        if not pdf_files:
            logger.warning("Keine PDF-Dateien zum Zusammenführen gefunden.")
            return
        merger = PdfMerger()
        output_path = pdf_files[0].parent
        for pdf_file in pdf_files:
            merger.append(pdf_file)
        merged_pdf_path = output_path / f"Rechnungen_{zdnr}_{abrechnungsmonat}.pdf"
        merger.write(merged_pdf_path)
        merger.close()
        logger.info(f"Zusammengefasste PDF gespeichert: {merged_pdf_path}")

    @staticmethod
    def create_summary(config: Config, summary_rows: List[Dict], abrechnungsmonat: str):
        """
        Erstellt eine Excel-Datei mit der Rechnungsübersicht.

        Args:
            config (Config): Konfiguration mit Pfadangaben.
            summary_rows (List[Dict]): Liste der Rechnungsübersicht-Zeilen.
            abrechnungsmonat (str): Abrechnungsmonat im Format 'YYYY-MM'.
        """
        output_path: Path = Path(config.data["structure"]["output_path"])
        summary_df = pd.DataFrame(summary_rows)
        summary_file = output_path / f"Rechnungsuebersicht_{abrechnungsmonat}.xlsx"
        with pd.ExcelWriter(summary_file, engine="openpyxl") as writer:
            summary_df.to_excel(writer, index=False, sheet_name="Rechnungsübersicht")
            worksheet = writer.sheets["Rechnungsübersicht"]
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
            if "Summe_Kosten" in summary_df.columns:
                kosten_col_idx = summary_df.columns.get_loc("Summe_Kosten") + 1
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

# if __name__ == "__main__":
#     print("DocumentUtils Modul. Nicht direkt ausführbar.")
