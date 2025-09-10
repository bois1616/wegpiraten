from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import yaml
from docxtpl import DocxTemplate  # type: ignore
from openpyxl import load_workbook
from rich import print

#from datetime import datetime

def format_2f(value: float, currency: str = None) -> str:
    if pd.isna(value):
        return ""
    currency = currency or ""
    if currency and not currency.startswith(" "):
        currency = " " + currency
    # Tausenderpunkt, Dezimalkomma
    tmp_val = f"{value:,.2f}"
    tmp_val = tmp_val.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{tmp_val}{currency}"
 

def load_data(db: Path, sheet: str) -> pd.DataFrame:
    """
    Lade die Aufwandsdaten aus der Excel-DB
    Achtung: Filter in der Excel-Abfrage bleiben bestehen

    Args:
        db (Path): Ort der Datenbank (Excel-Datei)
        sheet (str): Name des Arbeitsblatts

    Returns:
        pd.DataFrame: DataFrame mit den Aufwandsdaten
    """
    work_book = load_workbook(db, data_only=True)
    work_sheet = work_book[sheet]

    # Generator für die Zeilen
    data = work_sheet.values

    # Erste drei Zeilen sind Metadaten
    # Eventuell besser, bis zu einem Schlüsselwort zu springen
    for _ in range(3):
        next(data)
    
    # Erste Zeile sind die Spaltennamen, aber ohne die erste Spalte (ID)
    columns = next(data)[1:]  

    # Daten ab zweiter Spalte
    df = pd.DataFrame((row[1:] for row in data),
                      columns=columns,
                      )
    
    # Todo: Prüfen, ob das notwendig ist
    df["Leistungsdatum"] = pd.to_datetime(df["Leistungsdatum"], errors="coerce", format="%d.%m.%Y")
    df["Start_AbrMon"] = pd.to_datetime(df["Start_AbrMon"], errors="coerce", format="%d.%m.%Y")
    df["End_AbrMon"] = pd.to_datetime(df["End_AbrMon"], errors="coerce",  format="%d.%m.%Y")

    # Fehlende Werte in ZD_Name2 mit Leerzeichen auffüllen/ersetzen
    df["ZD_Name2"] = df["ZD_Name2"].fillna("").replace("(Leer)", "")

    return df


def create_invoice_id(inv_month: Optional[pd.Timestamp] = None,
                      client_id: Optional[str] = None) -> str:
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
    if client_id is None:
        client_id = "K000"

    month_mmYY = inv_month.strftime("%m%y") if pd.notna(inv_month) else ""
    return f"R{month_mmYY}_{client_id}"


def format_invoice(invoice_template: DocxTemplate,
                   client_details: pd.DataFrame
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
    client_details["Summe_Fahrtzeit"] = client_details['Fahrtzeit'].sum()
    client_details["Summe_Direkt"] = client_details['Direkt'].sum()
    client_details["Summe_Indirekt"] = client_details['Indirekt'].sum()
    client_details["Summe_Stunden"] = client_details['Stunden'].sum()
    client_details["Summe_Kosten"] = client_details['Kosten'].sum()

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
        client_details[f"{col}_2f"] = client_details[col].apply(lambda x: format_2f(x, currency) if pd.notna(x) else "")

    client_details["Leistungsdatum"] = client_details["Leistungsdatum"].dt.strftime("%d.%m.%Y")
    client_details["AbrMon"] = client_details["Start_AbrMon"].dt.strftime("%m.%Y")
    client_details["Rechnungsdatum"] = pd.Timestamp.now().strftime("%d.%m.%Y")

    # Rechnungsnummer generieren
    invoice_id = create_invoice_id(
        inv_month=client_details["Start_AbrMon"].iloc[0],
        client_id=client_details["Klient-Nr."].iloc[0]
    )

    client_details["Rechnungsnummer"] = invoice_id

    print(f"Erstelle Rechnung {invoice_id}")

    # Kopf-Daten (sind für alle Zeilen der Gruppe gleich, 
    # nehmen wir die aus der ersten Zeile (Index 0))
    # Summen üer relevante Spalten in die Daten übernehmen
    context_data = client_details.iloc[0].to_dict()

    # Tabellen-Daten (alle Zeilen für diese Gruppe)
    invoice_positions = client_details[
        ["Leistungsdatum",
         "Fahrtzeit_2f",
         "Direkt_2f",
         "Indirekt_2f",
         "Sollstunden_2f",
         #"Stundensatz_2f",
         "km_Pauschale_2f",
         "Stunden_2f",
         "Kosten_2f"]]

    invoice_positions = invoice_positions.to_dict(orient="records")
    
    # Kontext fürs Template
    # Felder im Template müssen mit den Keys im Kontext 
    # exakt übereinstimmen (inkl. Groß-/Kleinschreibung)
    context = {**context_data, "Positionen": invoice_positions}

    # Rendern
    invoice_template.render(context)
    return invoice_template, client_details


if __name__ == "__main__":

    # Alle Konfigurationsdaten laden
    cwd = Path(__file__).parent.parent.parent / ".config"
    with open(cwd / "wegpiraten_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    prj_root = Path(config["prj_root"])
    data_path = Path(config["data_path"])
    output_path = prj_root / config["output_path"]
    template_path = prj_root / config["template_path"]
    template_name = config["invoice_template_name"]
    invoice_template = DocxTemplate(template_path / template_name)              
    db_name = config["db_name"]
    sheet_name = config["sheet_name"]

    abrechnungsmonat = "2025-08"  # YYYY-MM

    # Aufwandsdaten aus der DB (Excel) laden
    # TODO Filtern nach Abrechnungsmonat
    invoice_data = load_data(data_path / db_name, sheet_name)

    # Debug only
    print(invoice_data.head())
    invoice_data.to_excel(output_path / "data.xlsx")

    # TODO nach Zahlungsdienstleister gruppieren
    # Nach Brief_ID gruppieren
    client_grouped = invoice_data.groupby("Klient-Nr.")

    # TODO Klären, ob alle Rechnungen in ein Dokument sollen oder einzelne
    # Für jeden Klienten eine Rechnung erstellen
    for client_id, client_details in client_grouped:

        formatted_invoice, updated_data = format_invoice(invoice_template,
                                 client_details
                                 , )
        # Kopf-Daten (sind für alle Zeilen der Gruppe gleich, nehmen wir aus der ersten Zeile)

        # TODO Alle Rechnungen als PDF
        re_nr = updated_data["Rechnungsnummer"].iloc[0]
        formatted_invoice.save(output_path /
                               f"Rechnung_{re_nr}.docx")