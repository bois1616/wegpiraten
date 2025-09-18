import tempfile
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import qrcode
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .entity import JuristischePerson, PrivatePerson
from .utils import format_2f
from .invoice_context import InvoiceContext


class InvoiceFactory:
    """
    Factory-Klasse zur Erstellung von Rechnungen und Einzahlungsscheinen.
    Nutzt die zentrale Konfiguration und stellt Methoden für die Formatierung und Dokumentenerstellung bereit.
    """

    def __init__(self, config: Config):
        self.config = config
        # Empfänger als Entity-Objekt
        empfaenger_cfg = self.config.data["empfaenger"]
        self.empfaenger = JuristischePerson(
            empfaenger_cfg.get("name", ""),
            empfaenger_cfg.get("strasse", ""),
            empfaenger_cfg.get("plz_ort", ""),
            empfaenger_cfg.get("IBAN"),
        )

    def create_invoice_id(
        self, inv_period: Optional[str], client_id: Optional[str]
    ) -> str:
        """
        Erstellt eine eindeutige Rechnungsnummer aus Leistungszeitraum und Klienten-ID.
        Args:
            inv_period (str): Leistungszeitraum im Format 'YYYY-MM-DD' oder 'MM-YYYY'.
            client_id (str): Klienten-ID.
        Returns:
            str: Rechnungsnummer im Format 'RMMYY_CLIENTID'.
        """
        if not inv_period:
            dt = pd.Timestamp.now()
        else:
            try:
                dt = pd.to_datetime(inv_period, errors="coerce")
                if pd.isna(dt):
                    dt = pd.to_datetime(
                        inv_period.replace(".", "-"), format="%m-%Y", errors="coerce"
                    )
                if pd.isna(dt):
                    raise ValueError
            except Exception:
                raise ValueError(
                    "inv_period muss 'YYYY-MM-DD', 'MM-YYYY' oder pd.Timestamp sein"
                )
        if pd.isna(dt):
            raise ValueError("Ungültiges Datum für inv_period")
        month_mmYY = dt.strftime("%m%y")
        client_id = client_id or "K000"
        return f"R{month_mmYY}_{client_id}"

    def format_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Formatiert numerische und Währungsfelder im DataFrame gemäß Konfiguration.
        Fügt für jedes Feld eine zusätzliche Spalte mit Suffix '_2f' hinzu.
        """
        expected_columns = self.config.data["expected_columns"]
        # Segmentierte Felder aus config holen
        numeric_currency_columns = []
        for section in ["zd", "cl", "allgemein"]:
            for col in expected_columns.get(section, []):
                if isinstance(col, dict) and col.get("type") in ("numeric", "currency"):
                    numeric_currency_columns.append(col)
        for col in numeric_currency_columns:
            currency = col.get("currency")
            name = col["name"]
            if name in df.columns:
                df[f"{name}_2f"] = df[name].apply(
                    lambda x: format_2f(x, currency) if pd.notna(x) else ""
                )
        # Datumsformat aus config holen
        date_format = next(
            (
                c.get("format")
                for section in ["zd", "cl", "allgemein"]
                for c in expected_columns.get(section, [])
                if isinstance(c, dict) and c["name"] == "Leistungsdatum"
            ),
            "%d.%m.%Y",
        )
        if "Leistungsdatum" in df.columns:
            df["Leistungsdatum"] = pd.to_datetime(df["Leistungsdatum"], errors="coerce").dt.strftime(date_format)
        return df

    def create_einzahlungsschein_png(
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

        empfaenger = context.empfaenger
        zd = context.zahlungsdienstleister
        zd_plz_ort = getattr(zd, "plz_ort", "")

        # Linien
        draw.line([(width // 2, 60), (width // 2, height - 60)], fill="black", width=3)
        draw.line([(60, 60), (width - 60, 60)], fill="black", width=2)

        # Linker Bereich: Empfangsschein
        x1, y1 = 80, 100
        draw.text((x1, y1), "Empfangsschein", font=font_bold, fill="black")
        y1 += 60
        for label, value in [
            ("Konto / Zahlbar an", empfaenger.iban),
            ("", empfaenger.name),
            ("", empfaenger.strasse),
            ("", empfaenger.plz_ort),
            ("Zahlbar durch", zd.name),
            ("", zd.strasse),
            ("", zd_plz_ort),
            ("Währung", "CHF"),
            ("Betrag", context.summe_kosten_2f),
        ]:
            if label:
                y1 += 10
                draw.text((x1, y1), label, font=font_small_bold, fill="black")
                y1 += 40
            draw.text((x1, y1), value, font=font, fill="black")
            y1 += 40

        # Rechter Bereich: Zahlteil
        x2, y2 = width // 2 + 80, 100
        draw.text((x2, y2), "Zahlteil", font=font_bold, fill="black")
        y2 += 60
        for label, value in [
            ("Konto / Zahlbar an", empfaenger.iban),
            ("", empfaenger.name),
            ("", empfaenger.strasse),
            ("", empfaenger.plz_ort),
            ("Zusätzliche Informationen", context.rechnungsnummer),
            ("Zahlbar durch", zd.name),
            ("", zd.strasse),
            ("", zd_plz_ort),
            ("Währung", "CHF"),
            ("Betrag", context.summe_kosten_2f),
        ]:
            if label:
                y2 += 10
                draw.text((x2, y2), label, font=font_small_bold, fill="black")
                y2 += 40
            draw.text((x2, y2), value, font=font, fill="black")
            y2 += 40

        qr_data = (
            f"SPC\n0200\n1\n{empfaenger.iban}\n{empfaenger.name}\n{empfaenger.strasse}\n{empfaenger.plz_ort}\n"
            f"{context.summe_kosten_2f}\nCHF\nNON\n{context.rechnungsnummer}\n"
            f"{zd.name}\n{zd.strasse}\n{zd_plz_ort}\n"
        )
        qr_img = qrcode.make(qr_data)
        qr_img = qr_img.convert("RGB").resize((300, 300))
        img.paste(qr_img, (width - 350, height // 2 - 150))
        img.save(output_png)

    def format_invoice(
        self,
        invoice_context: InvoiceContext,
        client_details: pd.DataFrame,
    ) -> Tuple[DocxTemplate, pd.DataFrame, InvoiceContext]:
        template_path = (
            Path(self.config.data["structure"]["prj_root"])
            / self.config.data["structure"]["template_path"]
            / self.config.data["invoice_template_name"]
        )
        invoice_template = DocxTemplate(template_path)

        # Summen berechnen (nur Rohwerte in client_details speichern)
        for col in ["Fahrtzeit", "Direkt", "Indirekt", "Stunden", "Kosten"]:
            if col in client_details.columns:
                client_details[f"Summe_{col}"] = client_details[col].sum()

        client_details = self.format_fields(client_details)

        # Formatiere Summen nur für den Kontext (nicht im DataFrame speichern)
        invoice_context.summe_kosten = client_details["Summe_Kosten"].iloc[0] if "Summe_Kosten" in client_details.columns else None
        invoice_context.summe_kosten_2f = format_2f(invoice_context.summe_kosten, "CHF") if invoice_context.summe_kosten is not None else ""

        invoice_positions = client_details[
            [
                col for col in [
                    "Leistungsdatum",
                    "Fahrtzeit",
                    "Direkt",
                    "Indirekt",
                    "Sollstunden",
                    "km_Pauschale",
                    "Stunden",
                    "Kosten",
                ] if col in client_details.columns
            ]
        ]

        # Positionen für das Template: formatiere die *_2f Felder nur für die Ausgabe
        invoice_context.positionen = []
        for _, pos in invoice_positions.iterrows():
            pos_dict = pos.to_dict()
            for key in ["Fahrtzeit", "Direkt", "Indirekt", "Sollstunden", "km_Pauschale", "Stunden", "Kosten"]:
                if key in pos_dict:
                    pos_dict[f"{key}_2f"] = format_2f(pos_dict[key], "CHF" if key == "Kosten" else None)
            invoice_context.positionen.append(pos_dict)

        output_png = self.config.data["structure"]["tmp_path"]
        with tempfile.NamedTemporaryFile(
            dir=output_png, suffix=".png", delete=True
        ) as tmp_file:
            self.create_einzahlungsschein_png(invoice_context, tmp_file.name)
            einzahlungsschein_img = InlineImage(
                invoice_template, tmp_file.name, width=Mm(200)
            )
            context = invoice_context.as_dict()
            context["Positionen"] = invoice_context.positionen
            context["Einzahlungsschein"] = einzahlungsschein_img
            invoice_template.render(context)
        return invoice_template, client_details, invoice_context

if __name__ == "__main__":
    print("InvoiceFactory Modul. Nicht direkt ausführbar.")


