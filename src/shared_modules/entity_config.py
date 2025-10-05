from pydantic import BaseModel
from typing import Optional

class Employee(BaseModel):
    PersNr: str
    Name: str
    Vorname: str
    Nachname: str
    FTE: Optional[float]
    Kommentar: Optional[str]
    # ...weitere Felder...

class Payer(BaseModel):
    ZdNr: str
    Name: str
    Name2: Optional[str]
    Strasse: str
    PLZ: str
    Ort: str
    Kommentar: Optional[str]
    # ...weitere Felder...

class ServiceRequester(BaseModel):
    LBNr: str
    Name: str
    # ...weitere Felder...

class Client(BaseModel):
    KlientNr: str
    Vorname: str
    Nachname: str
    Kuerzel: Optional[str]
    payer_id: Optional[str]  # ZdNr als Fremdschlüssel
    service_requester_id: Optional[str]  # LBNr als Fremdschlüssel
    Start: Optional[str]  # Datum als String, z.B. "2023-01-15"
    Ende: Optional[str]  # Datum als String
    betreuer_id: Optional[str]  # PersNr als Fremdschlüssel
    Stunden_pro_monat: Optional[float]
    Betreuungstyp: Optional[str] # kann SPF oder BBT sein
    Kommentar: Optional[str]
    # ...weitere Felder...
