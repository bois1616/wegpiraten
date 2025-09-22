from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from datetime import datetime
from .utils import get_month_period

@dataclass
class InvoiceFilter:
    """Filter für Rechnungsdaten.

    Ermöglicht die Filterung nach verschiedenen Kriterien wie:
    - Zahlungsdienstleister (payer)
    - Kunde (client)
    - Leistungsanforderer (service_requester)
    - Leistungszeitraum (service_date_range)
    - Listen von Zahlungsdienstleistern oder Kunden (payer_list, client_list)
    - Weitere Kriterien können leicht hinzugefügt werden.
    Beispiel:
        filter = InvoiceFilter(
            payer="Zahlungsdienstleister A",
            client_list=["Kunde 1", "Kunde 2"],
            service_date_range=(datetime(2023, 1, 1), datetime(2023, 1, 31))
        )
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
    service_date_range: Optional[Tuple[datetime, datetime]] = field(init=False)
    payer_list: Optional[Tuple[str, str]] = None
    client_list: Optional[List[str]] = None
    # Weitere Filterkriterien können hier hinzugefügt werden

    def __post_init__(self):
        self.service_date_range = get_month_period(self.invoice_month)

    def __str__(self):
        filters = []
        filters.append(f"invoice_month={self.invoice_month}")
        if self.payer:
            filters.append(f"payer={self.payer}")
        if self.client:
            filters.append(f"client={self.client}")
        if self.service_requester:
            filters.append(f"service_requester={self.service_requester}")
        if self.service_date_range:
            start, end = self.service_date_range
            filters.append(f"service_date_range=({start.strftime('%Y-%m-%d')}, {end.strftime('%Y-%m-%d')})")
        if self.payer_list:
            filters.append(f"payer_list={self.payer_list}")
        if self.client_list:
            filters.append(f"client_list={self.client_list}")
        return "InvoiceFilter(" + ", ".join(filters) + ")"