# AGENTS.md - Leitlinie für KI-Agenten (Codex, Claude, etc.)

Dieses Dokument beschreibt die Konventionen und Regeln für KI-Agenten, die an diesem Projekt arbeiten.

## Projektübersicht

**Wegpiraten** ist eine CLI-Anwendung für:

- Import von Stammdaten (Mitarbeiter, Klienten, Zahlungsdienstleister) aus Excel in SQLite
- Import von Zeiterfassungsbögen (Leistungsdaten)
- Erstellung von Rechnungen für einen Leistungsmonat
- Erstellung von leeren Zeiterfassungsbögen für den Folgemonat

**Sprache**: Deutsch (Code-Kommentare, Dokumentation, Benutzeroberfläche)
**Locale**: de_CH (Schweizerdeutsch), Währung: CHF

---

## Betriebsworkflow (Monatlicher Batch-Betrieb)

Der Regelbetrieb erfolgt in festen Zyklen:

### Initial

- Import der Stammdaten aus Excel in die SQLite-Datenbank

### Monatlicher Ablauf

1. Manuelle Anpassung der Stammdaten in der DB (falls erforderlich)
2. Import der Timesheets aus einem Verzeichnis
3. Batch-Erstellung der Rechnungen (DOCX + PDF)
4. Manueller Versand per E-Mail
5. Archivierung aller Daten (ZIP) und Leeren der Verzeichnisse
6. Generierung neuer leerer Timesheets aus der DB
7. Verteilung der Timesheets

### Korrekturen

- Notwendige Rechnungskorrekturen erfolgen manuell in DOCX
- Korrekturen müssen im Archiv dokumentiert werden

---

## Betriebssicherung

- Vor manuellen DB-Änderungen ist ein Backup zu erstellen
- Vor jedem Import ist ein DB-Snapshot zu sichern
- Nach Abschluss eines Monats ist ein Abschluss-Backup zu erstellen
- Archivnamen sind monatsbezogen zu normieren

---

## Projektprioritäten (Verbindlich)

Die folgenden Prioritäten gelten strikt:

1. Robustheit vor Performance
2. Korrektheit vor Komfort
3. Nachvollziehbarkeit vor Automatisierung

Automatisierung ist erwünscht, darf aber die Nachvollziehbarkeit nicht reduzieren.

---

## Review-Regel

Ein Patch ist nicht akzeptabel, wenn er gegen die Projektprioritäten verstößt.

Insbesondere unzulässig sind:

- Vereinfachungen mit fachlichen Risiken
- Optimierungen mit Verlust an Transparenz
- Automatisierungen ohne ausreichendes Logging

---

## Betriebsstabilität (Übergangsbetrieb)

Dieses Projekt dient als temporäre Übergangslösung.

Daher gelten folgende Stabilitätsregeln:

### Konfiguration

- Struktur gilt als eingefroren
- Keine Umbenennungen oder impliziten Änderungen

### Datenbank

- Keine destruktiven Schemaänderungen
- Nur additive Erweiterungen

### Rechnungsoutput

- Layout und Berechnungslogik gelten als stabil
- Änderungen nur bei fachlicher Notwendigkeit

### Importformate

- Bestehende Formate müssen weiterhin funktionieren
- Erweiterungen nur additiv

---

## Projektcharakter

Dieses System ist als Übergangslösung konzipiert.

Ziel ist:

- Sicherer Betrieb
- Korrekte Abrechnung
- Begrenzte Wartung

Nicht-Ziel ist:

- Langfristige Architektur
- Skalierung
- Funktionsausbau

## Architektur

```md
src/
├── cli.py                    # Haupteinstiegspunkt (typer)
├── shared_modules/
│   ├── config.py            # Singleton-Konfiguration (YAML + Pydantic)
│   ├── entity.py            # Entity-Basisklassen (LegalPerson, PrivatePerson)
│   ├── month_period.py      # Monatszeitraum-Utilities
│   └── utils.py             # Hilfsfunktionen
├── pydantic_models/
│   ├── config/              # Konfigurationsmodelle
│   └── data/                # Datenmodelle
├── invoices/                # Rechnungsverarbeitung
├── time_sheets/             # Zeiterfassungsbogen-Erstellung
├── data_imports/            # Stammdaten- und Zeiterfassungs-Import
└── unused/                  # Archivierte/ungenutzte Module
```

## Coding-Konventionen

### Python

- Python 3.13+
- Type Hints für alle Funktionen und Methoden
- Pydantic v2 für Datenvalidierung
- Docstrings auf Deutsch

### Qualitätssicherung

```bash
nox -s lint       # ruff check
nox -s typecheck  # pyright
nox -s format     # ruff format
```

### Konfiguration

- Zentrale YAML-Config: `.config/wegpiraten_config.yaml`
- Secrets in `.env` (Fernet-verschlüsselt)
- Config-Zugriff immer über `Config`-Singleton

## Wichtige Regeln

### DO (Machen)

1. **Type Hints verwenden** - Alle Funktionen typisieren
2. **Pydantic für Validierung** - Keine manuellen dict-Zugriffe ohne Validierung
3. **Config-Singleton nutzen** - `Config()` oder `Config(path)`
4. **Deutsche Kommentare** - Docstrings und Kommentare auf Deutsch
5. **CLI über typer** - Neue Befehle in `cli.py` hinzufügen
6. **Tests mit nox** - Vor Commit `nox` ausführen

### DON'T (Vermeiden)

1. **Keine `config.data.xxx`** - Nutze `config.structure`, `config.formatting`, etc.
2. **Keine Flask-Imports** - GUI ist deaktiviert
3. **Keine hardcoded Pfade** - Immer über Config
4. **Keine print()** - Nutze `loguru.logger` oder `rich.console`
5. **Keine Pydantic v1 Syntax** - Nutze `model_validator`, nicht `validator`

## Config-Zugriff (Korrekt)

```python
from shared_modules.config import Config

config = Config()  # Singleton mit Default-Pfad

# Struktur
config.structure.prj_root
config.get_db_path()
config.get_template_path("vorlage.xlsx")
config.get_output_path()

# Formatierung
config.formatting.locale
config.formatting.currency
config.get_currency()

# Templates
config.templates.invoice_template_name
config.templates.time_sheet_template

# Service Provider
config.service_provider.name
config.service_provider.iban

# Entity-Modelle
config.models["employee"].fields
config.models["client"].fields
config.get_expected_columns()
```

## Neue Features hinzufügen

### Neuer CLI-Befehl

```python
# In src/cli.py
@app.command("neuer-befehl")
def neuer_befehl(
    param: str = typer.Argument(..., help="Beschreibung"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Beschreibung des Befehls."""
    config = get_config(config_path)
    # Implementierung
```

### Neues Pydantic-Modell

```python
# In src/pydantic_models/data/neues_modell.py
from pydantic import BaseModel, model_validator

class NeuesModell(BaseModel):
    """Beschreibung auf Deutsch."""
    feld: str
    optional_feld: Optional[int] = None

    @model_validator(mode="after")
    def validate_something(self) -> "NeuesModell":
        # Validierungslogik
        return self
```

## Fehlerbehandlung

```python
from loguru import logger

try:
    # Operation
except ValueError as e:
    logger.error(f"Validierungsfehler: {e}")
    raise
except FileNotFoundError as e:
    logger.error(f"Datei nicht gefunden: {e}")
    raise
```

## Dateipfade

```python
from pathlib import Path
from shared_modules.config import Config

config = Config()

# Richtig
db_path = config.get_db_path()
template_path = config.get_template_path("vorlage.xlsx")

# Falsch - niemals hardcoded
db_path = Path("/home/user/data/db.sqlite3")  # NEIN!
```

## Bekannte Probleme (TODO)

1. `import_masterdata.py` verwendet noch `config.data.xxx` - muss migriert werden
2. `document_utils.py` hat Type-Fehler mit pandas iloc
3. `time_sheet_factory.py` hat Optional-Zugriffe ohne None-Check

## Kontakt

Bei Fragen zur Architektur: Siehe `CLAUDE.md` und `konzept.md`
