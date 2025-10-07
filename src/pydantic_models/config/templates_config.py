from typing import Optional
from pydantic import BaseModel

class TemplatesConfig(BaseModel):
    invoice_template_name: Optional[str] = "Rechnungsvorlage.docx"
    sheet_name: Optional[str] = "Rechnungsdaten"
    reporting_template: Optional[str] = "Reportingvorlage.xlsx"
    client_sheet_name: Optional[str] = "MD_Client"