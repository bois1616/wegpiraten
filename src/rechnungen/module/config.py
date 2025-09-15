import yaml
from pathlib import Path

class Config:
    """
    Singleton-Klasse für das Laden und Bereitstellen der Konfiguration.
    Stellt sicher, dass die Konfiguration nur einmal geladen wird und global verfügbar ist.
    """

    _instance = None  # Statische Variable für die Singleton-Instanz
    __slots__ = ("_config",)

    def __new__(cls):
        """
        Erzeugt eine neue Instanz, falls noch keine existiert.
        Singleton-Pattern: Es gibt immer nur eine Instanz dieser Klasse.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._config = None
        return cls._instance

    def load(self, config_path: Path):
        """
        Lädt die YAML-Konfiguration aus der angegebenen Datei.
        :param config_path: Pfad zur YAML-Konfigurationsdatei
        :raises ValueError: Falls kein Pfad übergeben wird oder die Datei nicht existiert.
        """
        if not config_path or not isinstance(config_path, Path):
            raise ValueError("config_path muss als pathlib.Path übergeben werden.")
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
    
    # Hinweis: Dieser Block wird nur ausgeführt, wenn das Modul direkt gestartet wird.
    if __name__ == "__main__":
        print("This is a singleton configuration module.")