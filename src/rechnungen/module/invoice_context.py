from datetime import datetime, timedelta
import locale

class InvoiceContext:
    def __init__(
        self,
        invoice_id: str,
        invoice_date: datetime,
        start_inv_period: datetime = None,
        end_inv_period: datetime = None,
        inv_month: str = None,
        payer: LegalPerson = None,
        service_provider: LegalPerson = None,
        client: PrivatePerson = None,
        positionen: list = None,
        payment_part_img=None,
        config: Config=None,
        **kwargs
    ):
        self.invoice_id = invoice_id
        self._invoice_date = invoice_date
        self._start_inv_period = start_inv_period
        self._end_inv_period = end_inv_period
        self.inv_month = inv_month
        self.payer = payer
        self.service_provider = service_provider
        self.client = client
        self.details_table = positionen or []
        self.payment_part_img = payment_part_img
        self.config: Config = config

        # Flexible Initialisierung für Abrechnungsmonat und Zeitraum
        if inv_month:
            # inv_month im Format "MM.YYYY"
            try:
                month_dt = datetime.strptime(inv_month, "%m.%Y")
                self._start_inv_period = month_dt.replace(day=1)
                if month_dt.month == 12:
                    next_month = month_dt.replace(year=month_dt.year + 1, month=1, day=1)
                else:
                    next_month = month_dt.replace(month=month_dt.month + 1, day=1)
                self._end_inv_period = next_month - timedelta(days=1)
                self.inv_month = inv_month
            except Exception:
                self._start_inv_period = None
                self._end_inv_period = None
                self.inv_month = inv_month
        elif start_inv_period and end_inv_period:
            self._start_inv_period = start_inv_period
            self._end_inv_period = end_inv_period
            self.inv_month = start_inv_period.strftime("%m.%Y")

        # Automatische Ergänzung für numerische Felder
        for k, v in kwargs.items():
            setattr(self, k, v)
            if isinstance(v, (int, float)):
                setattr(self, f"{k}_2f", f"{v:.2f}")

    def __setattr__(self, name, value):
        config = getattr(self, "config", None)
        config_spec = None
        locale_str = "de_CH.UTF-8"  # Default Locale

        # Locale aus Config holen, falls vorhanden
        if config and hasattr(config, "data"):
            locale_str = config.data.get("locale", locale_str)
            # Suche Feldspezifikation in allen relevanten Bereichen
            all_fields = {}
            for section in ["general", "payer", "client"]:
                for col in config.data.get("expected_columns", {}).get(section, []):
                    all_fields[col["name"]] = col
            config_spec = all_fields.get(name, None)

        # Währungsformatierung mit Locale aus Config oder Fallback
        def format_currency(val, symbol="CHF"):
            try:
                locale.setlocale(locale.LC_ALL, locale_str)
            except locale.Error:
                locale.setlocale(locale.LC_ALL, "de_CH.UTF-8")
            return f"{locale.format_string('%.2f', val, grouping=True)} {symbol}"

        # Falls eine Spezifikation existiert, berücksichtige sie
        if config_spec:
            if config_spec.get("type") == "currency":
                symbol = config_spec.get("currency", "CHF")
                if isinstance(value, (int, float)):
                    formatted = format_currency(value, symbol)
                    super().__setattr__(f"{name}_2f", formatted)
            elif config_spec.get("type") == "date":
                date_format = config_spec.get("format", "%d.%m.%Y")
                if isinstance(value, datetime):
                    value = value.strftime(date_format)
            elif config_spec.get("type") == "numeric" and "decimals" in config_spec:
                if isinstance(value, (int, float)):
                    decimals = config_spec["decimals"]
                    super().__setattr__(f"{name}_2f", f"{value:.{decimals}f}")
        else:
            # Fallback für Währungsfelder anhand des Namens
            if isinstance(value, (int, float)) and not name.endswith("_2f"):
                if any(kw in name.lower() for kw in ["kosten", "betrag", "preis", "summe_kosten"]):
                    formatted = format_currency(value)
                    super().__setattr__(f"{name}_2f", formatted)
                else:
                    super().__setattr__(f"{name}_2f", f"{value:.2f}")

        super().__setattr__(name, value)

    def __getattribute__(self, name):
        value = super().__getattribute__(name)
        # Automatische Formatierung für Datumsfelder (alle mit 'datum', 'date', 'period' im Namen)
        if isinstance(value, datetime) and (
            "datum" in name.lower() or "date" in name.lower() or "period" in name.lower()
        ):
            return value.strftime("%d.%m.%Y")
        return value

    def as_dict(self):
        """Gibt alle Felder als Dictionary zurück (für Templates etc.)."""
        result = self.__dict__.copy()
        # Optional: Entitäten als dict ausgeben
        for key in ["payer", "service_provider", "client"]:
            obj = result.get(key)
            if obj and hasattr(obj, "__dict__"):
                result[key] = obj.__dict__
        # Datumsfelder als String ausgeben
        for k, v in result.items():
            if isinstance(v, datetime):
                result[k] = v.strftime("%d.%m.%Y")
        return result