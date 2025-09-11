import subprocess
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import yaml
from docxtpl import DocxTemplate  # type: ignore
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from PyPDF2 import PdfMerger  # type: ignore
from rich import print
from rich.traceback import install
from openpyxl.styles import Font
from icecream import ic  # type: ignore
from zipfile import ZipFile



def format_2f(value: float, currency: Optional[str] = None) -> str:
    if pd.isna(value):
        return ""
    currency = currency or ""
    if currency and not currency.startswith(" "):
        currency = " " + currency
    # Tausenderpunkt, Dezimalkomma
    tmp_val = f"{value:,.2f}"
    tmp_val = tmp_val.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{tmp_val}{currency}"

def clear_path(path: Path):
    """Löscht alle Dateien im angegebenen Verzeichnis

    Args:
        path (Path): Verzeichnis, dessen Dateien gelöscht werden sollen
    """
    for item in path.iterdir():
        if item.is_file():
            item.unlink()

def zip_docs(src_dir: Path, zip_path: Path):
    with ZipFile(zip_path, "w") as zipf:
        for file in src_dir.glob("Rechnung_*.docx"):
            zipf.write(file, arcname=file.name)


def load_data(
    db: Path,
    sheet: Optional[str] = None,
    abrechnungsmonat: Optional[pd.Timestamp | str] = None,
) -> pd.DataFrame:
    """
    Lade die Aufwandsdaten aus der Excel-DB
    Achtung: Filter in der Excel-Abfrage bleiben bestehen

    Args:
        db (Path): Ort der Datenbank (Excel-Datei)
        sheet (str): Name des Arbeitsblatts. Wenn None, wird das aktive Blatt verwendet.
        abrechnungsmonat (pd.Timestamp): Abrechnungsmonat. Wenn None, wird

    Returns:
        pd.DataFrame: DataFrame mit den Aufwandsdaten für den Abrechnungsmonat
    """
    work_book = load_workbook(db, data_only=True)
    work_sheet = work_book[sheet] if sheet else work_book.active

    # Monat als pd.Timestamp
    if abrechnungsmonat is None:
        abrechnungsmonat = pd.Timestamp.now().to_period("M").to_timestamp()
    elif isinstance(abrechnungsmonat, str):
        abrechnungsmonat = pd.to_datetime(abrechnungsmonat, format="%Y-%m")
    elif not isinstance(abrechnungsmonat, pd.Timestamp):
        raise ValueError(
            "abrechnungsmonat muss ein String im Format 'YYYY-MM' oder ein pd.Timestamp sein"
        )

    # Generator für die Zeilen
    data = work_sheet.values

    # Erste drei Zeilen sind Metadaten
    # Eventuell besser, bis zu einem Schlüsselwort zu springen
    for _ in range(3):
        next(data)

    # Erste Zeile sind die Spaltennamen, aber ohne die erste Spalte (ID)
    columns = next(data)[1:]

    # Daten ab zweiter Spalte
    df = pd.DataFrame(
        (row[1:] for row in data),
        columns=columns,
    )

    # df["Leistungsdatum"] = pd.to_datetime(
    #     df["Leistungsdatum"], errors="coerce", format="%d.%m.%Y"
    # )

    # Start und Ende des Monats bestimmen
    monat_start: pd.Timestamp = abrechnungsmonat
    monat_ende: pd.Timestamp = abrechnungsmonat + pd.offsets.MonthEnd(0)

    # Nur Leistungen im Abrechnungsmonat übernehmen
    df = df[
        (df["Leistungsdatum"] >= monat_start) & (df["Leistungsdatum"] <= monat_ende)
    ]

    # Fehlende Werte in ZD_Name2 mit Leerzeichen auffüllen/ersetzen
    df["ZD_Name2"] = df["ZD_Name2"].fillna("").replace("(Leer)", "")

    return df


def check_data_consistency(df: pd.DataFrame, expected_columns: list):
    """Überprüfe, ob alle erwarteten Spalten im DataFrame vorhanden sind

    Args:
        df (pd.DataFrame): DataFrame mit den Aufwandsdaten
        expected_columns (list): Liste der erwarteten Spaltennamen

    Raises:
        ValueError: Wenn eine oder mehrere erwartete Spalten fehlen
    """
    missing_columns = set(expected_columns) - set(df.columns)

    if missing_columns:
        missing_str = "\n".join(sorted(missing_columns))
        print(f"Fehlende Spalten: {missing_str}")
        raise ValueError(f"Fehlende Felder in der Pivot-Tabelle: {missing_str}")


def create_invoice_id(
    inv_month: Optional[pd.Timestamp|str] = None, client_id: Optional[str] = None
) -> str:
    """Rechnungsnummer aus AbrMon und Klienten-ID generieren

    Args:
        inv_month (pd.Timestamp): Abrechnungsmonat
        client_id (str): Klienten-ID

    Returns:
        str: Rechnungsnummer als String
    """
    #
    # TODO: Klären, ob die erzeugte ReNr ok ist

    if inv_month is None:
        inv_month = pd.Timestamp.now()
    if isinstance(inv_month, str):
        # Extract year and month, format as MMYY
        dt = pd.to_datetime(inv_month.replace(".", "-"), format="%m-%Y", errors="coerce")
        if dt is pd.NaT:
            raise ValueError("inv_month muss ein String im Format 'MM-YYYY' oder ein pd.Timestamp sein")
        month_mmYY = dt.strftime("%m%y")
    elif isinstance(inv_month, pd.Timestamp):
        month_mmYY = inv_month.strftime("%m%y")
    else:
        raise ValueError("inv_month muss ein String im Format 'YYYY-MM' oder ein pd.Timestamp sein")
    client_id = client_id or "K000"

    return f"R{month_mmYY}_{client_id}"


def format_invoice(
    invoice_template: DocxTemplate, client_details: pd.DataFrame
) -> Tuple[DocxTemplate, pd.DataFrame]:
    """
    Erstelle eine Rechnung für einen Klienten
    Zur Übernahme in das Template müssen viele Werte formatiert
    (z.B. Zahlen mit 2 Nachkommastellen, CHF-Suffix etc.)
    oder neu erstellt werden (Summen).

    Args:
        invoice_template (DocxTemplate): Vorlage für die Rechnung
        invoice_id (str): Rechnungsnummer
        client_id (str): Klienten-ID
        client_details (pd.DataFrame): Details für diesen Klienten
    Returns:
        DocxTemplate: Ausgefüllte Rechnung
    """

    # Summen über relevante Spalten in die Daten übernehmen
    # client_details ist eine Gruppe aus dem DataFrame
    # (alle Zeilen für einen Klienten)
    client_details["Summe_Fahrtzeit"] = client_details["Fahrtzeit"].sum()
    client_details["Summe_Direkt"] = client_details["Direkt"].sum()
    client_details["Summe_Indirekt"] = client_details["Indirekt"].sum()
    client_details["Summe_Stunden"] = client_details["Stunden"].sum()
    client_details["Summe_Kosten"] = client_details["Kosten"].sum()

    # Liste der numerischen Felder und optional die Währung
    num_fields = [
        ("Fahrtzeit", None),
        ("Direkt", None),
        ("Indirekt", None),
        ("Sollstunden", None),
        # ("Stundensatz", None),
        ("km_Pauschale", None),
        ("Stunden", None),
        ("Kosten", " CHF"),
        ("Summe_Fahrtzeit", None),
        ("Summe_Direkt", None),
        ("Summe_Indirekt", None),
        ("Summe_Stunden", None),
        ("Summe_Kosten", " CHF"),
    ]

    # Für jedes numerische Feld eine formatierte Textspalte erzeugen
    for col, currency in num_fields:
        client_details[f"{col}_2f"] = client_details[col].apply(
            lambda x: format_2f(x, currency) if pd.notna(x) else ""
        )

    client_details["Leistungsdatum"] = client_details["Leistungsdatum"].dt.strftime(
        "%d.%m.%Y"
    )

    abrechnungsmonat: str = client_details["Leistungsdatum"].iloc[0][3:]
    client_details["Abrechnungsmonat"] = abrechnungsmonat
    client_details["Rechnungsdatum"] = pd.Timestamp.now().strftime("%d.%m.%Y")

    # Rechnungsnummer generieren
    invoice_id = create_invoice_id(
        inv_month=abrechnungsmonat,
        client_id=client_details["Klient-Nr."].iloc[0],
    )

    client_details["Rechnungsnummer"] = invoice_id

    print(f"Erstelle Rechnung {invoice_id}")

    # Kopf-Daten (sind für alle Zeilen der Gruppe gleich,
    # nehmen wir die aus der ersten Zeile (Index 0))
    # Summen üer relevante Spalten in die Daten übernehmen
    context_data = client_details.iloc[0].to_dict()

    # Tabellen-Daten (alle Zeilen für diese Gruppe)
    invoice_positions = client_details[
        [
            "Leistungsdatum",
            "Fahrtzeit_2f",
            "Direkt_2f",
            "Indirekt_2f",
            "Sollstunden_2f",
            # "Stundensatz_2f",
            "km_Pauschale_2f",
            "Stunden_2f",
            "Kosten_2f",
        ]
    ]

    invoice_positions = invoice_positions.to_dict(orient="records")

    # Kontext fürs Template
    # Felder im Template müssen mit den Keys im Kontext
    # exakt übereinstimmen (inkl. Groß-/Kleinschreibung)
    context = {**context_data, "Positionen": invoice_positions}

    # Rendern
    invoice_template.render(context)
    return invoice_template, client_details


def docx_to_pdf(docx_path, pdf_path):
    """
    Konvertiere eine DOCX-Datei in eine PDF-Datei mit LibreOffice

    Args:
        docx_path (str): Pfad zur DOCX-Datei
        pdf_path (str): Pfad zur Ausgabedatei (PDF)
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

def merge_pdfs(pdf_files: list, 
               output_path: Path, 
               zdnr: str, 
               abrechnungsmonat: str):
    """
    Merge multiple PDF files into a single PDF.

    Args:
        pdf_files (list): List of paths to PDF files to be merged.
        output_path (Path): Path to save the merged PDF.
        zdnr (str): Identifier for the payment service provider.
            abrechnungsmonat (str): Billing month in 'YYYY-MM' format.
    """

    merger = PdfMerger()

    for pdf_file in pdf_files:
        merger.append(pdf_file)

    merged_pdf_path = output_path / f"Rechnungen_{zdnr}_{abrechnungsmonat}.pdf"
    merger.write(merged_pdf_path)
    merger.close()

    ic("Zusammengefasste PDF gespeichert:" + str(merged_pdf_path.name))


def create_summary(summary_rows: list, 
                   output_path: Path, 
                   abrechnungsmonat: str):
    """Erstelle eine Excel-Datei mit der Rechnungsübersicht

    Args:
        summary_rows (list): Liste der Rechnungsübersicht-Zeilen
        output_path (Path): Pfad zum Speichern der Excel-Datei
        abrechnungsmonat (str): Abrechnungsmonat im Format 'YYYY-MM'
    """
    summary_df = pd.DataFrame(summary_rows)
    summary_file = output_path / f"Rechnungsuebersicht_{abrechnungsmonat}.xlsx"

    with pd.ExcelWriter(summary_file, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Rechnungsübersicht")
        worksheet = writer.sheets["Rechnungsübersicht"]

        # Endspalte dynamisch bestimmen
        end_col_idx = len(summary_df.columns)
        end_col_letter = chr(64 + end_col_idx)  # 64 + 1 = 'A', etc.
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

        # Spalte "Summe_Kosten" als Währung formatieren
        if "Summe_Kosten" in summary_df.columns:
            kosten_col_idx = summary_df.columns.get_loc("Summe_Kosten") + 1
            kosten_col_letter = chr(64 + kosten_col_idx)
            for row in range(2, len(summary_df) + 2):
                worksheet[f"{kosten_col_letter}{row}"].number_format = '#,##0.00 "CHF"'

            # Ergebniszeile hinzufügen
            total_row_idx = len(summary_df) + 2
            worksheet[f"A{total_row_idx}"] = "Gesamt"
            worksheet[f"{kosten_col_letter}{total_row_idx}"] = f"=SUM({kosten_col_letter}2:{kosten_col_letter}{total_row_idx - 1})"
            worksheet[f"{kosten_col_letter}{total_row_idx}"].number_format = '#,##0.00 "CHF"'
            # Fettdruck für die Ergebniszeile
            bold_font = Font(bold=True)
            for col in range(1, end_col_idx + 1):
                worksheet.cell(row=total_row_idx, column=col).font = bold_font

    ic("Rechnungsübersicht gespeichert:" + str(summary_file))


def main():
    # Rich Traceback für bessere Fehlermeldungen
    install(show_locals=True)
    # Alle Konfigurationsdaten laden
    cwd = Path(__file__).parent.parent.parent / ".config"
    with open(cwd / "wegpiraten_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    prj_root = Path(config["prj_root"])
    data_path = Path(config["data_path"])
    output_path = prj_root / config["output_path"]
    template_path = prj_root / config["template_path"]
    tmp_path = prj_root / config["tmp_path"]
    template_name = config["invoice_template_name"]
    invoice_template = DocxTemplate(template_path / template_name)
    db_name = config["db_name"]
    sheet_name = config["sheet_name"]
    expected_columns = config["expected_columns"]

    # tmp putzen, evtl context manager nutzen?
    clear_path(tmp_path)

    # TODO: dynamisch einlesen
    abrechnungsmonat = "2025-08"  # YYYY-MM

    # Aufwandsdaten für den Abrechnungsmonat aus der DB (Excel) laden
    invoice_data = load_data(data_path / db_name, 
                             sheet_name, 
                             abrechnungsmonat)

    check_data_consistency(invoice_data, 
                           expected_columns)

    # Rechnungsübersicht initialisieren
    summary_rows = []

    # Nach Zahlungsdienstleister gruppieren
    zd_grouped = invoice_data.groupby("ZDNR")

    for zdnr, zd_data in zd_grouped:
        ic("Verarbeite Zahlungsdienstleister " + zd_data['ZD_Name'].iloc[0])
        # Liste für die Rechnungsdateien dieses Zahlungsdienstleisters
        invoice_group: list[Path] = []

        # Innerhalb des ZD nach Klient-Nr. gruppieren
        client_grouped = zd_data.groupby("Klient-Nr.")

        # Für jeden Klienten eine Rechnung erstellen
        for client_id, client_details in client_grouped:
            formatted_invoice, updated_data = format_invoice(
                invoice_template, client_details
            )
            re_nr:str = updated_data["Rechnungsnummer"].iloc[0]
            docx_path:Path = tmp_path / f"Rechnung_{re_nr}.docx"
            formatted_invoice.save(docx_path)
            # DOCX zu PDF konvertieren, um später zusammenzufassen
            # in merge_pdfs()
            docx_to_pdf(docx_path, _ := docx_path.with_suffix(".pdf"))
            
            invoice_group.append(_)

            # Summarische Daten sammeln
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

        merge_pdfs(invoice_group, 
                output_path, 
                zdnr, 
                abrechnungsmonat)
        # Ende Klienten-Schleife
    
    # Summarische Tabelle als Excel ausgeben
    create_summary(summary_rows, 
                   output_path, 
                   abrechnungsmonat)
    
    # Alle Rechnungen im Word Format in eine ZIP-Datei packen und im output
    # Verzeichnis ablegen
    zip_docs(tmp_path, output_path / f"Rechnungen_{abrechnungsmonat}.zip")
   
    # Ende Zahlungsdienstleister-Schleife



if __name__ == "__main__":
    ic.configureOutput(prefix='', outputFunction=print)
    # ic.disable()  # Falls du die Ausgabe komplett abschalten willst

    # Nur das Ergebnis ausgeben (ohne Variable, Datei, Zeilennummer etc.)
    def ic_simple_format(*args):
        return " ".join(str(arg) for arg in args)
    ic.format = ic_simple_format
    
    main()