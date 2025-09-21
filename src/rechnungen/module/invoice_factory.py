import tempfile
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import qrcode
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .entity import LegalPerson
from .utils import format_2f
from .invoice_context import InvoiceContext
from loguru import logger


class InvoiceFactory:
    """
    Factory-Klasse zur Erstellung von Rechnungen und Einzahlungsscheinen.
    Nutzt die zentrale Konfiguration und stellt Methoden für die Formatierung und Dokumentenerstellung bereit.
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


    def format_fields(self, invoice_context: InvoiceContext, client_details: pd.DataFrame) -> None:
        """
        Formatiert numerische und Datumsfelder aus client_details und erweitert den Kontext um die entsprechenden Summen, *_2f und Datums-Strings.
        Es werden keine neuen Spalten im DataFrame angelegt.
        Die Werte werden als einzelne Strings im Kontext abgelegt, z.B. summe_fahrtzeit, summe_fahrtzeit_2f.
        """
        expected_columns = self.config.data["expected_columns"]
        # Segmentierte Felder aus config holen
        numeric_currency_columns = []
        date_columns = []

        # Sammle alle numerischen (ggfls mit Einheit) und Datumsfelder
        for section in ["payer", "client", "general"]:
            for col in expected_columns.get(section, []):
                if isinstance(col, dict):
                    if col.get("type") in ("numeric", "currency"):
                        numeric_currency_columns.append(col)
                    if col.get("type") == "date":
                        date_columns.append(col)

        # Numerische Felder als einzelne Werte und *_2f Strings im Kontext ablegen (Summe)
        for col in numeric_currency_columns:
            num_field = col["name"]
            currency = col.get("currency", "")
            if num_field in client_details.columns:
                value = client_details[num_field].sum()
                setattr(invoice_context, f"summe_{num_field.lower()}", value)
                formatted: str = format_2f(value, currency) if pd.notna(value) else ""
                setattr(invoice_context, f"summe_{num_field.lower()}_2f", formatted)

        # Datumsfelder als einzelne Strings im Kontext ablegen (z.B. frühestes Datum)
        for col in date_columns:
            date_field = col["name"]
            date_format = col.get("format", "%d.%m.%Y")
            if date_field in client_details.columns:
                value = pd.to_datetime(client_details[date_field], errors="coerce").min()
                formatted: str = value.strftime(date_format) if pd.notna(value) else ""
                setattr(invoice_context, f"{date_field.lower()}_short", formatted)

    def create_payment_part_png(
        self,
        context: InvoiceContext,
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
        payer = context.payer

        provider_name = getattr(service_provider, "name", "")
        provider_street = getattr(service_provider, "strasse", "")
        provider_zip_city = getattr(service_provider, "zip_city", getattr(service_provider, "plz_ort", ""))
        provider_iban = getattr(service_provider, "iban", "")

        payer_name = getattr(payer, "name", "")
        payer_street = getattr(payer, "strasse", "")
        payer_zip_city = getattr(payer, "zip_city", getattr(payer, "plz_ort", ""))

        total_2f = getattr(context, "summe_kosten_2f", "")
        invoice_id = getattr(context, "rechnungsnummer", "")

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
            ("Währung", "CHF"),
            ("Betrag", total_2f),
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
            ("Währung", "CHF"),     # TODO: Währung aus config holen
            ("Betrag", total_2f),
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
            f"{total_2f}\nCHF\nNON\n{invoice_id}\n"
            f"{payer_name}\n{payer_street}\n{payer_zip_city}\n"
        )
        qr_img = qrcode.make(qr_data)
        qr_img = qr_img.convert("RGB").resize((300, 300))
        img.paste(qr_img, (width - 350, height // 2 - 150))
        img.save(output_png)

    def get_position_fields(self) -> list:
        """
        Gibt eine Liste der Feldnamen zurück, die in der config mit 'position: true' markiert sind.
        """
        expected_columns = self.config.data["expected_columns"]
        position_fields = []
        for section in ["payer", "client", "general"]:
            for col in expected_columns.get(section, []):
                if isinstance(col, dict) and col.get("position", False):
                    position_fields.append(col["name"])
        return position_fields

    def get_field_type_and_format(self, key: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Liefert Typ ('numeric', 'currency', 'date'), Währung und Datumsformat für ein Feld aus der config.
        """
        expected_columns = self.config.data["expected_columns"]
        for section in ["payer", "client", "general"]:
            for col in expected_columns.get(section, []):
                if isinstance(col, dict) and col["name"] == key:
                    return col.get("type"), col.get("currency"), col.get("format", "%d.%m.%Y")
        return None, None, None

    def format_position_fields(self, client_details: pd.DataFrame) -> list[dict]:
        """
        Erstellt eine Liste von Dictionaries = Zeilen für die Positionen 
        in Form formatierter *_2f Felder für numerische/currency Felder
        und *_short Felder für Datumsfelder. 
        Die Typen und Formate werden aus der Konfiguration entnommen.
        """
        position_fields = self.get_position_fields()
        positions = []
        for _, pos in client_details[position_fields].iterrows():
            pos_dict = pos.to_dict()
            for key in position_fields:
                if key in pos_dict:
                    field_type, currency, date_format = self.get_field_type_and_format(key)
                    if field_type in ("numeric", "currency"):
                        pos_dict[f"{key}_2f"] = format_2f(pos_dict[key], currency)
                    elif field_type == "date":
                        try:
                            pos_dict[f"{key}_short"] = pd.to_datetime(pos_dict[key], errors="coerce").strftime(date_format)
                        except Exception:
                            pos_dict[f"{key}_short"] = ""
            positions.append(pos_dict)
        return positions


    def render_invoice(
        self,
        invoice_context: InvoiceContext,
        client_details: pd.DataFrame,
    ) -> DocxTemplate:
        """
        Generiert ein fertig formatiertes Rechnungsdokument

        Args:
            invoice_context (InvoiceContext): _description_
            client_details (pd.DataFrame): _description_

        Returns:
            DocxTemplate: _description_
        """
        template_path = (
            Path(self.config.data["structure"]["prj_root"])
            / self.config.data["structure"]["template_path"]
            / self.config.data["invoice_template_name"]
        )
        invoice_template = DocxTemplate(template_path)

        # Kontext mit formatierten Feldern (Summenwerte) ergänzen
        self.format_fields(invoice_context, client_details)

        # Einzelpositionen formatieren
        invoice_context.details_table: list[dict] = self.format_position_fields(client_details)

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

            # Kontext kann jetzt vollständig zusammengesetzt werden
            context = invoice_context.as_dict()
            context["Positionen"] = invoice_context.details_table
            context["Einzahlungsschein"] = payment_part_img

            invoice_template.render(context)
            # Nach Verlassen des Blocks wird die Datei automatisch gelöscht

        return invoice_template

if __name__ == "__main__":
    print("InvoiceFactory Modul. Nicht direkt ausführbar.")


