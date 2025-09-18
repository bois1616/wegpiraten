class Entity:
    def __init__(self, name, strasse, plz_ort, kennung=None):
        self.name = name
        self.strasse = strasse
        self.plz_ort = plz_ort
        self.kennung = kennung or "" # z.B. ZDNR, Klient-Nr., etc.

class JuristischePerson(Entity):
    def __init__(self, name, strasse, plz_ort, iban=None, kennung=None):
        super().__init__(name, strasse, plz_ort, kennung)
        self.iban = iban

class PrivatePerson(Entity):
    def __init__(self, vorname, nachname, strasse, plz_ort, geburtsdatum=None, kennung=None):
        name = f"{vorname} {nachname}"
        super().__init__(name, strasse, plz_ort, kennung)
        self.vorname = vorname
        self.nachname = nachname
        self.geburtsdatum = geburtsdatum

