from typing import List
from pydantic import BaseModel, Field

from .column_config import ColumnConfig


class ExpectedColumnsConfig(BaseModel):
    """
    Modell für die erwarteten Spaltenkonfigurationen verschiedener Bereiche.

    Attribute:
        payer (List[ColumnConfig]): Spalten für Zahler-Daten.
        client (List[ColumnConfig]): Spalten für Klienten-Daten.
        general (List[ColumnConfig]): Allgemeine Spalten.
    """

    payer: List[ColumnConfig] = Field(default_factory=list)
    client: List[ColumnConfig] = Field(default_factory=list)
    general: List[ColumnConfig] = Field(default_factory=list)