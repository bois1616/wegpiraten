import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from datetime import datetime

# Pfade
prj_root = Path(__file__).parent.parent.parent
# data_path = prj_root / "daten"
data_path = Path("/mnt/c/Users/micro/OneDrive/Shared/Beatus/Wegpiraten Unterlagen")
output_path = prj_root / "output"
template_path = prj_root / "vorlagen"

# Excel-Daten laden
template_name = "zeiterfassunsboegen.xlsx"
db_name = "Wegpiraten Datenbank.xlsx"
table_name = "MD_Client"  # Name der Excel-Tabelle
abrechnungsmonat = "2025-09"  # YYYY-MM

# abrechnungsmonat als Datum
# Workbook laden
abrechnungsmonat_dt = datetime.strptime(abrechnungsmonat, "%Y-%m")
wb = load_workbook(data_path / db_name, data_only=True)
# Alle Sheets durchsuchen
for ws in wb.worksheets:
    if table_name in ws.tables:
        table = ws.tables[table_name]
        # Bereich der Tabelle, z.B. 'A1:D10'
        ref = table.ref
        # Bereich auslesen
        data = ws[ref]
        # Daten in eine Liste umwandeln
        rows = [[cell.value for cell in row] for row in data]
        # DataFrame erzeugen
        df = pd.DataFrame(rows[1:], columns=rows[0])
        break

df["Ende"] = pd.to_datetime(df["Ende"], format="%d.%m.%Y",errors="coerce")

# nur aktive Klienten (Ende >= Abrechnungsmonat)
df = df[(df["Ende"].isna()) | (df["Ende"] >= abrechnungsmonat_dt)]

# Jetzt enthält df die Daten der Tabelle "MD_Client"
print(df)

AZ_bogen = 0

for idx, row in df.iterrows():
    AZ_bogen += 1
    # Vorlage laden
    wb = load_workbook(template_path / template_name)
    ws = wb.active # ["Arbeitszeiterfassung"]

    # Blattschutz deaktivieren
    ws.protection.sheet = False

    # Felder befüllen
    ws["c5"] = row["Sozialpädagogin"]
    ws["g5"] = row["MA_ID"]
    ws["c6"] = abrechnungsmonat_dt
    ws["c6"].number_format = "MM.YYYY"
    ws["c7"] = row["Stunden pro Monat"]
    ws["g7"] = row["SPF / BBT"]
    ws["c8"] = row["Kürzel"]
    ws["g8"] = row["KlientNr"]

    print(f"Erstelle AZ Erfassungsbogen {AZ_bogen} für {row['Sozialpädagogin']} ({row['Kürzel']}, Ende: {row['Ende']})")

    # Blattschutz wieder aktivieren
    ws.protection.sheet = True
    ws.protection.enable()
    #ws.protection.password = None  # Falls kein Passwort
    ws.protection.set_password("fickdich25")

    # Optional: Nur gesperrte Zellen schützen, entsperrte bleiben frei
    ws.protection.enable_select_locked_cells = False
    ws.protection.enable_select_unlocked_cells = True
    ws.protection.format_cells = False
    ws.protection.format_columns = False
    ws.protection.format_rows = False
    ws.protection.insert_columns = False
    ws.protection.insert_rows = False
    ws.protection.insert_hyperlinks = False
    ws.protection.delete_columns = False
    ws.protection.delete_rows = False
    ws.protection.sort = False
    ws.protection.auto_filter = False
    ws.protection.objects = False
    ws.protection.scenarios = False
    
    # Neuen Z Erfassungsbogen erstellen
    dateiname = f"Aufwandserfassung_{abrechnungsmonat}_{row['Kürzel']}.xlsx"
    wb.save(output_path / dateiname)