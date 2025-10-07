from typing import Optional
from pydantic import BaseModel

class FormattingConfig(BaseModel):
    locale: Optional[str] = "de_CH"
    currency: Optional[str] = "CHF"
    currency_format: Optional[str] = "#,##0.00 ¤"
    date_format: Optional[str] = "dd.MM.yyyy"
    numeric_format: Optional[str] = "#,##0.00"