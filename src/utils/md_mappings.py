# Bildet die felder der Excel Ursprungstabellen auf die Felder der Pydantic-Modelle ab.
# Diese Mappings werden in import_masterdata.py verwendet.
# Die Schlüssel sind die Spaltennamen in der Excel-Tabelle, die Werte die Feldnamen

EMPLOYEE_MAPPING = {
    "PersNr": "PersNr", #key field
    "Name": "Name",
    "Vorname": "Vorname",
    "Nachname": "Nachname",
    "FTE": "FTE",
    "Kommentar": "Kommentar",
    # ggf. weitere Felder
}

CLIENT_MAPPING = {
    "KlientNr": "KlientNr", # key field
    "Vorname": "Vorname",
    "Nachname": "Nachname",
    "Kürzel": "Kuerzel",
    "Zahlungsdienstleister": "payer_id",  # Mapping von Ursprungsfeld auf FK
    "Leistungsbesteller": "service_requester_id",
    "Betreuer": "betreuer",
    "Stunden pro Monat": "Stunden_pro_monat",
    "Betreuungstyp": "Betreuungstyp",
    "Kommentar": "Kommentar",
    # ggf. weitere Felder
}
PAYER_MAPPING = {
    "ZdNr": "ZdNr", # key field
    "Name": "Name",
    "Name2": "Name2",
    "Strasse": "Strasse",
    "PLZ": "PLZ",
    "Ort": "Ort",
    "Kommentar": "Kommentar",
    # ggf. weitere Felder
}
SERVICE_REQUESTER_MAPPING = {
    "LBNr": "LBNr", # key field
    "Name": "Name",
    # ggf. weitere Felder
}