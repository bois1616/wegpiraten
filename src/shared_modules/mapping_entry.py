from typing import Dict
from pydantic import BaseModel

class MappingEntry(BaseModel):
    """
    Repräsentiert einen Mapping-Eintrag für ein Feld:
    - field: Ziel-Feldname im Pydantic-Modell/DB
    - type: Typ als String (z.B. 'str', 'float')
    """
    field: str
    type: str  # oder Optional[str], wenn nicht immer gesetzt

