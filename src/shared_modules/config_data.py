from typing import Optional, Dict
from pydantic import BaseModel


from .structure_config import StructureConfig
from .provider_config import ProviderConfig
from .mapping_entry import MappingEntry

class ConfigData(BaseModel):
    """
    Modell für die gesamte Konfiguration des Projekts.

    Attribute:
        locale (str): Gebietsschema (z.B. "de_CH").
        currency (str): Währung (z.B. "CHF").
        currency_format (str): Format für Währungsangaben.
        date_format (str): Datumsformat.
        numeric_format (str): Zahlenformat.
        structure (StructureConfig): Struktur-Teil der Konfiguration.
        db_name (Optional[str]): Name der Datenbank (optional).
        sqlite_db_name (Optional[str]): Name der SQLite-Datenbank (optional).
        db_encrypted (Optional[bool]): Gibt an, ob die DB verschlüsselt ist.
        invoice_template_name (Optional[str]): Name des Rechnungsvorlagen-Dokuments (optional).
        sheet_name (Optional[str]): Name des Sheets (optional).
        client_sheet_name (Optional[str]): Name des Klienten-Sheets (optional).
        reporting_template (Optional[str]): Name der Reporting-Vorlage (optional).
        provider (Optional[ProviderConfig]): Anbieter-Konfiguration (optional).
        table_mappings (Dict[str, Dict[str, str]]): Tabellen-Mapping (Excel-Tabelle → Entity/Zieltabelle).
        field_mappings (Dict[str, Dict[str, MappingEntry]]): Feld-Mappings für jede Entity.
    """
    locale: str = "de_CH"
    currency: str = "CHF"
    currency_format: str = "¤#,##0.00"
    date_format: str = "dd.MM.yyyy"
    numeric_format: str = "#,##0.00"
    structure: StructureConfig
    db_name: Optional[str] = None
    sqlite_db_name: Optional[str] = None
    db_encrypted: Optional[bool] = None
    invoice_template_name: Optional[str] = None
    sheet_name: Optional[str] = None
    client_sheet_name: Optional[str] = None
    reporting_template: Optional[str] = None
    provider: Optional[ProviderConfig] = None
    # Tabellen-Mapping: Excel-Tabelle → {"entity": Entity-Name, "target": Zieltabelle}
    table_mappings: Dict[str, Dict[str, str]]
    # Feld-Mappings: Entity-Name → {Excel-Spaltenname: MappingEntry}
    field_mappings: Dict[str, Dict[str, MappingEntry]]