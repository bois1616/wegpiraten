from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

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

    @model_validator(mode="after")
    def sync_zip_city(self) -> "Entity":
        """
        Synchronisiert zip, city und zip_city nach der Initialisierung.
        - Wenn zip_city gesetzt ist, werden zip und city daraus extrahiert.
        - Wenn zip_city leer ist, aber zip oder city gesetzt sind, wird zip_city zusammengesetzt.
        """
        if self.zip_city:
            parts = self.zip_city.strip().split(" ", 1)
            self.zip = parts[0] if len(parts) > 0 else ""
            self.city = parts[1] if len(parts) > 1 else ""
        elif self.zip or self.city:
            self.zip_city = f"{self.zip} {self.city}".strip()
        return self

    @field_validator("name_2", mode="after")
    def empty_name_2(cls, v: str) -> str:
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
    Nutzt Pydantic für Typsicherheit und Validierung.
    """
    iban: Optional[str] = None

class PrivatePerson(Entity):
    """
    Private Person (z.B. Klient).
    Nutzt Pydantic für Typsicherheit und Validierung.
    """
    first_name: str = ""
    last_name: str = ""
    birth_date: Optional[str] = None  # Datumsformatierung erfolgt im Template
    social_security_number: str = ""  # Sozialversicherungsnummer

    @field_validator("name", mode="after")
    def set_name_if_empty(cls, v: str, info) -> str:
        """
        Setzt name automatisch, falls nicht explizit gesetzt.
        Nutzt last_name und first_name, falls name leer ist.
        """
        if not v:
            last_name = info.data.get("last_name", "")
            first_name = info.data.get("first_name", "")
            return f"{last_name}, {first_name}".strip(", ")
        return v

    def as_dict(self) -> dict:
        """
        Gibt die Felder als Dictionary zurück, inkl. Felder aus Entity.
        """
        return self.model_dump()

