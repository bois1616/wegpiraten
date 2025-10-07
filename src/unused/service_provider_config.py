from typing import Optional
from pydantic import BaseModel

class ServiceProviderConfig(BaseModel):
    name: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    uid: Optional[str] = None
    bank: Optional[str] = None
    iban: Optional[str] = None