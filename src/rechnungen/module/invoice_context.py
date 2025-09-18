from .entity import JuristischePerson, PrivatePerson

class InvoiceContext:
    def __init__(
        self,
        rechnungsnummer: str,
        rechnungsdatum: str,
        start_inv_period: str,
        end_inv_period: str,
        zahlungsdienstleister: JuristischePerson,
        empfaenger: JuristischePerson,
        client: PrivatePerson,
        summe_kosten: float = None,
        summe_kosten_2f: str = None,
        positionen: list = None,
        einzahlungsschein=None,
        **kwargs
    ):
        self.rechnungsnummer = rechnungsnummer
        self.rechnungsdatum = rechnungsdatum
        self.start_inv_period = start_inv_period
        self.end_inv_period = end_inv_period
        self.zahlungsdienstleister = zahlungsdienstleister
        self.empfaenger = empfaenger
        self.client = client
        self.summe_kosten = summe_kosten
        self.summe_kosten_2f = summe_kosten_2f
        self.positionen = positionen or []
        self.einzahlungsschein = einzahlungsschein
        # Weitere Felder aus kwargs übernehmen
        for k, v in kwargs.items():
            setattr(self, k, v)

    def as_dict(self):
        """Gibt alle Felder als Dictionary zurück (für Templates etc.)."""
        result = self.__dict__.copy()
        # Optional: Entitäten als dict ausgeben
        for key in ["zahlungsdienstleister", "empfaenger", "client"]:
            obj = result.get(key)
            if obj and hasattr(obj, "__dict__"):
                result[key] = obj.__dict__
        return result