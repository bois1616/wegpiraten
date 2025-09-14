# filepath: /wegpiraten/wegpiraten/src/rechnungen/rechnungen_erstellen.py

import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any
from zipfile import ZipFile
import pandas as pd
import qrcode
import yaml
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.worksheet.table import Table, TableStyleInfo
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfMerger
from rich import print
from rich.traceback import install

class Config:
    def __init__(self, config_path: Path):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

class Client:
    def __init__(self, client_id: str, name: str, address: str):
        self.client_id = client_id
        self.name = name
        self.address = address

class PaymentServiceProvider:
    def __init__(self, provider_id: str, name: str, iban: str):
        self.provider_id = provider_id
        self.name = name
        self.iban = iban

class Invoice:
    def __init__(self, client: Client, provider: PaymentServiceProvider, month: str):
        self.client = client
        self.provider = provider
        self.month = month
        self.items = []
        self.total_cost = 0.0

    def add_item(self, description: str, cost: float):
        self.items.append({"description": description, "cost": cost})
        self.total_cost += cost

    def generate_invoice_id(self) -> str:
        month_mmYY = pd.to_datetime(self.month).strftime("%m%y")
        return f"R{month_mmYY}_{self.client.client_id}"

    def create_document(self) -> DocxTemplate:
        template_path = Path(CONFIG.get("structure.template_path")) / CONFIG.get("invoice_template_name")
        invoice_template = DocxTemplate(template_path)
        context = {
            "client_name": self.client.name,
            "provider_name": self.provider.name,
            "items": self.items,
            "total_cost": format_2f(self.total_cost, "CHF"),
            "invoice_id": self.generate_invoice_id(),
        }
        invoice_template.render(context)
        return invoice_template

def format_2f(value: float, currency: str = None) -> str:
    if pd.isna(value):
        return ""
    currency = currency or ""
    if currency and not currency.startswith(" "):
        currency = " " + currency
    tmp_val = f"{value:,.2f}"
    tmp_val = tmp_val.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{tmp_val}{currency}"

def load_data(db: Path, sheet: str = None, month: str = None) -> pd.DataFrame:
    work_book = load_workbook(db, data_only=True)
    work_sheet = work_book[sheet] if sheet else work_book.active
    data = work_sheet.values
    for _ in range(3):
        next(data)
    columns = next(data)[1:]
    df = pd.DataFrame((row[1:] for row in data), columns=columns)
    if month:
        month_start = pd.to_datetime(month).to_period("M").to_timestamp()
        month_end = month_start + pd.offsets.MonthEnd(0)
        df = df[(df["Leistungsdatum"] >= month_start) & (df["Leistungsdatum"] <= month_end)]
    return df

def create_invoice(db_path: Path, client_data: Dict[str, Any], provider_data: Dict[str, Any], month: str) -> Invoice:
    client = Client(client_data["Klient-Nr."], client_data["ZD_Name"], client_data["ZD_Strasse"])
    provider = PaymentServiceProvider(provider_data["ZDNR"], provider_data["ZD_Name"], provider_data["IBAN"])
    invoice = Invoice(client, provider, month)
    for index, row in client_data.iterrows():
        invoice.add_item(row["Leistungsdatum"], row["Kosten"])
    return invoice

def main():
    install(show_locals=True)
    global CONFIG
    CONFIG = Config(Path(__file__).parent.parent.parent / ".config/wegpiraten_config.yaml")

    data_path = CONFIG.get("structure.data_path")
    db_name = CONFIG.get("db_name")
    if not data_path or not db_name:
        raise ValueError(f"Fehlende Konfigurationswerte: data_path={data_path}, db_name={db_name}. Bitte prüfe die Datei .config/wegpiraten_config.yaml.")
    db_path = Path(data_path) / db_name
    month = "2025-08"
    invoice_data = load_data(db_path, CONFIG.get("sheet_name"), month)

    grouped_data = invoice_data.groupby("ZDNR")
    for provider_id, provider_data in grouped_data:
        provider_info = provider_data.iloc[0].to_dict()
        for _, client_row in provider_data.iterrows():
            invoice = create_invoice(db_path, client_row.to_dict(), provider_info, month)
            doc = invoice.create_document()
            doc.save(f"Rechnung_{invoice.generate_invoice_id()}.docx")

if __name__ == "__main__":
    main()