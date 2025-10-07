from typing import Optional
from pydantic import BaseModel

class LoggingConfig(BaseModel):
    log_file: Optional[str] = "wegpiraten.log"      # Defaultwert
    log_level: Optional[str] = "INFO"               # Defaultwert
