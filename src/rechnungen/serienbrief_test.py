import pandas as pd
from docxtpl import DocxTemplate
from rich import print
from pathlib import Path

prj_root = Path(__file__).parent.parent.parent
data_path = prj_root / "daten"
output_path = prj_root / "output"

# Pfad zur Excel-Datei
steuer_daten = Path(data_path / "test_serienbrief.xlsx")

# Excel-Daten laden
df = pd.read_excel(steuer_daten)

# Nach Brief_ID gruppieren
# Alle Felder sind kontext-sensitiv!
client = df.groupby("Brief_ID")

template = DocxTemplate(prj_root / "vorlagen" / "rechnungsvorlage.docx")

for brief_id, daten in client:
    # Kopf-Daten (nehmen wir aus der ersten Zeile)
    kopf = daten.iloc[0].to_dict()

    # Tabellen-Daten (alle Zeilen für diese Gruppe)
    positionen = daten[["Artikel", "Menge", "Preis"]].to_dict(orient="records")

    # Kontext fürs Template
    context = {
        "Name": kopf["Name"],
        "Adresse": kopf["Adresse"],
        "Positionen": positionen
    }

    # Rendern
    template.render(context)
    template.save(output_path / f"serienbrief_{brief_id}.docx")