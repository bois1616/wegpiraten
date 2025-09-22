import tempfile
from pathlib import Path

import qrcode
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from jinja2 import Environment
from PIL import Image, ImageDraw, ImageFont
from rich import print

from .config import Config
from .entity import LegalPerson
from .invoice_context import InvoiceContext


class InvoiceFactory:
    """
    Factory-Klasse zur Erstellung von Rechnungen und Einzahlungsscheinen.
    Nutzt Babel/Jinja2-Filter für die Formatierung.
    """

    def __init__(self, config: Config):
        self.config = config
        # Empfänger als Entity-Objekt
        provider_cfg = self.config.data["provider"]
        self.provider = LegalPerson(
            name=provider_cfg.get("name", ""),
            street=provider_cfg.get("strasse", ""),
            zip_city=provider_cfg.get("plz_ort", ""),
            iban=provider_cfg.get("IBAN"),
        )

    def create_invoice_id(
        self, 
        client_id: str, 
        invoice_month: str) -> str:
        """
        Erstellt eine eindeutige Rechnungsnummer aus Leistungszeitraum und Klienten-ID.
        Args:
            client_id (str): Klienten-ID.
            invoice_month (str): Abrechnungsmonat im Format 'MM-YYYY'.
        Returns:
            str: Rechnungsnummer im Format 'RMMYY_CLIENTID'.
        """
    
        # TODO Prüfen, ob das als Rechnungsnummer ausreicht
        return f"{invoice_month or 'mm.YYYY'}_{client_id or 'K000'}"

    def create_payment_part_png(
        self,
        invoice_context: InvoiceContext,
        output_png: str,
        font_dir: str = "/usr/share/fonts/truetype/msttcorefonts/",
    ):
        """Erstellt einen Einzahlungsschein als PNG mit QR-Code."""
        Path(output_png).parent.mkdir(parents=True, exist_ok=True)
        width, height = 1800, 900
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(str(Path(font_dir) / "calibri.ttf"), 36)
            font_bold = ImageFont.truetype(str(Path(font_dir) / "calibrib.ttf"), 48)
            font_small = ImageFont.truetype(str(Path(font_dir) / "calibri.ttf"), 28)
            font_small_bold = ImageFont.truetype(
                str(Path(font_dir) / "calibrib.ttf"), 28
            )
        except Exception:
            font = font_bold = font_small = font_small_bold = ImageFont.load_default()

        # Service Provider nur aus Factory, im Kontext nur Referenz
        service_provider = self.provider
        payer = invoice_context.data.get("payer")

        provider_name = getattr(service_provider, "name", "")
        provider_street = getattr(service_provider, "street", "")
        provider_zip_city = getattr(service_provider, "zip_city", "")
        provider_iban = getattr(service_provider, "iban", "")

        payer_name = getattr(payer, "name", "")
        payer_street = getattr(payer, "street", "")
        payer_zip_city = getattr(payer, "zip_city", "")

        # Betragsformatierung mit Babel
        currency = self.config.get_currency()
        total_str = f'{invoice_context.data.get("summe_kosten", -999):.2f}'
        invoice_id = invoice_context.data.get("invoice_id", "-ReNr-")

        # Linien
        draw.line([(width // 2, 60), (width // 2, height - 60)], fill="black", width=3)
        draw.line([(60, 60), (width - 60, 60)], fill="black", width=2)

        # Linker Bereich: Empfangsschein
        x1, y1 = 80, 100
        draw.text((x1, y1), "Empfangsschein", font=font_bold, fill="black")
        y1 += 60
        for label, value in [
            ("Konto / Zahlbar an", provider_iban),
            ("", provider_name),
            ("", provider_street),
            ("", provider_zip_city),
            ("Zahlbar durch", payer_name),
            ("", payer_street),
            ("", payer_zip_city),
            ("Währung", currency),
            ("Betrag", total_str),
        ]:
            if label:
                y1 += 10
                draw.text((x1, y1), label, font=font_small_bold, fill="black")
                y1 += 30
            draw.text((x1, y1), str(value) if value is not None else "", font=font, fill="black")
            y1 += 40

        # Rechter Bereich: Zahlteil
        x2, y2 = width // 2 + 80, 100
        draw.text((x2, y2), "Zahlteil", font=font_bold, fill="black")
        y2 += 60
        for label, value in [
            ("Konto / Zahlbar an", provider_iban),
            ("", provider_name),
            ("", provider_street),
            ("", provider_zip_city),
            ("Zusätzliche Informationen", invoice_id),
            ("Zahlbar durch", payer_name),
            ("", payer_street),
            ("", payer_zip_city),
            ("Währung", currency),
            ("Betrag", total_str),
        ]:
            if label:
                y2 += 10
                draw.text((x2, y2), label, font=font_small_bold, fill="black")
                y2 += 30
            draw.text((x2, y2), str(value) if value is not None else "", font=font, fill="black")
            y2 += 40

        # QR-Code-Daten aus Kontext
        qr_data = (
            f"SPC\n0200\n1\n{provider_iban}\n{provider_name}\n{provider_street}\n{provider_zip_city}\n"
            f"{total_str}\n{currency}\nNON\n{invoice_id}\n"
            f"{payer_name}\n{payer_street}\n{payer_zip_city}\n"
        )
        qr_img = qrcode.make(qr_data)
        qr_img = qr_img.convert("RGB").resize((300, 300))
        img.paste(qr_img, (width - 350, height // 2 - 150))
        img.save(output_png)

    def render_invoice(
        self,
        invoice_context: InvoiceContext,
        jinja_env: Environment = None,
    ) -> DocxTemplate:
        """
        Generiert ein fertig formatiertes Rechnungsdokument.
        Die Formatierung erfolgt ausschließlich im Template via Jinja2-Filter.

        Args:
            invoice_context (InvoiceContext): Kontext mit Rechnungsdaten.
            jinja_env (Environment, optional): Jinja2-Environment mit registrierten Filtern.
        
        Returns:
            DocxTemplate: Gerendertes Dokument.
        """
        template_path = (
            Path(self.config.data["structure"]["prj_root"])
            / self.config.data["structure"]["template_path"]
            / self.config.data["invoice_template_name"]
        )
        assert template_path.exists(), f"Template nicht gefunden: {template_path}"

        invoice_template = DocxTemplate(template_path)

        # Einzahlungsschein-Bild wie gehabt erzeugen
        output_png = self.config.data["structure"]["tmp_path"]

        # Kontextmanager für temporäre Datei, automatische Löschung nach Verwendung
        with tempfile.NamedTemporaryFile(
            dir=output_png,
            suffix=".png",
            delete=True
        ) as tmp_file:
            self.create_payment_part_png(invoice_context, tmp_file.name)
            payment_part_img = InlineImage(
                invoice_template,
                tmp_file.name,
                width=Mm(200)
            )
            invoice_context["payment_part"] = payment_part_img

            # füge hier einen check ein, welche felder im context sind
            # vergleiche mit den feldern im template
            
            # template_fields = invoice_template.get_undeclared_template_variables(jinja_env=jinja_env)
            # print('Template (ist):\n', template_fields)
            # context_fields = list(invoice_context.as_dict().keys())
            # print('Kontext (Soll)\n', context_fields)
            # #gib die felder von Positions aus
            # print('Positionen-Felder:')
            # print(invoice_context["positions"][0] if invoice_context["positions"] else "Keine Positionen")
            # exit(0)

            invoice_template.render(invoice_context.as_dict(), jinja_env=jinja_env)

        return invoice_template

if __name__ == "__main__":
    print("InvoiceFactory Modul. Nicht direkt ausführbar.")


