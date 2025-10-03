from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from .utils import safe_str  # Nutze zentrale Hilfsfunktion für String-Konvertierung


class Entity(BaseModel):
    """
    Basisklasse für juristische und private Personen.
    Ermöglicht die Eingabe von PLZ und Ort entweder getrennt oder als gemeinsamen String.
    Nutzt Pydantic für Validierung und Typsicherheit.
    Alle Felder werden beim Initialisieren auf str gecastet, um Typfehler durch z.B. numerische PLZ zu vermeiden.
    """
    name: str = ""
    name_2: str = ""  # Ergänzung für zweiten Namen
    street: str = ""
    zip: str = ""
    city: str = ""
    zip_city: str = ""
    key: str = ""

    @model_validator(mode="before")
    def ensure_str_fields(cls, data):
        """
        Sorgt dafür, dass alle string-Felder wirklich als str vorliegen.
        Das verhindert Validierungsfehler, wenn z.B. PLZ als int aus einer Datenquelle kommt.
        """
        for field in ["name", "name_2", "street", "zip", "city", "zip_city", "key"]:
            if field in data:
                data[field] = safe_str(data[field])
        return data

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

    @model_validator(mode="before")
    def ensure_iban_str(cls, data):
        """
        Sorgt dafür, dass IBAN immer ein String oder None ist.
        """
        if "iban" in data and data["iban"] is not None:
            data["iban"] = safe_str(data["iban"])
        return data

class PrivatePerson(Entity):
    """
    Private Person (z.B. Klient).
    Nutzt Pydantic für Typsicherheit und Validierung.
    """
    first_name: str = ""
    last_name: str = ""
    birth_date: Optional[str] = None  # Datumsformatierung erfolgt im Template
    social_security_number: str = ""  # Sozialversicherungsnummer

    @model_validator(mode="before")
    def ensure_private_str_fields(cls, data):
        """
        Sorgt dafür, dass alle string-Felder wirklich als str vorliegen.
        """
        for field in ["first_name", "last_name", "birth_date", "social_security_number"]:
            if field in data and data[field] is not None:
                data[field] = safe_str(data[field])
        return data

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

