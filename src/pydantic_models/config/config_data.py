from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .structure_config import StructureConfig
from .logging_config import LoggingConfig
from .database_config import DatabaseConfig
from .templates_config import TemplatesConfig
from .formatting_config import FormattingConfig
from .service_provider_config import ServiceProviderConfig
from .entity_model_config import EntityModelConfig



class ConfigData(BaseModel):
    """
    Modell für die gesamte Konfiguration des Projekts.
    Das sind die Sektionen in der Config-Datei.
    """
    structure: StructureConfig
    database: DatabaseConfig
    logging: LoggingConfig
    templates: TemplatesConfig
    formatting: FormattingConfig
    service_provider: ServiceProviderConfig

    models: Dict[str, EntityModelConfig]
    table_mappings: Dict[str, Dict[str, str]]



class TimeSheetHeaderCells(BaseModel):
    employee_name: str
    emp_id: str
    reporting_month: str
    allowed_hours_per_month: str
    service_type: str
    short_code: str
    client_id: str

class TimeSheetRowMapping(BaseModel):
    service_time: str
    service_date: str
    travel_time: str
    travel_distance: str
    direct_time: str
    indirect_time: str
    billable_hours: str
    notes: str

class TemplatesConfig(BaseModel):
    invoice_template_name: str
    time_sheet_template: str
    sheet_name: Optional[str] = None  # legacy
    client_sheet_name: Optional[str] = None  # legacy
    time_sheet_sheet_name: Optional[str] = None
    time_sheet_header_cells: TimeSheetHeaderCells
    time_sheet_data_start_cell: str
    time_sheet_data_end_cell: str
    time_sheet_row_mapping: TimeSheetRowMapping