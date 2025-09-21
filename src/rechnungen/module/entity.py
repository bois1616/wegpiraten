class Entity:
    def __init__(self, name, street, zip_city=None, zip=None, city=None, key=None, **kwargs):
        self.name = name
        self.street = street
        if zip_city:
            self.zip_city = zip_city
        elif zip and city:
            self.zip_city = f"{zip} {city}"
        else:
            self.zip_city = ""
        self.key = key or ""  # z.B. ZDNR, Klient-Nr., etc.

class LegalPerson(Entity):
    def __init__(self, name, street, zip_city=None, zip=None, city=None, iban=None, key=None, **kwargs):
        super().__init__(name, street, zip_city=zip_city, zip=zip, city=city, key=key, **kwargs)
        self.iban = iban

class PrivatePerson(Entity):
    def __init__(self, first_name, last_name, street, zip_city=None, zip=None, city=None, birth_date=None, key=None, **kwargs):
        name = f"{last_name}, {first_name}"
        super().__init__(name, street, zip_city=zip_city, zip=zip, city=city, key=key, **kwargs)
        self.first_name = first_name
        self.last_name = last_name
        self.birth_date = birth_date

