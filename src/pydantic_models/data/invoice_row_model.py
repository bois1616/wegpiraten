from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


class InvoiceRowModel(BaseModel):
    """
    Fachliches Datenmodell für eine einzelne Zeit­erfassungs- bzw. Rechnungsposition.
    Dieses Modell wird sowohl beim Import der ausgefüllten Excel-Sheets (Staging in invoice_data)
    als auch bei nachgelagerten Auswertungen verwendet. Alle Felder müssen mit der Entity-
    Definition `invoice_data` in der Config übereinstimmen.
    """
    client_id: str
    employee_id: str
    service_date: date
    service_type: str

    travel_time: float = 0.0
    direct_time: float = 0.0
    indirect_time: float = 0.0
    billable_hours: float = 0.0

    hourly_rate: Optional[float] = None
    total_hours: Optional[float] = None
    total_costs: Optional[float] = None

    @field_validator("billable_hours", mode="before")
    @classmethod
    def default_billable_hours(cls, value, values):
        """
        Falls das Excel-Sheet keine eigenen verrechenbaren Stunden liefert,
        wird standardmäßig direct_time + indirect_time verwendet.
        """
        if value is None:
            return float(values.get("direct_time", 0.0)) + float(values.get("indirect_time", 0.0))
        return value

    @field_validator("total_hours", mode="before")
    @classmethod
    def default_total_hours(cls, value, values):
        """
        Gesamtstunden sind S0-Feld (Reise + direkte + indirekte Zeiten).
        """
        if value is None:
            return (
                float(values.get("travel_time", 0.0))
                + float(values.get("direct_time", 0.0))
                + float(values.get("indirect_time", 0.0))
            )
        return value

    @field_validator("total_costs", mode="before")
    @classmethod
    def default_total_costs(cls, value, values):
        """
        Bei gesetztem Stundensatz den Betrag automatisch berechnen.
        """
        if value is None and values.get("hourly_rate") is not None:
            return float(values.get("billable_hours", 0.0)) * float(values["hourly_rate"])
        return value