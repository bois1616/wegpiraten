import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import qrcode
from babel.numbers import format_decimal
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from jinja2 import Environment
from PIL import Image, ImageDraw, ImageFont

from shared_modules.config import Config
from shared_modules.entity import LegalPerson
from shared_modules.utils import (
    safe_str,  # Zentrale String-Konvertierung für Typensicherheit
)

from .invoice_context import InvoiceContext


class InvoiceFactory:
    """
    Factory-Klasse zur Erstellung von Rechnungen und Einzahlungsscheinen.
    Nutzt Babel/Jinja2-Filter für die Formatierung.
    Erwartet eine Pydantic-basierte Konfiguration und Entity-Objekte.
    """

    def __init__(self, config: Config):
        """
        Initialisiert die Factory mit einer Pydantic-basierten Konfiguration.
        Args:
            config (Config): Singleton-Konfiguration mit Pydantic-Modell.
        """
        self.config: Config = config
        # Empfänger als Entity-Objekt, Zugriff auf Provider-Konfiguration typisiert
        provider_cfg = self.config.service_provider
        # Alle Felder werden mit safe_str abgesichert, um Typfehler zu vermeiden
        self.provider: LegalPerson = LegalPerson(
            name=safe_str(provider_cfg.name),
            street=safe_str(provider_cfg.street),
            zip_city=f"{provider_cfg.zip_code} {provider_cfg.city}",
            iban=safe_str(provider_cfg.iban),
        )

    def create_invoice_id(self, client_id: str, invoice_month: str) -> str:
        """
        Erstellt eine eindeutige Rechnungsnummer aus Leistungszeitraum und Klienten-ID.
        Args:
            client_id (str): Klienten-ID.
            invoice_month (str): Abrechnungsmonat im Format 'MM-YYYY'.
        Returns:
            str: Rechnungsnummer im Format 'MM-YYYY_CLIENTID'.
        """

        # TODO Prüfen, ob das als Rechnungsnummer ausreicht
        return f"{invoice_month or 'mm.YYYY'}-{client_id or 'K000'}"

    def create_payment_part_png(
        self,
        invoice_context: InvoiceContext,
        output_png: str,
        font_dir: str = "/usr/share/fonts/truetype/msttcorefonts/",
    ) -> None:
        """
        Erstellt einen Einzahlungsschein als PNG mit QR-Code.
        Nutzt ausschließlich typisierte Entity- und Kontextdaten.
        Args:
            invoice_context (InvoiceContext): Kontext mit Rechnungsdaten.
            output_png (str): Zielpfad für das PNG.
            font_dir (str): Verzeichnis mit Schriftarten.
        """
        Path(output_png).parent.mkdir(parents=True, exist_ok=True)
        width, height = 1800, 900
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        _FONT_CANDIDATES = [
            (str(Path(font_dir) / "calibri.ttf"), str(Path(font_dir) / "calibrib.ttf")),
            ("/mnt/c/Windows/Fonts/calibri.ttf", "/mnt/c/Windows/Fonts/calibrib.ttf"),
            (
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ),
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ),
        ]
        font = font_bold = font_small_bold = ImageFont.load_default()
        for _regular, _bold in _FONT_CANDIDATES:
            try:
                font = ImageFont.truetype(_regular, 36)
                font_bold = ImageFont.truetype(_bold, 48)
                font_small_bold = ImageFont.truetype(_bold, 28)
                break
            except Exception:
                continue

        # Service Provider aus typisiertem Entity-Objekt
        service_provider: LegalPerson = self.provider
        payer = invoice_context.data.get("payer")

        provider_name = safe_str(getattr(service_provider, "name", ""))
        provider_street = safe_str(getattr(service_provider, "street", ""))
        provider_zip_city = safe_str(getattr(service_provider, "zip_city", ""))
        provider_zip = safe_str(getattr(service_provider, "zip", ""))
        provider_city = safe_str(getattr(service_provider, "city", ""))
        provider_iban = safe_str(getattr(service_provider, "iban", ""))

        payer_name = safe_str(getattr(payer, "name", ""))
        payer_street = safe_str(getattr(payer, "street", ""))
        payer_zip_city = safe_str(getattr(payer, "zip_city", ""))
        payer_zip = safe_str(getattr(payer, "zip", ""))
        payer_city = safe_str(getattr(payer, "city", ""))

        currency = self.config.get_currency()
        invoice_id = safe_str(invoice_context.data.get("invoice_id", "-ReNr-"))
        total_amount = invoice_context.data.get("summe_kosten", None)
        total_display = self._format_amount_display(total_amount)

        # Linien
        divider_x = 600
        draw.line([(divider_x, 60), (divider_x, height - 60)], fill="black", width=3)
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
        ]:
            if label:
                y1 += 10
                draw.text((x1, y1), label, font=font_small_bold, fill="black")
                y1 += 30
            draw.text((x1, y1), safe_str(value), font=font, fill="black")
            y1 += 40

        y1 += 10
        self._draw_amount_block(draw, x1, y1, currency, total_display, font_small_bold, font)

        # Rechter Bereich: Zahlteil (QR links, Textblock rechts)
        qr_size = 418
        qr_x = divider_x + 40
        qr_y = (height - qr_size) // 2
        x2, y2 = qr_x + qr_size + 40, 100
        draw.text((qr_x, 100), "Zahlteil", font=font_bold, fill="black")
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
        ]:
            if label:
                y2 += 10
                draw.text((x2, y2), label, font=font_small_bold, fill="black")
                y2 += 30
            draw.text((x2, y2), safe_str(value), font=font, fill="black")
            y2 += 40

        # QR-Code-Daten aus Kontext
        qr_data = self._build_spc_payload(
            provider_name=provider_name,
            provider_street=provider_street,
            provider_zip=provider_zip,
            provider_city=provider_city,
            provider_iban=provider_iban,
            payer_name=payer_name,
            payer_street=payer_street,
            payer_zip=payer_zip,
            payer_city=payer_city,
            amount=total_amount,
            currency=currency,
            additional_info=invoice_id,
        )
        qr_img = qrcode.make(qr_data)
        # qrcode mit PIL-Backend gibt ein PIL.Image zurück
        qr_img = qr_img.get_image().convert("RGB").resize((qr_size, qr_size))  # type: ignore[union-attr]
        img.paste(qr_img, (qr_x, qr_y))
        amount_y = qr_y + qr_size + 20
        self._draw_amount_block(draw, qr_x, amount_y, currency, total_display, font_small_bold, font)
        img.save(output_png)

    @staticmethod
    def _split_street(street: str) -> Tuple[str, str]:
        cleaned = safe_str(street)
        parts = cleaned.split()
        if not parts:
            return "", ""
        last = parts[-1]
        if any(ch.isdigit() for ch in last):
            return " ".join(parts[:-1]).strip() or cleaned, last
        return cleaned, ""

    @staticmethod
    def _format_amount(amount: Optional[float]) -> str:
        if amount is None:
            return ""
        try:
            return f"{float(amount):.2f}"
        except (TypeError, ValueError):
            return ""

    def _format_amount_display(self, amount: Optional[float]) -> str:
        if amount is None:
            return ""
        try:
            numeric_format = self.config.formatting.numeric_format or "#,##0.00"
            locale = self.config.formatting.locale or "de_CH"
            return format_decimal(float(amount), format=numeric_format, locale=locale)
        except Exception:
            return self._format_amount(amount)

    @staticmethod
    def _draw_amount_block(
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        currency: str,
        amount: str,
        font_label: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_value: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> None:
        col_gap = 180
        draw.text((x, y), "Währung", font=font_label, fill="black")
        draw.text((x + col_gap, y), "Betrag", font=font_label, fill="black")
        y += 32
        draw.text((x, y), safe_str(currency), font=font_value, fill="black")
        draw.text((x + col_gap, y), safe_str(amount), font=font_value, fill="black")

    def _address_lines_structured(self, name: str, street: str, zip_code: str, city: str) -> List[str]:
        if not name:
            return [""] * 7
        street_name, house_no = self._split_street(street)
        return [
            name,
            "S",
            street_name,
            house_no,
            zip_code,
            city,
            "CH",
        ]

    def _build_spc_payload(
        self,
        provider_name: str,
        provider_street: str,
        provider_zip: str,
        provider_city: str,
        provider_iban: str,
        payer_name: str,
        payer_street: str,
        payer_zip: str,
        payer_city: str,
        amount: Optional[float],
        currency: str,
        additional_info: str,
    ) -> str:
        """
        Erzeugt den QR-Referenzstring gemäss SPS (SPC) Version 2.3 mit Adresstyp S.
        """
        creditor_lines = self._address_lines_structured(provider_name, provider_street, provider_zip, provider_city)
        debtor_lines = self._address_lines_structured(payer_name, payer_street, payer_zip, payer_city)
        amount_str = self._format_amount(amount)

        lines = [
            "SPC",
            "0200",
            "1",
            provider_iban,
            *creditor_lines,
            "",  # Ultimate creditor name
            "",  # Ultimate creditor address type
            "",  # Ultimate creditor street
            "",  # Ultimate creditor house number
            "",  # Ultimate creditor postal code
            "",  # Ultimate creditor city
            "",  # Ultimate creditor country
            amount_str,
            currency,
            *debtor_lines,
            "NON",
            "",
            safe_str(additional_info),
            "EPD",
            "",
            "",
        ]
        return "\n".join(lines)

    def render_invoice(
        self,
        invoice_context: InvoiceContext,
        jinja_env: Optional[Environment] = None,
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
        # Zugriff auf Pfade und Template-Namen über typisierte Pydantic-Konfiguration
        template_name = self.config.templates.invoice_template_name or "rechnungsvorlage.docx"
        template_path = self.config.get_template_path(template_name)
        if not template_path.exists():
            raise FileNotFoundError(f"Template nicht gefunden: {template_path}")

        invoice_template = DocxTemplate(template_path)

        # Einzahlungsschein-Bild erzeugen, temporär speichern
        tmp_dir = self.config.get_tmp_path()
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=tmp_dir, suffix=".png", delete=True) as tmp_file:
            self.create_payment_part_png(invoice_context, tmp_file.name)
            payment_part_img = InlineImage(invoice_template, tmp_file.name, width=Mm(200))
            invoice_context["payment_part"] = payment_part_img

            # Optional: Template- und Kontext-Felder vergleichen (Debug)
            # template_fields = invoice_template.get_undeclared_template_variables(jinja_env=jinja_env)
            # print('Template (ist):\n', template_fields)
            # context_fields = list(invoice_context.as_dict().keys())
            # print('Kontext (Soll)\n', context_fields)
            # print('Positionen-Felder:')
            # print(invoice_context["positions"][0] if invoice_context["positions"] else "Keine Positionen")
            # exit(0)

            invoice_template.render(invoice_context.as_dict(), jinja_env=jinja_env)

        return invoice_template


if __name__ == "__main__":
    print("InvoiceFactory Modul. Nicht direkt ausführbar.")
