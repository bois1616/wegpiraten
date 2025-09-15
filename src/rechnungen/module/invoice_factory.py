import tempfile
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import qrcode  # Für QR-Code-Erstellung
from docx.shared import Mm  # Für Maßeinheiten in Word
from docxtpl import DocxTemplate, InlineImage  # Für Word-Templates und Bildintegration
from module.config import Config  # Singleton-Konfiguration
from module.utils import format_2f  # Hilfsfunktion für Zahlenformatierung
from PIL import Image, ImageDraw, ImageFont  # Für Bildbearbeitung und Einzahlungsschein


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
        self, inv_month: Optional[pd.Timestamp | str], client_id: Optional[str]
    ) -> str:
        """
        Erstellt eine eindeutige Rechnungsnummer aus Abrechnungsmonat und Klienten-ID.

        Args:
            inv_month (pd.Timestamp | str): Abrechnungsmonat als Timestamp oder 'MM-YYYY'-String.
            client_id (str): Klienten-ID.

        Returns:
            str: Rechnungsnummer im Format 'RMMYY_KLIENTID'.
        """
        if inv_month is None:
            inv_month = pd.Timestamp.now()
        if isinstance(inv_month, str):
            dt = pd.to_datetime(
                inv_month.replace(".", "-"), format="%m-%Y", errors="coerce"
            )
            if dt is pd.NaT:
                raise ValueError(
                    "inv_month muss ein String im Format 'MM-YYYY' oder ein pd.Timestamp sein"
                )
            month_mmYY = dt.strftime("%m%y")
        elif isinstance(inv_month, pd.Timestamp):
            month_mmYY = inv_month.strftime("%m%y")
        else:
            raise ValueError(
                "inv_month muss ein String im Format 'YYYY-MM' oder ein pd.Timestamp sein"
            )
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
        num_fields = []
        expected_columns = self.config.data["expected_columns"]
        for col in expected_columns:
            if isinstance(col, dict) and col.get("type") in ("numeric", "currency"):
                currency = col.get("currency")
                num_fields.append((col["name"], currency))
        for col, currency in num_fields:
            decimals = next(
                (
                    c.get("decimals", 2)
                    for c in expected_columns
                    if isinstance(c, dict) and c["name"] == col
                ),
                2,
            )
            df[f"{col}_2f"] = df[col].apply(
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
        """
        Erstellt einen Einzahlungsschein als PNG-Bild mit allen relevanten Daten und QR-Code.

        Args:
            context (dict): Kontextdaten für den Einzahlungsschein (Empfänger, Zahler, Betrag, usw.).
            output_png (str): Pfad zur Ausgabedatei (PNG).
            font_dir (str): Verzeichnis der Schriftdateien (Standard: msttcorefonts).
        """
        # Sicherstellen, dass der Zielordner existiert
        output_png_dir = Path(output_png).parent
        output_png_dir.mkdir(parents=True, exist_ok=True)

        width, height = 1800, 900
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        try:
            font_path = Path(font_dir) / "calibri.ttf"
            font_path_bold = Path(font_dir) / "calibrib.ttf"
            font = ImageFont.truetype(font_path, 36)
            font_bold = ImageFont.truetype(font_path_bold, 48)
            font_small = ImageFont.truetype(font_path, 28)
            font_small_bold = ImageFont.truetype(font_path_bold, 28)
        except Exception as e:
            print(
                "[red on white]Warnung: Calibri-Font nicht gefunden, Standardfont wird verwendet.",
                e,
            )
            font = font_bold = font_small = font_small_bold = ImageFont.load_default()

        # Empfängerdaten aus der Konfiguration
        empf = self.config.data["empfaenger"]
        empf_IBAN = empf["IBAN"]
        empf_Name = empf["name"]
        empf_Strasse = empf["strasse"]
        empf_PLZ_Ort = empf["plz_ort"]
        zd_PLZ_Ort = f"{context.get('ZD_PLZ', '')} {context.get('ZD_Ort', '')}"

        # Einzahlungsschein zeichnen (linker und rechter Bereich)
        # Linien
        draw.line([(width // 2, 60), (width // 2, height - 60)], fill="black", width=3)
        draw.line([(60, 60), (width - 60, 60)], fill="black", width=2)

        # Linker Bereich: Empfangsschein
        x1, y1 = 80, 100
        draw.text((x1, y1), "Empfangsschein", font=font_bold, fill="black")
        y1 += 80
        draw.text((x1, y1), "Konto / Zahlbar an", font=font_small_bold, fill="black")
        y1 += 40
        draw.text((x1, y1), empf_IBAN, font=font, fill="black")
        y1 += 40
        draw.text((x1, y1), empf_Name, font=font, fill="black")
        y1 += 40
        draw.text((x1, y1), empf_Strasse, font=font, fill="black")
        y1 += 40
        draw.text((x1, y1), empf_PLZ_Ort, font=font, fill="black")
        y1 += 60
        draw.text((x1, y1), "Zahlbar durch", font=font_small_bold, fill="black")
        y1 += 40
        draw.text((x1, y1), context["ZD_Name"], font=font, fill="black")
        y1 += 40
        draw.text((x1, y1), context["ZD_Strasse"], font=font, fill="black")
        y1 += 40
        draw.text((x1, y1), zd_PLZ_Ort, font=font, fill="black")
        y1 += 60
        draw.text((x1, y1), "Währung", font=font_small_bold, fill="black")
        draw.text((x1 + 180, y1), "Betrag", font=font_small_bold, fill="black")
        y1 += 40
        draw.text((x1, y1), "CHF", font=font, fill="black")
        draw.text((x1 + 180, y1), context["Summe_Kosten_2f"], font=font, fill="black")

        # Rechter Bereich: Zahlteil
        x2, y2 = width // 2 + 80, 100
        draw.text((x2, y2), "Zahlteil", font=font_bold, fill="black")
        y2 += 80
        draw.text((x2, y2), "Konto / Zahlbar an", font=font_small_bold, fill="black")
        y2 += 40
        draw.text((x2, y2), empf_IBAN, font=font, fill="black")
        y2 += 40
        draw.text((x2, y2), empf_Name, font=font, fill="black")
        y2 += 40
        draw.text((x2, y2), empf_Strasse, font=font, fill="black")
        y2 += 40
        draw.text((x2, y2), empf_PLZ_Ort, font=font, fill="black")
        y2 += 60
        draw.text(
            (x2, y2), "Zusätzliche Informationen", font=font_small_bold, fill="black"
        )
        y2 += 40
        draw.text((x2, y2), context["Rechnungsnummer"], font=font, fill="black")
        y2 += 60
        draw.text((x2, y2), "Zahlbar durch", font=font_small_bold, fill="black")
        y2 += 40
        draw.text((x2, y2), context["ZD_Name"], font=font, fill="black")
        y2 += 40
        draw.text((x2, y2), context["ZD_Strasse"], font=font, fill="black")
        y2 += 40
        draw.text((x2, y2), zd_PLZ_Ort, font=font, fill="black")
        y2 += 60
        draw.text((x2, y2), "Währung", font=font_small_bold, fill="black")
        draw.text((x2 + 180, y2), "Betrag", font=font_small_bold, fill="black")
        y2 += 40
        draw.text((x2, y2), "CHF", font=font, fill="black")
        draw.text((x2 + 180, y2), context["Summe_Kosten_2f"], font=font, fill="black")

        # QR-Code generieren nach SPC-Standard
        qr_data = f"""SPC
0200
1
{empf_IBAN}
{empf_Name}
{empf_Strasse}
{empf_PLZ_Ort}
{context.get("Summe_Kosten_2f", "")}
CHF
NON
{context.get("Rechnungsnummer", "")}
{context.get("ZD_Name", "")}
{context.get("ZD_Strasse", "")}
{zd_PLZ_Ort}
"""
        qr = qrcode.make(qr_data)
        qr = qr.resize((300, 300))
        img.paste(qr, (width - 350, height // 2 - 150))
        img.save(output_png)

    def format_invoice(
        self, client_details: pd.DataFrame
    ) -> Tuple[DocxTemplate, pd.DataFrame]:
        """
        Erstellt eine ausgefüllte Rechnung für einen Klienten und erzeugt den Einzahlungsschein.

        Args:
            client_details (pd.DataFrame): Alle Daten für den Klienten.

        Returns:
            Tuple[DocxTemplate, pd.DataFrame]: Die ausgefüllte Rechnung und die aktualisierten Daten.
        """
        invoice_template = DocxTemplate(
            Path(self.config.data["structure"]["prj_root"])
            / self.config.data["structure"]["template_path"]
            / self.config.data["invoice_template_name"]
        )
        # Summen berechnen und formatieren
        client_details["Summe_Fahrtzeit"] = client_details["Fahrtzeit"].sum()
        client_details["Summe_Direkt"] = client_details["Direkt"].sum()
        client_details["Summe_Indirekt"] = client_details["Indirekt"].sum()
        client_details["Summe_Stunden"] = client_details["Stunden"].sum()
        client_details["Summe_Kosten"] = client_details["Kosten"].sum()
        client_details["Summe_Fahrtzeit_2f"] = format_2f(
            client_details["Summe_Fahrtzeit"].iloc[0]
        )
        client_details["Summe_Direkt_2f"] = format_2f(
            client_details["Summe_Direkt"].iloc[0]
        )
        client_details["Summe_Indirekt_2f"] = format_2f(
            client_details["Summe_Indirekt"].iloc[0]
        )
        client_details["Summe_Stunden_2f"] = format_2f(
            client_details["Summe_Stunden"].iloc[0]
        )
        client_details["Summe_Kosten_2f"] = format_2f(
            client_details["Summe_Kosten"].iloc[0], "CHF"
        )
        client_details = self.format_fields(client_details)
        # Abrechnungsmonat als String extrahieren
        abrechnungsmonat: str = client_details["Leistungsdatum"].iloc[0][3:]
        client_details["AbrMon"] = abrechnungsmonat
        client_details["Rechnungsdatum"] = pd.Timestamp.now().strftime("%d.%m.%Y")
        # Rechnungsnummer generieren
        invoice_id = self.create_invoice_id(
            abrechnungsmonat, client_details["Klient-Nr."].iloc[0]
        )
        client_details["Rechnungsnummer"] = invoice_id
        print(f"Erstelle Rechnung {invoice_id}")
        # Kontext für das Template
        invoice_context = client_details.iloc[0].to_dict()
        # Positionen für die Rechnungstabelle
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
        invoice_details: dict = invoice_positions.to_dict(orient="records")
        # Einzahlungsschein als PNG erzeugen und einfügen
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
            }
            invoice_template.render(context)
        return invoice_template, client_details
