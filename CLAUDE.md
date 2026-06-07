# CLAUDE.md — Claude Code Anweisungen

Dieses Dokument enthält Claude-spezifische Anweisungen für Claude Code (claude.ai/code).
Modell-agnostische Projektregeln stehen in [AGENTS.md](AGENTS.md).

---

## Modell

Aktuelle Claude-Modelle (Stand 2025): Sonnet 4.6 (`claude-sonnet-4-6`), Opus 4.8 (`claude-opus-4-8`), Haiku 4.5 (`claude-haiku-4-5-20251001`).
Für neue KI-Funktionen im Projekt standardmäßig `claude-sonnet-4-6` verwenden.

---

## Development Setup

```bash
uv sync --all-extras   # Dependencies installieren
direnv allow           # Automatische venv-Aktivierung
pre-commit install     # Pre-commit Hooks installieren
```

---

## CLI-Befehle

```bash
# Im src-Verzeichnis oder mit PYTHONPATH=src
python -m cli invoice 01.2025      # Rechnungen erstellen
python -m cli timesheet 2025-02    # Zeiterfassungsbögen erstellen
python -m cli import-master        # Stammdaten importieren
python -m cli import-sheets        # Zeiterfassungsbögen importieren
python -m cli validate             # Konfiguration prüfen
```

---

## Qualitätssicherung

```bash
nox                              # lint + typecheck (Standard vor Commit)
nox -s lint                      # ruff check
nox -s typecheck                 # pyright
nox -s format                    # ruff format

ruff check src/ --exclude src/unused
ruff format src/ --exclude src/unused
pyright src/
```

---

## Verhalten in Claude Code

- Keine Kommentare schreiben, außer wenn das **Warum** nicht aus dem Code ersichtlich ist
- Keine mehrzeiligen Docstring-Blöcke — maximal eine kurze Zeile
- Keine Fehlerbehandlung für Szenarien, die nicht eintreten können
- Keine Features hinzufügen, die nicht explizit angefragt wurden
- Bei destruktiven Operationen (DB-Änderungen, Dateilöschung) immer zuerst bestätigen lassen
- Vor dem Commit `nox` ausführen

---

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
        return self
```

---

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

---

## Dateipfade

```python
from pathlib import Path
from shared_modules.config import Config

config = Config()

db_path = config.get_db_path()           # richtig
template_path = config.get_template_path("vorlage.xlsx")  # richtig
db_path = Path("/home/user/data/db.sqlite3")  # NEIN — niemals hardcoded
```
