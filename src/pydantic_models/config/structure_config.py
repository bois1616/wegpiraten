from typing import Optional
from pydantic import BaseModel

class StructureConfig(BaseModel):
    """
    Modell für die Struktur-Konfiguration des Projekts.

    Attribute:
        prj_root (str): Wurzelverzeichnis des Projekts.
        shared_data_path (Optional[str]): Pfad zum gemeinsamen Datenverzeichnis.
        output_path (Optional[str]): Pfad zum Ausgabeverzeichnis (Standard: "output").
        template_path (Optional[str]): Pfad zum Template-Verzeichnis (Standard: "templates").
        tmp_path (Optional[str]): Pfad zum temporären Verzeichnis (Standard: ".tmp").
        log_path (Optional[str]): Pfad zum Log-Verzeichnis relativ zu prj_root (Standard: ".logs").
        local_data_path (Optional[str]): Pfad zum lokalen Datenverzeichnis (Standard: "data").
    """
    prj_root: str = "/home/stephan/projects/wegpiraten"
    shared_data_path: Optional[str] = "shared_data"
    output_path: Optional[str] = "output"
    template_path: Optional[str] = "templates"
    tmp_path: Optional[str] = ".tmp"
    log_path: Optional[str] = ".logs"
    local_data_path: Optional[str] = "data"