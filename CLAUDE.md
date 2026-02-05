# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wegpiraten ist eine deutschsprachige CLI-Anwendung für die Verwaltung von Zeiterfassungsbögen und die Rechnungserstellung für ein Schweizer Pflegedienstleistungsunternehmen.

**Kernfunktionen:**
- Import von Stammdaten (Mitarbeiter, Klienten, Zahlungsdienstleister) aus Excel in SQLite
- Import von ausgefüllten Zeiterfassungsbögen (Leistungsdaten)
- Erstellung von Rechnungen für einen Leistungsmonat
- Erstellung von leeren Zeiterfassungsbögen für den Folgemonat

**Kein GUI** - reine CLI-Bedienung mit typer.

## Development Setup

```bash
# Dependencies installieren (mit uv)
uv sync --all-extras

# Automatische venv-Aktivierung (direnv)
direnv allow

# Pre-commit Hooks installieren
pre-commit install
```

## CLI-Befehle

```bash
# Im src-Verzeichnis oder mit PYTHONPATH=src
python -m cli invoice 01.2025           # Rechnungen erstellen
python -m cli timesheet 2025-02         # Zeiterfassungsbögen erstellen
python -m cli import-master             # Stammdaten importieren
python -m cli import-sheets             # Zeiterfassungsbögen importieren
python -m cli validate                  # Konfiguration prüfen
```

## Qualitätssicherung

```bash
# Nox-Sessions (empfohlen)
nox                    # lint + typecheck
nox -s lint            # Linting mit ruff
nox -s typecheck       # Type-Checking mit pyright
nox -s format          # Code formatieren

# Manuell
ruff check src/ --exclude src/unused
ruff format src/ --exclude src/unused
pyright src/
```

## Architecture

```
src/
├── cli.py                    # Haupteinstiegspunkt (typer)
├── shared_modules/
│   ├── config.py            # Singleton-Konfiguration
│   ├── entity.py            # Entity-Basisklassen
│   ├── month_period.py      # Monatszeitraum-Utilities
│   └── utils.py             # Hilfsfunktionen
├── pydantic_models/
│   ├── config/              # Konfigurationsmodelle
│   └── data/                # Datenmodelle
├── invoices/                # Rechnungsverarbeitung
├── time_sheets/             # Zeiterfassungsbogen-Erstellung
├── data_imports/            # Import-Module
└── unused/                  # Archivierte Module (GUI, etc.)
```

## Configuration

- **`.config/wegpiraten_config.yaml`**: Zentrale YAML-Config
- **`.env`**: Secrets (Fernet-verschlüsselt)
- Config-Zugriff immer über `Config`-Singleton

### Config-Zugriff (Korrekt)

```python
from shared_modules.config import Config

config = Config()  # Singleton mit Default-Pfad

config.structure.prj_root
config.get_db_path()
config.formatting.currency
config.service_provider.name
config.models["employee"].fields
```

**NICHT verwenden:** `config.data.xxx` (existiert nicht!)

## Key Patterns

- **Pydantic v2** für alle Modelle (`model_validator`, nicht `validator`)
- **Type Hints** für alle Funktionen
- **loguru** für Logging (nicht `print()`)
- **rich** für CLI-Output

## Language

- Code-Kommentare: Deutsch
- Locale: `de_CH`
- Währung: CHF
