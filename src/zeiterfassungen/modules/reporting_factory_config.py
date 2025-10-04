from typing import Optional
from pydantic import BaseModel

class ReportingFactoryConfig(BaseModel):
    """
    Pydantic-Modell für die Konfiguration der ReportingFactory.

    Sorgt für Typsicherheit und Validierung der Konfigurationsdaten.
    Das Passwort für den Blattschutz wird nicht mehr im Code gespeichert,
    sondern sicher aus der Umgebung geladen.

    Attribute:
        reporting_template (str): Dateiname des Excel-Templates für die Zeiterfassungsbögen.
        sheet_password (Optional[str]): Passwort für den Blattschutz (optional, wird aus der Umgebung geladen).
    """

    reporting_template: str = "zeiterfassunsboegen.xlsx"  # Standard-Template-Dateiname
    sheet_password: Optional[str] = None  # Wird im Konstruktor aus der Umgebung geladen
