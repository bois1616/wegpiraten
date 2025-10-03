from typing import Optional
from pydantic import BaseModel

from shared_modules.config import StructureConfig  # Struktur-Konfiguration importieren

class ReportingConfig(BaseModel):
    structure: StructureConfig
    db_name: str
    client_sheet_name: Optional[str] = "MD_Client"
