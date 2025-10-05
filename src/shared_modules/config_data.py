from typing import Optional
from pydantic import BaseModel

from .expected_columns_config import ExpectedColumnsConfig
from .structure_config import StructureConfig
from .provider_config import ProviderConfig

class ConfigData(BaseModel):
    """
    Modell für die gesamte Konfiguration des Projekts.

    Attributte:
        locale (str): Gebietsschema (z.B. "de_CH").
        currency (str): Währung (z.B. "CHF").
        currency_format (str): Format für Währungsangaben.
        date_format (str): Datumsformat.
        numeric_format (str): Zahlenformat.
        expected_columns (ExpectedColumnsConfig): Erwartete Spalten als typisiertes Modell.
        structure (StructureConfig): Struktur-Teil der Konfiguration.
        db_name (Optional[str]): Name der Datenbank (optional).
        sqlite_db_name (Optional[str]): Name der SQLite-Datenbank (optional).
        db_encrypted (Optional[bool]): Gibt an, ob die DB verschlüsselt ist.
        invoice_template_name (Optional[str]): Name des Rechnungsvorlagen-Dokuments (optional).
        sheet_name (Optional[str]): Name des Sheets (optional).
        client_sheet_name (Optional[str]): Name des Klienten-Sheets (optional).
        reporting_template (Optional[str]): Name der Reporting-Vorlage (optional).
        provider (Optional[ProviderConfig]): Anbieter-Konfiguration (optional).
    """
    locale: str = "de_CH"                       # Gebietsschema
    currency: str = "CHF"                       # Währung
    currency_format: str = "¤#,##0.00"          # Format für Währungsangaben
    date_format: str = "dd.MM.yyyy"             # Datumsformat
    numeric_format: str = "#,##0.00"            # Zahlenformat
    expected_columns: ExpectedColumnsConfig     # Erwartete Spalten als typisiertes Modell
    structure: StructureConfig                  # Struktur-Teil (siehe oben)
    db_name: Optional[str] = None
    sqlite_db_name: Optional[str] = None
    db_encrypted: Optional[bool] = None
    invoice_template_name: Optional[str] = None
    sheet_name: Optional[str] = None
    client_sheet_name: Optional[str] = None
    reporting_template: Optional[str] = None
    provider: Optional[ProviderConfig] = None