from pathlib import Path
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook

class ReportingProcessor:
    def __init__(self, config, factory):
        self.config = config
        self.factory = factory

    def load_client_data(self, reporting_month: str) -> pd.DataFrame:
        prj_root = Path(self.config.data["structure"]["prj_root"])
        data_path = prj_root / self.config.data["structure"]["data_path"]
        db_name = self.config.data["db_name"]
        source = data_path / db_name
        table_name = self.config.data.get("client_sheet_name", "MD_Client")

        reporting_month_dt = datetime.strptime(reporting_month, "%Y-%m")
        wb = load_workbook(source, data_only=True)
        for ws in wb.worksheets:
            if table_name in ws.tables:
                table = ws.tables[table_name]
                ref = table.ref
                data = ws[ref]
                rows = [[cell.value for cell in row] for row in data]
                df = pd.DataFrame(rows[1:], columns=rows[0])
                break
        else:
            raise ValueError(f"Tabelle {table_name} nicht gefunden in {db_name}")

        df["Ende"] = pd.to_datetime(df["Ende"], format="%d.%m.%Y", errors="coerce")
        df = df[(df["Ende"].isna()) | (df["Ende"] >= reporting_month_dt)]
        return df

    def run(self, reporting_month: str, output_path: Path, template_path: Path):
        reporting_month_dt = datetime.strptime(reporting_month, "%Y-%m")
        df = self.load_client_data(reporting_month)
        for idx, row in df.iterrows():
            dateiname = self.factory.create_reporting_sheet(
                row, reporting_month_dt, output_path, template_path
            )
            print(f"Erstelle AZ Erfassungsbogen für {row['Sozialpädagogin']} ({row['Kürzel']}, Ende: {row['Ende']}) -> {dateiname}")