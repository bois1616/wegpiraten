from typing import Optional

from pydantic import BaseModel


class TimeSheetHeaderCells(BaseModel):
    employee_name: str
    emp_id: str
    reporting_month: str
    allowed_hours_per_month: str
    service_type: str
    short_code: str
    client_id: str
    budget_travel_time: Optional[str] = None
    budget_direct_effort: Optional[str] = None
    budget_indirect_effort: Optional[str] = None


class TimeSheetRowMapping(BaseModel):
    service_time: str
    service_date: str
    travel_time: str
    travel_distance: Optional[str] = None
    direct_time: str
    indirect_time: str
    billable_hours: Optional[str] = None
    notes: str


class TemplatesConfig(BaseModel):
    invoice_template_name: Optional[str] = "Rechnungsvorlage.docx"
    sheet_name: Optional[str] = "Rechnungsdaten"
    reporting_template: Optional[str] = "time_sheet_template.xlsx"
    client_sheet_name: Optional[str] = "MD_Client"
    time_sheet_template: Optional[str] = None
    time_sheet_sheet_name: Optional[str] = None
    time_sheet_header_cells: Optional[TimeSheetHeaderCells] = None
    time_sheet_data_start_cell: Optional[str] = None
    time_sheet_data_end_cell: Optional[str] = None
    time_sheet_row_mapping: Optional[TimeSheetRowMapping] = None
