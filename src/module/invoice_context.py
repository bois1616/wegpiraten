from typing import Any, Dict
from pydantic import BaseModel, Field, field_validator

class InvoiceContext(BaseModel):
    """
    Kontext für die Rechnung.
    Enthält nur rohe Werte, keine formatierten Strings.
    Nutzt Pydantic für Typsicherheit, Validierung und Serialisierung.
    """
    data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("data", mode="after")
    def validate_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optional: Validiert, dass data ein Dictionary ist.
        Hier können weitere Prüfungen ergänzt werden.
        """
        if not isinstance(v, dict):
            raise ValueError("data muss ein Dictionary sein.")
        return v

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