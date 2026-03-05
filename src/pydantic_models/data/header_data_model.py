from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class HeaderDataModel(BaseModel):
    """
    Fachliches Datenmodell für die Kopfzeile eines Timesheets.
    Diese Felder werden sowohl in der Factory (Sheet-Erzeugung) als auch
    im Importer (Auswertung ausgefüllter Sheets) verwendet und müssen mit
    den Entity-Definitionen aus der Config übereinstimmen.
    """

    client_id: str
    employee_id: str
    service_type: str
    short_code: str
    allowed_hours_per_month: float
    allowed_travel_time: float = 0.0
    allowed_direct_effort: float = 0.0
    allowed_indirect_effort: float = 0.0
    client_first_name: Optional[str] = None
    client_last_name: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
