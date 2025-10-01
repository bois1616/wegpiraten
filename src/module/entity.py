from typing import Optional
from pydantic import BaseModel, field_validator

class Entity(BaseModel):
    """
    Basisklasse für juristische und private Personen.
    Ermöglicht die Eingabe von PLZ und Ort entweder getrennt oder als gemeinsamen String.
    Nutzt Pydantic für Validierung und Typsicherheit.
    """
    name: str = ""
    name_2: str = ""  # Ergänzung für zweiten Namen
    street: str = ""
    zip: str = ""
    city: str = ""
    zip_city: str = ""
    key: str = ""

    @field_validator("zip_city", mode="after")
    def split_zip_city(cls, v, values):
        """
        Validiert und setzt zip und city anhand von zip_city, falls vorhanden.
        """
        if v:
            parts = v.strip().split(" ", 1)
            if len(parts) == 2:
                values["zip"] = parts[0]
                values["city"] = parts[1]
            elif len(parts) == 1:
                values["zip"] = parts[0]
                values["city"] = ""
        else:
            # Falls zip_city leer ist, aus zip und city zusammensetzen
            zip_val = values.get("zip", "")
            city_val = values.get("city", "")
            values["zip_city"] = f"{zip_val} {city_val}".strip()
        return v

    @field_validator("name_2", mode="after")
    def empty_name_2(cls, v):
        """
        Setzt name_2 auf "" falls "(leer)" eingetragen ist.
        """
        return "" if v == "(leer)" else v

    def as_dict(self) -> dict:
        """
        Gibt die Felder als Dictionary zurück.
        """
        return self.model_dump()

class LegalPerson(Entity):
    """
    Juristische Person (z.B. Zahlungsdienstleister).
    """
    iban: Optional[str] = None

class PrivatePerson(Entity):
    """
    Private Person (z.B. Klient).
    """
    first_name: str = ""
    last_name: str = ""
    birth_date: Optional[str] = None  # Datumsformatierung erfolgt im Template
    social_security_number: str = ""  # Sozialversicherungsnummer

    @field_validator("name", mode="after")
    def set_name_if_empty(cls, v, values):
        """
        Setzt name automatisch, falls nicht explizit gesetzt.
        """
        if not v:
            last_name = values.get("last_name", "")
            first_name = values.get("first_name", "")
            return f"{last_name}, {first_name}".strip(", ")
        return v

    def as_dict(self) -> dict:
        """
        Gibt die Felder als Dictionary zurück, inkl. Felder aus Entity.
        """
        return self.model_dump()

