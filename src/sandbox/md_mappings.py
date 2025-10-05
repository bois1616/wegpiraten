# Bildet die felder der Excel Ursprungstabellen auf die Felder der Pydantic-Modelle ab.
# Diese Mappings werden in import_masterdata.py verwendet.
# Die Schlüssel sind die Spaltennamen in der Excel-Tabelle, die Werte die Feldnamen

EMPLOYEE_MAPPING = {
    "PersNr": "emp_id", #key field
    # "Name": "surname",
    "Vorname": "firstname",
    "Nachname": "surname",
    "FTE": "fte",
    "Kommentar": "notes",
    # ggf. weitere Felder
}

CLIENT_MAPPING = {
    "KlientNr": "client_id", # key field
    "SozVersNr": "social_security_number",
    "Vorname": "firstname",
    "Nachname": "surname",
    "Kürzel": "short_code",
    "ZdNr": "payer_id", # foreign key
    "LbNr": "service_requester_id", # foreign key
    "Beginn": "start_date",
    "Ende": "end_date",
    "MA_ID": "employee_id", # foreign key
    "Stunden pro Monat": "allowed_hours_per_month",
    "SPF / BBT": "service_type",
    "Kommentar": "notes",
    # ggf. weitere Felder
}
PAYER_MAPPING = {
    "ZdNr": "payer_id", # key field
    "ZD_Name": "name",
    "ZD_Name2": "name2",
    "ZD_Strasse": "street",
    "ZD_PLZ": "zip",
    "ZD_Ort": "city",
    "Kommentar": "notes",
    # ggf. weitere Felder
}
SERVICE_REQUESTER_MAPPING = {
    "LBNr": "sr_key", # key field
    "Leistungsbesteller": "name",
    # ggf. weitere Felder
}