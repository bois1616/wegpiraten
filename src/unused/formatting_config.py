from typing import Optional
from pydantic import BaseModel

class FormattingConfig(BaseModel):
    locale: Optional[str] = None
    currency: Optional[str] = None
    currency_format: Optional[str] = None
    date_format: Optional[str] = None
    numeric_format: Optional[str] = None