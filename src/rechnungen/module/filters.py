from babel.numbers import format_currency, format_decimal
from babel.dates import format_date
from jinja2 import Environment, Undefined

def babel_currency(value, currency="CHF", locale="de_CH", currency_format=None):
    """Jinja2-Filter für Währungsformatierung mit Babel."""
    if value is None:
        return ""
    return format_currency(value, currency, format=currency_format, locale=locale)

def babel_decimal(value, locale="de_CH", numeric_format=None):
    """Jinja2-Filter für numerische Formatierung mit Babel."""
    if value is None or isinstance(value, Undefined):
        return ""
    return format_decimal(value, format=numeric_format, locale=locale)

def babel_date(value, locale="de_CH", date_format=None):
    """Jinja2-Filter für Datumsformatierung mit Babel."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%d.%m.%Y").date()
        except Exception:
            return value  # Fallback: gib den String zurück
    return format_date(value, format=date_format, locale=locale)

def register_filters(env: Environment, config: dict):
    """Registriert alle Babel-Filter im Jinja2-Environment."""
    locale = config.get("locale", "de_CH")
    currency = config.get("currency", "CHF")
    currency_format = config.get("currency_format", None)
    date_format = config.get("date_format", None)
    numeric_format = config.get("numeric_format", None)

    env.filters["currency"] = lambda v: babel_currency(v, currency, locale, currency_format)
    env.filters["decimal"] = lambda v: babel_decimal(v, locale, numeric_format)
    env.filters["date"] = lambda v: babel_date(v, locale, date_format)