from typing import Optional
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """
    Konfigurationsmodell für Datenbank-Einstellungen.

    Attribute:
        sqlite_db_name (Optional[str]): Name der SQLite-Datenbankdatei.
        db_name (Optional[str]): Name der Excel-Datenbankdatei.
        db_encrypted (Optional[bool]): Gibt an, ob die Datenbank verschlüsselt ist.
    """
    sqlite_db_name: Optional[str] = 'Wegpiraten Datenbank.sqlite3'
    db_name: Optional[str] = 'Wegpiraten Datenbank.xlsx'
    db_encrypted: Optional[bool] = False