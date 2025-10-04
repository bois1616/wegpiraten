from typing import Optional
from pydantic import BaseModel

class StructureConfig(BaseModel):
    """
    Modell für die Struktur-Konfiguration des Projekts.

    Attribute:
        prj_root (str): Wurzelverzeichnis des Projekts.
        data_path (Optional[str]): Pfad zum Datenverzeichnis (optional).
        output_path (Optional[str]): Pfad zum Ausgabeverzeichnis (Standard: "output").
        template_path (Optional[str]): Pfad zum Template-Verzeichnis (Standard: "templates").
        tmp_path (Optional[str]): Pfad zum temporären Verzeichnis (Standard: ".tmp").
        logs (Optional[str]): Pfad zum Log-Verzeichnis relativ zu prj_root (Standard: ".logs").
        log_file (Optional[str]): Name der Logdatei (Standard: "wegpiraten.log").
    """
    prj_root: str
    data_path: Optional[str] = None
    output_path: Optional[str] = "output"
    template_path: Optional[str] = "templates"
    tmp_path: Optional[str] = ".tmp"
    logs: Optional[str] = ".logs"
    log_file: Optional[str] = "wegpiraten.log"