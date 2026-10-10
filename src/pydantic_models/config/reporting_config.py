"""Konfigurierte Meldepflicht für Accordix."""

from pydantic import BaseModel


class ReportingConfig(BaseModel):
    """Kostenträger, deren Betreuungen im Accordix-Export enthalten sind."""

    accordix_payer_ids: list[str] = ["P1000"]
