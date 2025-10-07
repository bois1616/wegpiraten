from typing import Optional
from pydantic import BaseModel

class ProviderConfig(BaseModel):
    """
    Modell für die Konfiguration eines Anbieters (Provider).

    Attribute:
        IBAN (Optional[str]): IBAN des Anbieters.
        name (Optional[str]): Name des Anbieters.
        strasse (Optional[str]): Straße und Hausnummer des Anbieters.
        plz_ort (Optional[str]): Postleitzahl und Ort des Anbieters.
    """
    IBAN: Optional[str] = None
    name: Optional[str] = None
    strasse: Optional[str] = None
    plz_ort: Optional[str] = None