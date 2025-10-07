from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator

class MonthPeriod(BaseModel):
    """
    Pydantic-Modell für einen Monatszeitraum.
    Sorgt für Typsicherheit und Validierung.
    """
    start: datetime
    end: datetime

    @field_validator("end", mode="after")
    def end_must_be_after_start(cls, v: datetime, info) -> datetime:
        """
        Validiert, dass das Enddatum nach dem Startdatum liegt.
        Args:
            v (datetime): Das Enddatum.
            info (ValidationInfo): Enthält das Startdatum.
        Returns:
            datetime: Das validierte Enddatum.
        Raises:
            ValueError: Wenn das Enddatum vor dem Startdatum liegt.
        """
        start = info.data.get("start")
        if start and v < start:
            raise ValueError("Enddatum muss nach dem Startdatum liegen.")
        return v

def get_month_period(abrechnungsmonat: str) -> MonthPeriod:
    """
    Gibt den ersten und letzten Tag eines Abrechnungsmonats als Pydantic-Modell zurück.
    Erwartet das Format MM.YYYY oder MM-YYYY.

    Args:
        abrechnungsmonat (str): Monat im Format MM.YYYY oder MM-YYYY.

    Returns:
        MonthPeriod: Pydantic-Modell mit Start- und Enddatum.
    """
    # Erlaubt sowohl MM.YYYY als auch MM-YYYY als Eingabe
    abrechnungsmonat = abrechnungsmonat.replace("-", ".")
    monat, jahr = abrechnungsmonat.split(".")
    monat = int(monat)
    jahr = int(jahr)
    start = datetime(jahr, monat, 1)
    if monat == 12:
        end = datetime(jahr, 12, 31)
    else:
        # Letzter Tag im Monat = erster Tag im nächsten Monat - 1 Tag
        end = datetime(jahr, monat + 1, 1) - timedelta(days=1)
    # Rückgabe als Pydantic-Modell für Typsicherheit
    return MonthPeriod(start=start, end=end)