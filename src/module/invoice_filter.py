from typing import Optional, Tuple, List
from datetime import datetime
from pydantic import BaseModel, model_validator
from .utils import safe_str
from .month_period import MonthPeriod, get_month_period  # MonthPeriod nutzen

class InvoiceFilter(BaseModel):
    """
    Pydantic-Modell für Filterkriterien bei Rechnungsdaten.

    Ermöglicht die Filterung nach verschiedenen Kriterien wie:
    - Zahlungsdienstleister (payer)
    - Kunde (client)
    - Leistungsanforderer (service_requester)
    - Leistungszeitraum (service_date_range)
    - Listen von Zahlungsdienstleistern oder Kunden (payer_list, client_list)
    - Weitere Kriterien können leicht hinzugefügt werden.

    Die Filterkriterien können kombiniert werden. Nicht gesetzte Kriterien werden ignoriert.
    Die Filterung erfolgt dynamisch basierend auf den gesetzten Attributen.

    Nomenklatur:
    - Einzelwertfilter: Attributname entspricht dem Spaltennamen (z.B. payer, client).
    - Bereichsfilter: Attributname endet auf '_range' und erwartet ein Tupel (z.B. service_date_range).
    - Listenfilter: Attributname endet auf '_list' und erwartet eine Liste oder ein Tupel (z.B. payer_list, client_list).
    """

    invoice_month: str
    payer: Optional[str] = None
    client: Optional[str] = None
    service_requester: Optional[str] = None
    service_date_range: Optional[MonthPeriod] = None  # Nutze MonthPeriod statt Tuple
    payer_list: Optional[List[str]] = None
    client_list: Optional[List[str]] = None
    # Weitere Filterkriterien können hier hinzugefügt werden

    @model_validator(mode="before")
    def ensure_str_fields(cls, data):
        """
        Sorgt dafür, dass alle string-basierten Felder wirklich als str vorliegen.
        Das verhindert Validierungsfehler, wenn z.B. IDs als int aus einer Datenquelle kommen.
        """
        for field in ["invoice_month", "payer", "client", "service_requester"]:
            if field in data and data[field] is not None:
                data[field] = safe_str(data[field])
        # Auch Listenfelder absichern
        for field in ["payer_list", "client_list"]:
            if field in data and data[field] is not None:
                data[field] = [safe_str(x) for x in data[field]]
        return data

    @model_validator(mode="after")
    def set_service_date_range(self) -> "InvoiceFilter":
        """
        Setzt service_date_range automatisch anhand des invoice_month,
        falls dieses Feld nicht explizit gesetzt wurde.
        Nutzt das Pydantic-Modell MonthPeriod für Typsicherheit.
        """
        if self.service_date_range is None and self.invoice_month:
            self.service_date_range = get_month_period(self.invoice_month)
        return self

    def __str__(self) -> str:
        """
        Gibt eine lesbare String-Repräsentation des Filters zurück.
        """
        filters: List[str] = [f"invoice_month={self.invoice_month}"]
        if self.payer:
            filters.append(f"payer={self.payer}")
        if self.client:
            filters.append(f"client={self.client}")
        if self.service_requester:
            filters.append(f"service_requester={self.service_requester}")
        if self.service_date_range:
            filters.append(
                f"service_date_range=({self.service_date_range.start.strftime('%Y-%m-%d')}, "
                f"{self.service_date_range.end.strftime('%Y-%m-%d')})"
            )
        if self.payer_list:
            filters.append(f"payer_list={self.payer_list}")
        if self.client_list:
            filters.append(f"client_list={self.client_list}")
        return "InvoiceFilter(" + ", ".join(filters) + ")"