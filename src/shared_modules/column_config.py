from typing import Optional
from pydantic import BaseModel

class ColumnConfig(BaseModel):
    """
    Modell für die Beschreibung einer Tabellenspalte.

    Attribute:
        name (str): Name der Spalte.
        type (str): Datentyp der Spalte (z.B. "str", "int", "float").
        format (Optional[str]): Optionales Format, z.B. für Datum oder Zahlen.
        is_position (Optional[bool]): Gibt an, ob es sich um eine Positionsspalte handelt.
        sum (Optional[bool]): Gibt an, ob die Spalte summiert werden soll.
        decimals (Optional[int]): Anzahl Nachkommastellen (falls relevant).
    """
    name: str
    type: str
    format: Optional[str] = None
    is_position: Optional[bool] = None
    sum: Optional[bool] = None
    decimals: Optional[int] = None
