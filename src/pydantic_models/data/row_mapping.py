from typing import Optional

from pydantic import BaseModel


class RowMapping(BaseModel):
    """
    Abbildung der Excel-Spalten (A..H) auf Positions-Felder.
    Hinweis: Die Vorlage hat evtl. keine expliziten Spalten für 'billable_hours'/'hourly_rate'.
    Wir leiten billable_hours = direct_time + indirect_time ab (ohne Reisezeit).
    """

    service_time_col: str = "A"  # Uhrzeit
    service_date_col: str = "B"
    travel_time_col: str = "C"
    travel_distance_col: Optional[str] = "D"  # optional, wird nicht importiert
    direct_time_col: str = "E"
    indirect_time_col: str = "F"
    billable_hours_col: Optional[str] = "G"  # berechnet (Summe), nur informativ
    notes_col: Optional[str] = "H"  # optional, nicht importiert

    @classmethod
    def from_config(cls, cfg) -> "RowMapping":
        return cls(
            service_time_col=cfg.service_time,
            service_date_col=cfg.service_date,
            travel_time_col=cfg.travel_time,
            travel_distance_col=getattr(cfg, "travel_distance", None),
            direct_time_col=cfg.direct_time,
            indirect_time_col=cfg.indirect_time,
            billable_hours_col=getattr(cfg, "billable_hours", None),
            notes_col=getattr(cfg, "notes", None),
        )
