from pydantic import BaseModel
from typing import Optional

class Employee(BaseModel):
    emp_id: str
    first_name: str
    last_name: str
    fte: Optional[float]
    notes: Optional[str]
    # ...weitere Felder...

class Payer(BaseModel):
    payer_id: str
    name: str
    name2: Optional[str]
    street: Optional[str]
    zip_code: Optional[str]
    city: Optional[str]
    notes: Optional[str]
    # ...weitere Felder...

class ServiceRequester(BaseModel):
    service_requester_id: str
    name: str
    # ...weitere Felder...

class Client(BaseModel):
    client_id: str
    social_security_number: Optional[str]
    first_name: str
    last_name: str
    short_code: Optional[str]  # oder "short_code", je nach Mapping
    payer_id: Optional[str]  # Fremdschlüssel auf Payer
    service_requester_id: Optional[str]  # Fremdschlüssel auf ServiceRequester
    start_date: Optional[str]
    end_date: Optional[str]
    employee_id: Optional[str]  # Fremdschlüssel auf Employee
    allowed_hours_per_month: Optional[float]
    service_type: Optional[str]  # z.B. "SPF" oder "BBT"
    notes: Optional[str]
    # ...weitere Felder...
