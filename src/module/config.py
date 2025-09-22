import yaml
from pathlib import Path

class Config:
    """
    Singleton-Klasse für das Laden und Bereitstellen der Konfiguration.
    Stellt sicher, dass die Konfiguration nur einmal geladen wird und global verfügbar ist.
    """

    _instance = None  # Statische Variable für die Singleton-Instanz

    def __new__(cls):
        """
        Erzeugt eine neue Instanz, falls noch keine existiert.
        Singleton-Pattern: Es gibt immer nur eine Instanz dieser Klasse.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
        return cls._instance

    def load(self, config_path: Path):
        """
        Lädt die YAML-Konfiguration aus der angegebenen Datei.
        :param config_path: Pfad zur YAML-Konfigurationsdatei
        :raises ValueError: Falls kein Pfad übergeben wird oder die Datei nicht existiert.
        """
        if not isinstance(config_path, Path):
            raise ValueError("config_path muss ein pathlib.Path-Objekt sein.")
        if not config_path.exists():
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
        with open(config_path, "r") as f:
            self._config = yaml.safe_load(f)

    @property
    def data(self):
        """
        Gibt die geladene Konfiguration zurück.
        :raises ValueError: Falls die Konfiguration noch nicht geladen wurde.
        :return: Konfigurationsdaten als Dictionary
        """
        if self._config is None:
            raise ValueError("Config not loaded!")
        return self._config

    def get(self, key, default=None):
        """
        Allgemeiner Getter für Konfigurationswerte.
        """
        return self.data.get(key, default)

    def get_locale(self):
        """Gibt die Locale aus der Konfiguration zurück, Fallback: de_CH"""
        return self.get("locale", "de_CH")

    def get_currency(self):
        """Gibt das Währungssymbol aus der Konfiguration zurück, Fallback: CHF"""
        return self.get("currency", "CHF")

    def get_currency_format(self):
        """Gibt das Währungsformat für Babel zurück, Fallback: ¤#,##0.00"""
        return self.get("currency_format", "¤#,##0.00")

    def get_date_format(self):
        """Gibt das Datumsformat für Babel zurück, Fallback: dd.MM.yyyy"""
        return self.get("date_format", "dd.MM.yyyy")

    def get_numeric_format(self):
        """Gibt das numerische Format für Babel zurück, Fallback: #,##0.00"""
        return self.get("numeric_format", "#,##0.00")

    def get_expected_columns(self):
        """Gibt die erwarteten Spalten aus der Konfiguration zurück."""
        return self.get("expected_columns", {})

if __name__ == "__main__":
    print("This is a singleton configuration module.")
