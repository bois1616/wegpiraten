from typing import Optional
from pydantic import BaseModel

class ServiceProviderConfig(BaseModel):
    name: Optional[str] = "Wegpiraten GmbH"
    street: Optional[str] = "Alpenstrasse 2"
    zip_code: Optional[str] = "3800"
    city: Optional[str] = "Interlaken"
    phone: Optional[str] = "+41 (0)76 790 67 56"
    email: Optional[str] = "info@wegpiraten.ch"
    website: Optional[str] = "www.wegpiraten.ch"
    uid: Optional[str] = "CHE-123.456.789 MWST"
    bank: Optional[str] = "Bank EKI Genossenschaft"
    iban: Optional[str] = "CH07 0839 3053 8385 3915 1"