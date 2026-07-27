from pydantic import BaseModel


class MasterdataSourceConfig(BaseModel):
    """
    Konfigurationsmodell für die Quelle der Stammdaten-Datei auf Proton Drive.

    Proton Drive ist Ende-zu-Ende-verschlüsselt und nur über die proton-drive
    CLI erreichbar (kein Mount). Alle CLI-Aufrufe laufen unter dem zentralen
    flock, damit sie sich nicht mit den Sync-Timern um den lokalen Cache
    streiten (SQLITE_BUSY) -- siehe ~/proton-drive/Makefile.

    Attribute:
        remote_dir (str): Remote-Verzeichnis auf Proton Drive.
        file_pattern (str): Glob-Muster für Kandidaten-Dateien.
        preferred_filename (str): Bevorzugter (kanonischer) Dateiname.
        proton_cli (str): Pfad zur proton-drive CLI.
        lockfile (str): Zentrale Lockdatei für die Serialisierung der CLI.
        lock_timeout_seconds (int): Wartezeit auf den Lock in Sekunden.
    """

    remote_dir: str = "/my-files/Shared/Beatus/Wegpiraten Unterlagen"
    file_pattern: str = "wegpiraten_datenbank*.xlsx"
    preferred_filename: str = "wegpiraten_datenbank.xlsx"
    proton_cli: str = "~/.local/bin/proton-drive"
    lockfile: str = "~/proton-drive/.proton.lock"
    lock_timeout_seconds: int = 1800
