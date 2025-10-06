from typing import Optional
from pydantic import BaseModel

class TemplatesConfig(BaseModel):
    invoice_template_name: Optional[str] = None
    sheet_name: Optional[str] = None
    reporting_template: Optional[str] = None
    client_sheet_name: Optional[str] = None