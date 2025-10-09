from pydantic import BaseModel


class HeaderCells(BaseModel):
    """
    Zelladressen im Excel-Template für die Kopfwerte.
    Diese Adressen müssen mit ReportingFactory.create_reporting_sheet übereinstimmen.
    Relevant sind hier nur die Felder G5 (emp_id) und G8 (client_id) als Schlüssel.
    Alle anderen Felder sind informativ oder optional.
    """
    employee_name: str = "C5"           # rein informativ
    emp_id: str = "G5"                 # Schlüssel
    reporting_month: str = "C6"             # Datum (Excel-Date), i. d. R. pro Datei gleich
    allowed_hours_per_month: str = "C7"     # informativ
    service_type: str = "G7"                # Schlüssel/Festwert
    short_code: str = "C8"                  # informativ
    client_id: str = "G8"                   # Schlüssel

    @classmethod
    def from_config(cls, cfg) -> "HeaderCells":
        return cls(
            employee_name=cfg.employee_name,
            emp_id=cfg.emp_id,
            reporting_month=cfg.reporting_month,
            allowed_hours_per_month=cfg.allowed_hours_per_month,
            service_type=cfg.service_type,
            short_code=cfg.short_code,
            client_id=cfg.client_id,
        )