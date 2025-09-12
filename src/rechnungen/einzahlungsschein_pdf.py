def create_einzahlungsschein(data: dict, empfaenger: dict, output_pdf: str):
    c = canvas.Canvas(output_pdf, pagesize=A4)
    width, height = A4

    # Linien und Layout
    c.setLineWidth(1)
    c.line(width/2, 40*mm, width/2, height-40*mm)
    c.line(20*mm, height-40*mm, width-20*mm, height-40*mm)

    # Empfangen-Teil
    c.setFont("Helvetica-Bold", 14)
    c.drawString(25*mm, height-50*mm, "Empfangsschein")
    c.setFont("Helvetica", 10)
    c.drawString(25*mm, height-60*mm, "Konto / Zahlbar an")
    c.drawString(25*mm, height-65*mm, empfaenger["IBAN"])
    c.drawString(25*mm, height-70*mm, empfaenger["Name"])
    c.drawString(25*mm, height-75*mm, empfaenger["Strasse"])
    c.drawString(25*mm, height-85*mm, "Zahlbar durch")
    c.drawString(25*mm, height-90*mm, data["ZD_Name"])
    c.drawString(25*mm, height-95*mm, data["ZD_Strasse"])
    c.drawString(25*mm, height-105*mm, "Währung")
    c.drawString(45*mm, height-105*mm, "Betrag")
    c.drawString(25*mm, height-110*mm, "CHF")
    c.drawString(45*mm, height-110*mm, f"{data['Summe_Kosten']:.2f}")

    # Zahlteil
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width/2+5*mm, height-50*mm, "Zahlteil")
    c.setFont("Helvetica", 10)
    c.drawString(width/2+5*mm, height-60*mm, "Konto / Zahlbar an")
    c.drawString(width/2+5*mm, height-65*mm, empfaenger["IBAN"])
    c.drawString(width/2+5*mm, height-70*mm, empfaenger["Name"])
    c.drawString(width/2+5*mm, height-75*mm, empfaenger["Strasse"])
    c.drawString(width/2+5*mm, height-85*mm, "Zusätzliche Informationen")
    c.drawString(width/2+5*mm, height-90*mm, data['Rechnungsnummer'])
    c.drawString(width/2+5*mm, height-95*mm, "Zahlbar durch")
    c.drawString(width/2+5*mm, height-100*mm, data["ZD_Name"])
    c.drawString(width/2+5*mm, height-105*mm, data["ZD_Strasse"])
    c.drawString(width/2+5*mm, height-115*mm, "Währung")
    c.drawString(width/2+25*mm, height-115*mm, "Betrag")
    c.drawString(width/2+5*mm, height-120*mm, "CHF")
    c.drawString(width/2+25*mm, height-120*mm, f"{data['Summe_Kosten']:.2f}")

    # QR-Code generieren
    qr_data = f"""SPC
0200
1
{empfaenger['IBAN']}
{empfaenger['Name']}
{empfaenger['Strasse']}
{data['Summe_Kosten']:.2f}
CHF
{data['Rechnungsnummer']}
{data['ZD_Name']}
{data['ZD_Strasse']}"""

    qr = qrcode.make(qr_data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    qr_img = Image.open(buf)
    c.drawInlineImage(qr_img, width/2+5*mm, height-170*mm, 60*mm, 60*mm)

    c.showPage()
    c.save()