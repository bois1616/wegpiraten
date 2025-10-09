from typing import Optional

from pydantic import BaseModel

from pydantic_models.data.header_cells import HeaderCells
from pydantic_models.data.row_mapping import RowMapping
from pydantic_models.data.table_range import TableRange
from shared_modules.utils import derive_table_range

class TimeSheetImportProfile(BaseModel):
    """
    Komplettes Import-Profil für Reporting-Sheets.
    - sheet_name: Name der Tabelle im Excel (aus Config.templates.sheet_name, Fallback).
    - header_cells: Adressen der Header-Zellen (müssen mit ReportingFactory übereinstimmen).
    - row_mapping: Spalten-Mapping für die Positionszeilen.
    - table_range: Bereich der Positionszeilen.
    """
    sheet_name: Optional[str]
    header_cells: HeaderCells
    row_mapping: RowMapping
    table_range: TableRange

    @classmethod
    def from_config(cls, templates_cfg) -> "TimeSheetImportProfile":
        first_col, start_row, last_col, end_row = derive_table_range(
            templates_cfg.time_sheet_data_start_cell,
            templates_cfg.time_sheet_data_end_cell,
        )
        return cls(
            sheet_name=getattr(templates_cfg, "time_sheet_sheet_name", None),
            header_cells=HeaderCells.from_config(templates_cfg.time_sheet_header_cells),
            row_mapping=RowMapping.from_config(templates_cfg.time_sheet_row_mapping),
            table_range=TableRange(
                start_row=start_row,
                end_row=end_row,
                first_col=first_col,
                last_col=last_col,
            ),
        )
