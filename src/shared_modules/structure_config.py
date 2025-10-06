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
        log_file (Optional[str]): Name der Logdatei (Standard: "wegpiraten.log").
        local_data_path (Optional[str]): Pfad zum lokalen Datenverzeichnis (Standard: "data").
    """
    prj_root: str
    shared_data_path: str = None
    output_path: str = None
    template_path: Optional[str] = None
    tmp_path: Optional[str] = None
    log_path: Optional[str] = None
    #log_file: Optional[str] = "wegpiraten.log"
    local_data_path: str = None