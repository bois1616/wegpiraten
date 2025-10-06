from typing import Optional
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    sqlite_db_name: Optional[str] = 'Wegpiraten Datenbank.sqlite3'
    db_name: Optional[str] = 'Wegpiraten Datenbank.xlsx'
    db_encrypted: Optional[bool] = False