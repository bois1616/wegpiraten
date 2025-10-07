from typing import Optional, Any, List
from pydantic import BaseModel

class FieldConfig(BaseModel):
    """
    Modell für die Definition eines einzelnen Feldes in einem Entity-Modell.
    Enthält alle relevanten Metadaten für die spätere Verarbeitung und Validierung.
    """
    name: str
    type: str
    excel_column: Optional[str] = None
    format: Optional[str] = None
    default: Optional[Any] = None
    primary_key: Optional[bool] = False
    optional: Optional[bool] = False
    sum: Optional[bool] = False
    decimals: Optional[int] = None
    is_position: Optional[bool] = None

class EntityModelConfig(BaseModel):
    """
    Modell für die Definition eines Entity-Modells in der Konfiguration.
    Enthält eine Liste von FieldConfig-Instanzen, die die Felder des Modells beschreiben.
    """
    fields: List[FieldConfig]
