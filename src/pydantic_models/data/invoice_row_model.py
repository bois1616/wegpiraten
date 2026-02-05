from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, model_validator


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
    billable_hours: Optional[float] = None

    hourly_rate: Optional[float] = None
    total_hours: Optional[float] = None
    total_costs: Optional[float] = None

    @model_validator(mode="after")
    def compute_derived_fields(self) -> "InvoiceRowModel":
        """
        Berechnet abgeleitete Felder nach der Initialisierung:
        - billable_hours: direct_time + indirect_time (falls nicht gesetzt)
        - total_hours: travel_time + direct_time + indirect_time (falls nicht gesetzt)
        - total_costs: billable_hours * hourly_rate (falls hourly_rate gesetzt)
        """
        # billable_hours
        if self.billable_hours is None:
            self.billable_hours = self.direct_time + self.indirect_time

        # total_hours
        if self.total_hours is None:
            self.total_hours = self.travel_time + self.direct_time + self.indirect_time

        # total_costs
        if self.total_costs is None and self.hourly_rate is not None:
            self.total_costs = (self.billable_hours or 0.0) * self.hourly_rate

        return self
