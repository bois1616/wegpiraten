from datetime import datetime
from babel.numbers import format_currency, format_decimal
from babel.dates import format_date
from jinja2 import Environment, Undefined
from pydantic import BaseModel
from typing import Optional, Any

class FilterConfig(BaseModel):
    """
    Pydantic-Modell für die Filter-Konfiguration.
    Sorgt für Typsicherheit und Validierung der Formatierungsoptionen.
    """
    locale: str = "de_CH"
    currency: str = "CHF"
    currency_format: Optional[str] = None
    date_format: Optional[str] = None
    numeric_format: Optional[str] = None

def babel_currency(
    value: Any,
    currency: str = "CHF",
    locale: str = "de_CH",
    currency_format: Optional[str] = None
) -> str:
    """Jinja2-Filter für Währungsformatierung mit Babel."""
    if value is None:
        return ""
    return format_currency(value, currency, format=currency_format, locale=locale)

def babel_decimal(
    value: Any,
    locale: str = "de_CH",
    numeric_format: Optional[str] = None
) -> str:
    """Jinja2-Filter für numerische Formatierung mit Babel."""
    if value is None or isinstance(value, Undefined):
        return ""
    return format_decimal(value, format=numeric_format, locale=locale)

def babel_date(
    value: Any,
    locale: str = "de_CH",
    date_format: Optional[str] = None
) -> str:
    """Jinja2-Filter für Datumsformatierung mit Babel."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%d.%m.%Y").date()
        except Exception:
            return value  # Fallback: gib den String zurück
    return format_date(value, format=date_format, locale=locale)

def register_filters(env: Environment, config: FilterConfig) -> None:
    """
    Registriert alle Babel-Filter im Jinja2-Environment.
    Erwartet ein Pydantic-Modell für die Konfiguration.
    """
    env.filters["currency"] = lambda v: babel_currency(
        v,
        config.currency,
        config.locale,
        config.currency_format
    )
    env.filters["decimal"] = lambda v: babel_decimal(
        v,
        config.locale,
        config.numeric_format
    )
    env.filters["date"] = lambda v: babel_date(
        v,
        config.locale,
        config.date_format
    )