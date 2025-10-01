from typing import Any, Dict
from pydantic import BaseModel, Field

class InvoiceContext(BaseModel):
    """
    Kontext für die Rechnung.
    Enthält nur rohe Werte, keine formatierten Strings.
    Nutzt Pydantic für Typsicherheit, Validierung und Serialisierung.
    """
    data: Dict[str, Any] = Field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """
        Ermöglicht den Zugriff auf Daten wie bei einem Dictionary.
        """
        return self.data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Ermöglicht das Setzen von Werten wie bei einem Dictionary.
        """
        self.data[key] = value

    def as_dict(self) -> Dict[str, Any]:
        """
        Gibt eine Kopie der Daten als Dictionary zurück.
        """
        return self.data.copy()