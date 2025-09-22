from pathlib import Path
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook

class ReportingFactory:
    def __init__(self, config):
        self.config = config

    def create_reporting_sheet(self, row: pd.Series, reporting_month_dt: datetime, output_path: Path, template_path: Path) -> str:
        template_name = self.config.data.get("reporting_template", "zeiterfassunsboegen.xlsx")
        wb = load_workbook(template_path / template_name)
        ws = wb.active

        ws.protection.sheet = False

        ws["c5"] = row["Sozialpädagogin"]
        ws["g5"] = row["MA_ID"]
        ws["c6"] = reporting_month_dt
        ws["c6"].number_format = "MM.YYYY"
        ws["c7"] = row["Stunden pro Monat"]
        ws["g7"] = row["SPF / BBT"]
        ws["c8"] = row["Kürzel"]
        ws["g8"] = row["KlientNr"]

        ws.protection.sheet = True
        ws.protection.enable()
        ws.protection.set_password(self.config.data.get("sheet_password", "wegpiraten"))
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

        dateiname = f"Aufwandserfassung_{reporting_month_dt.strftime('%Y-%m')}_{row['Kürzel']}.xlsx"
        wb.save(output_path / dateiname)
        return dateiname