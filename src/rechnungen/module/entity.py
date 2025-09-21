from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Entity:
    """
    Basisklasse für juristische und private Personen.
    Ermöglicht die Eingabe von PLZ und Ort entweder getrennt oder als gemeinsamen String.
    """
    name: str = ""
    street: str = ""
    zip: str = ""
    city: str = ""
    zip_city: str = ""
    key: str = ""

    def __post_init__(self):
        # Falls zip_city gesetzt ist, zip und city daraus ableiten
        if self.zip_city and (not self.zip or not self.city):
            parts = self.zip_city.strip().split(" ", 1)
            if len(parts) == 2:
                self.zip, self.city = parts
            elif len(parts) == 1:
                self.zip = parts[0]
                self.city = ""

    def as_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

@dataclass
class LegalPerson(Entity):
    """
    Juristische Person (z.B. Zahlungsdienstleister).
    """
    iban: Optional[str] = None

@dataclass
class PrivatePerson(Entity):
    """
    Private Person (z.B. Klient).
    """
    first_name: str = ""
    last_name: str = ""
    birth_date: Optional[str] = None  # Datumsformatierung erfolgt im Template

    def __post_init__(self):
        super().__post_init__()
        # Setze name automatisch, falls nicht explizit gesetzt
        if not self.name:
            self.name = f"{self.last_name}, {self.first_name}"

    def as_dict(self):
        base = super().as_dict()
        base.update({
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_date": self.birth_date,
        })
        return base

