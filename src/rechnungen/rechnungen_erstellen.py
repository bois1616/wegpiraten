import pandas as pd
from docxtpl import DocxTemplate
from openpyxl import load_workbook
from rich import print
from pathlib import Path

from datetime import datetime

def format_chf(value: float) -> str:
    if pd.isna(value):
        return ""
    return f"{value:,.2f} CHF".replace(",", "’").replace(".", ",")

# Pfade
prj_root = Path(__file__).parent.parent.parent
data_path = Path("/mnt/c/Users/micro/OneDrive/Shared/Beatus/Wegpiraten Unterlagen")
output_path = prj_root / "output"
template_path = prj_root / "vorlagen"

# Excel-Daten laden
template_name = "rechnungsvorlage.docx"
db_name = "Wegpiraten Datenbank.xlsx"
sheet_name = "Pivot Rechnungsdaten"  # Name der Excel-Tabelle
abrechnungsmonat = "2025-08"  # YYYY-MM

# Excel-Daten laden
wb = load_workbook(data_path / db_name, data_only=True)
ws = wb[sheet_name]

# Lade die Daten aus der Pivorttabelle in ein DataFrame
data = ws.values    # Generator für die Zeilen
for _ in range(3):  # Überspringe die ersten 3 Zeilen
    next(data)
columns = next(data)[1:]  # Erste Zeile als Spaltennamen, erste Spalte ignorieren

df = pd.DataFrame((row[1:] for row in data), columns=columns)  # Daten ab zweiter Spalte

#daten formatieren
df["Start_AbrMon"] = pd.to_datetime(df["Start_AbrMon"], errors="coerce").dt.strftime("%b-%Y")
df["End_AbrMon"] = pd.to_datetime(df["End_AbrMon"], errors="coerce").dt.strftime("%d.%m.%Y")
df["Leistungsdatum"] = pd.to_datetime(df["Leistungsdatum"], errors="coerce").dt.strftime("%d.%m.%Y")
df["ZD_Name2"] = df["ZD_Name2"].fillna("").replace("(Leer)", "")
df["Kosten"] = df["Kosten"].apply(format_chf)

# TODO Filtern nach Abrechnungsmonat
print(df.head())
df.to_excel(output_path / "data.xlsx")

# Nach Brief_ID gruppieren
# Alle Felder sind kontext-sensitiv!
client = df.groupby("Klient-Nr.")

template = DocxTemplate(template_path / template_name)              

# TODO Klären, ob alle Rechnungen in ein Dokument sollen oder einzelne
# Für jeden Klienten eine Rechnung erstellen
for klient_id, daten in client:
    # Kopf-Daten (nehmen wir aus der ersten Zeile)
    kopf = daten.iloc[0].to_dict()
    #TODO: Datum im Format AUG25 ausgeben
    kopf["Rechnungsnummer"] = f"R{kopf['Start_AbrMon'].strftime("%m%Y")}_{klient_id}"

    # Tabellen-Daten (alle Zeilen für diese Gruppe)
    positionen = daten[["Leistungsdatum",
                        "Fahrtzeit", 
                        "Direkt",
                        "Indirekt",
                        "Sollstunden",
                        "Stundensatz",
                        "km_Pauschale",
                        "Stunden",
                        "Kosten"]].to_dict(orient="records")

    # TODO: Felder (z.B. Datum) aus dem Template übernehmen
    # TODO: Summenzeile einbauen
    # TODO: Rechnungsnummer erzeugen und zurückschreiben bzw. Tabelle erzeugen
    
    # Kontext fürs Template
    context = {**kopf, "Positionen": positionen}

    # Rendern
    template.render(context)
    template.save(output_path / f"Rechnung_{klient_id}.docx")