from typing import Optional
from pydantic import BaseModel

class ReportingRowModel(BaseModel):
    """
    Pydantic-Modell für die Felder, die zur Erzeugung der Zeiterfassungs-Sheets benötigt werden.
    """

    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = 'Undefiniert'
    employee_id: Optional[str] = 'M000'
    allowed_hours_per_month: float
    service_type: str
    short_code: str
    client_id: str
