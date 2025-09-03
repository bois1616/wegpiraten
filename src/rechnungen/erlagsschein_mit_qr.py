import qrcode
from rich import print
from pathlib import Path

prj_root = Path(__file__).parent.parent.parent
data_path = prj_root / "daten"
output_path = prj_root / "output"


# Beispiel-Daten
empfaenger = "Max Mustermann"
iban = "DE02120300000000202051"
betrag = 123.45
verwendungszweck = "Rechnung 1234"

# EPC-String nach Standard
epc = f"""BCD
001
1
SCT
{empfaenger}
{iban}
EUR{betrag:.2f}

{verwendungszweck}
"""

# QR-Code erzeugen und speichern
img = qrcode.make(epc)
img.save(output_path / "zahlung_qr.png")