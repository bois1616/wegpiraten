from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .structure_config import StructureConfig
from .logging_config import LoggingConfig
from .database_config import DatabaseConfig
from .templates_config import TemplatesConfig
from .formatting_config import FormattingConfig
from .service_provider_config import ServiceProviderConfig

class FieldConfig(BaseModel):
    name: str
    type: str
    excel_column: Optional[str] = None
    default: Optional[Any] = None

class EntityModelConfig(BaseModel):
    fields: List[FieldConfig]

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