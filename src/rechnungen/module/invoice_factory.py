import tempfile
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import qrcode
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .utils import format_2f


class InvoiceFactory:
    """
    Factory-Klasse zur Erstellung von Rechnungen und Einzahlungsscheinen.
    Nutzt die zentrale Konfiguration und stellt Methoden für die Formatierung und Dokumentenerstellung bereit.
    """

    def __init__(self, config: Config):
        """
        Initialisiert die Factory mit einer Konfigurationsinstanz.

        Args:
            config (Config): Singleton-Konfiguration mit allen Einstellungen.
        """
        self.config = config

    def create_invoice_id(
        self, inv_period: Optional[str], client_id: Optional[str]
    ) -> str:
        """
        Erstellt eine eindeutige Rechnungsnummer aus Leistungszeitraum und Klienten-ID.
        Args:
            inv_period (str): Leistungszeitraum im Format 'YYYY-MM-DD' oder 'MM-YYYY'.
            client_id (str): Klienten-ID.
        Returns:
            str: Rechnungsnummer im Format 'RMMYY_KLIENTID'.
        """
        if not inv_period:
            dt = pd.Timestamp.now()
        else:
            try:
                # Versuche verschiedene Formate zu parsen
                dt = pd.to_datetime(inv_period, errors="coerce")
                if dt is pd.NaT:
                    dt = pd.to_datetime(
                        inv_period.replace(".", "-"), format="%m-%Y", errors="coerce"
                    )
                if dt is pd.NaT:
                    raise ValueError
            except Exception:
                raise ValueError(
                    "inv_period muss 'YYYY-MM-DD', 'MM-YYYY' oder pd.Timestamp sein"
                )
        month_mmYY = dt.strftime("%m%y")
        client_id = client_id or "K000"
        return f"R{month_mmYY}_{client_id}"

    def format_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Formatiert numerische und Währungsfelder im DataFrame gemäß Konfiguration.
        Fügt für jedes Feld eine zusätzliche Spalte mit Suffix '_2f' hinzu.

        Args:
            df (pd.DataFrame): DataFrame mit den Rohdaten.

        Returns:
            pd.DataFrame: DataFrame mit formatierten Feldern.
        """
        expected_columns = self.config.data["expected_columns"]
        for col in expected_columns:
            if isinstance(col, dict) and col.get("type") in ("numeric", "currency"):
                currency = col.get("currency")
                name = col["name"]
                df[f"{name}_2f"] = df[name].apply(
                    lambda x: format_2f(x, currency) if pd.notna(x) else ""
                )
        date_format = next(
            (
                c.get("format")
                for c in expected_columns
                if isinstance(c, dict) and c["name"] == "Leistungsdatum"
            ),
            "%d.%m.%Y",
        )
        df["Leistungsdatum"] = df["Leistungsdatum"].dt.strftime(date_format)
        return df

    def create_einzahlungsschein_png(
        self,
        context: dict,
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

        empf = self.config.data["empfaenger"]
        zd_plz_ort = f"{context.get('ZD_PLZ', '')} {context.get('ZD_Ort', '')}"

        # Linien
        draw.line([(width // 2, 60), (width // 2, height - 60)], fill="black", width=3)
        draw.line([(60, 60), (width - 60, 60)], fill="black", width=2)

        # Linker Bereich: Empfangsschein
        x1, y1 = 80, 100
        draw.text((x1, y1), "Empfangsschein", font=font_bold, fill="black")
        y1 += 80
        for label, value in [
            ("Konto / Zahlbar an", empf["IBAN"]),
            ("", empf["name"]),
            ("", empf["strasse"]),
            ("", empf["plz_ort"]),
            ("Zahlbar durch", context["ZD_Name"]),
            ("", context["ZD_Strasse"]),
            ("", zd_plz_ort),
            ("Währung", "CHF"),
            ("Betrag", context["Summe_Kosten_2f"]),
        ]:
            if label:
                draw.text((x1, y1), label, font=font_small_bold, fill="black")
                y1 += 40
            draw.text((x1, y1), value, font=font, fill="black")
            y1 += 40

        # Rechter Bereich: Zahlteil
        x2, y2 = width // 2 + 80, 100
        draw.text((x2, y2), "Zahlteil", font=font_bold, fill="black")
        y2 += 80
        for label, value in [
            ("Konto / Zahlbar an", empf["IBAN"]),
            ("", empf["name"]),
            ("", empf["strasse"]),
            ("", empf["plz_ort"]),
            ("Zusätzliche Informationen", context["Rechnungsnummer"]),
            ("Zahlbar durch", context["ZD_Name"]),
            ("", context["ZD_Strasse"]),
            ("", zd_plz_ort),
            ("Währung", "CHF"),
            ("Betrag", context["Summe_Kosten_2f"]),
        ]:
            if label:
                draw.text((x2, y2), label, font=font_small_bold, fill="black")
                y2 += 40
            draw.text((x2, y2), value, font=font, fill="black")
            y2 += 40

        # QR-Code
        qr_data = (
            f"SPC\n0200\n1\n{empf['IBAN']}\n{empf['name']}\n{empf['strasse']}\n{empf['plz_ort']}\n"
            f"{context.get('Summe_Kosten_2f', '')}\nCHF\nNON\n{context.get('Rechnungsnummer', '')}\n"
            f"{context.get('ZD_Name', '')}\n{context.get('ZD_Strasse', '')}\n{zd_plz_ort}\n"
        )
        qr = qrcode.make(qr_data).resize((300, 300))
        img.paste(qr, (width - 350, height // 2 - 150))
        img.save(output_png)

    def format_invoice(
        self,
        client_details: pd.DataFrame,
        start_inv_period: Optional[str] = None,
        end_inv_period: Optional[str] = None,
    ) -> Tuple[DocxTemplate, pd.DataFrame]:
        """Erstellt eine ausgefüllte Rechnung und den Einzahlungsschein."""
        template_path = (
            Path(self.config.data["structure"]["prj_root"])
            / self.config.data["structure"]["template_path"]
            / self.config.data["invoice_template_name"]
        )
        invoice_template = DocxTemplate(template_path)

        # Summen berechnen
        for col in ["Fahrtzeit", "Direkt", "Indirekt", "Stunden", "Kosten"]:
            client_details[f"Summe_{col}"] = client_details[col].sum()
            client_details[f"Summe_{col}_2f"] = format_2f(
                client_details[f"Summe_{col}"].iloc[0],
                "CHF" if col == "Kosten" else None,
            )

        client_details = self.format_fields(client_details)
        # Leistungszeitraum übernehmen
        client_details["start_inv_period"] = start_inv_period
        client_details["end_inv_period"] = end_inv_period
        client_details["Rechnungsdatum"] = pd.Timestamp.now().strftime("%d.%m.%Y")
        invoice_id = self.create_invoice_id(
            start_inv_period, client_details["Klient-Nr."].iloc[0]
        )
        client_details["Rechnungsnummer"] = invoice_id
        print(f"Erstelle Rechnung {invoice_id}")
        # Kontext für das Template
        invoice_context = client_details.iloc[0].to_dict()
        invoice_positions = client_details[
            [
                "Leistungsdatum",
                "Fahrtzeit_2f",
                "Direkt_2f",
                "Indirekt_2f",
                "Sollstunden_2f",
                # "Stundensatz_2f",
                "km_Pauschale_2f",
                "Stunden_2f",
                "Kosten_2f",
            ]
        ]
        invoice_details = invoice_positions.to_dict(orient="records")

        output_png = self.config.data["structure"]["tmp_path"]
        with tempfile.NamedTemporaryFile(
            dir=output_png, suffix=".png", delete=True
        ) as tmp_file:
            self.create_einzahlungsschein_png(invoice_context, tmp_file.name)
            einzahlungsschein_img = InlineImage(
                invoice_template, tmp_file.name, width=Mm(200)
            )
            context = {
                **invoice_context,
                "Positionen": invoice_details,
                "Einzahlungsschein": einzahlungsschein_img,
                "start_inv_period": start_inv_period,
                "end_inv_period": end_inv_period,
            }
            invoice_template.render(context)
        return invoice_template, client_details

if __name__ == "__main__":
    print("InvoiceFactory Modul. Nicht direkt ausführbar.")

