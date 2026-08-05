# AGENTS.md — Leitlinie für KI-Agenten

Dieses Dokument beschreibt Konventionen und Regeln für alle KI-Agenten (Claude, Codex, Gemini, etc.), die an diesem Projekt arbeiten. Es ist modell-agnostisch.

Claude-spezifische Anweisungen stehen in [CLAUDE.md](CLAUDE.md).

---

## Projektübersicht

**Wegpiraten** ist eine deutschsprachige CLI-Anwendung für ein Schweizer Pflegedienstleistungsunternehmen.

Kernfunktionen:

- Import von Stammdaten (Mitarbeiter, Klienten, Zahlungsdienstleister) aus Excel in SQLite
- Import von ausgefüllten Zeiterfassungsbögen (Leistungsdaten)
- Erstellung von Rechnungen für einen Leistungsmonat (DOCX + PDF)
- Erstellung von leeren Zeiterfassungsbögen für den Folgemonat

**Kein GUI** — reine CLI-Bedienung mit typer.
**Sprache**: Deutsch (Kommentare, Dokumentation, Benutzeroberfläche)
**Locale**: de_CH, Währung: CHF

---

## Projektprioritäten (verbindlich)

1. Robustheit vor Performance
2. Korrektheit vor Komfort
3. Nachvollziehbarkeit vor Automatisierung

Automatisierung ist erwünscht, darf aber die Nachvollziehbarkeit nicht reduzieren.

---

## Projektcharakter

Dieses System ist als Übergangslösung konzipiert. Ziel:

- Sicherer Betrieb
- Korrekte Abrechnung
- Begrenzte Wartung

Nicht-Ziel: langfristige Architektur, Skalierung, Funktionsausbau.

---

## Betriebsworkflow (monatlicher Batch-Betrieb)

### Initial

- Import der Stammdaten aus Excel in die SQLite-Datenbank

### Monatlicher Ablauf

0. Stammdaten bei Änderungen von Proton Drive holen (`fetch-master` bzw. `import-master --fetch`; Zugriff via proton-drive CLI unter zentralem flock)
1. Manuelle Anpassung der Stammdaten in der DB (falls erforderlich)
2. Import der Timesheets aus einem Verzeichnis (Holung von Proton Drive: `fetch-timesheets <relativer Remote-Pfad>`, Verzeichnis-Cache analog MONTH)
3. Batch-Erstellung der Rechnungen (DOCX + PDF)
4. Manueller Versand per E-Mail
5. Archivierung aller Daten (ZIP) und Leeren der Verzeichnisse
6. Generierung neuer leerer Timesheets aus der DB
7. Verteilung der Timesheets

### Korrekturen

- Rechnungskorrekturen erfolgen manuell in DOCX
- Korrekturen müssen im Archiv dokumentiert werden

---

## Betriebssicherung

- Die SQLite-DB ist ein abgeleitetes Artefakt: Sie wird routinemässig verworfen
  und aus Stammdaten (`import-master`) und Timesheets (`import-sheets`) neu
  erstellt. Ältere Leistungsdaten liegen in den Monatsarchiven (ZIP).
- Vor manuellen DB-Änderungen ist ein Backup zu erstellen
- Vor jedem Import ist ein DB-Snapshot zu sichern
- Nach Abschluss eines Monats ist ein Abschluss-Backup zu erstellen
- Archivnamen sind monatsbezogen zu normieren

---

## Architektur

```text
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

---

## Coding-Konventionen

### Python

- Python 3.13+
- Type Hints für alle Funktionen und Methoden
- Pydantic v2 für Datenvalidierung (`model_validator`, nicht `validator`)
- Docstrings auf Deutsch
- Logging mit `loguru` (kein `print()`)
- CLI-Output mit `rich`

### Qualitätssicherung

```bash
nox              # lint + typecheck (empfohlen)
nox -s lint      # ruff check
nox -s typecheck # pyright
nox -s format    # ruff format
```

### Konfiguration

- Zentrale YAML-Config: `.config/wegpiraten_config.yaml`
- Secrets in `.env` (Fernet-verschlüsselt)
- Config-Zugriff immer über `Config`-Singleton

---

## Wichtige Regeln

### DO

1. Type Hints für alle Funktionen
2. Pydantic v2 für Validierung — keine manuellen dict-Zugriffe ohne Validierung
3. Config-Singleton nutzen: `Config()` oder `Config(path)`
4. Kommentare auf Deutsch
5. Neue CLI-Befehle in `cli.py` über typer
6. Vor Commit `nox` ausführen

### DON'T

1. Kein `config.data.xxx` — nutze `config.structure`, `config.formatting`, etc.
2. Keine Flask-Imports (GUI ist deaktiviert)
3. Keine hardcoded Pfade — immer über Config
4. Kein `print()` — nutze `loguru.logger` oder `rich.console`
5. Keine Pydantic v1 Syntax

---

## Config-Zugriff (korrekt)

```python
from shared_modules.config import Config

config = Config()

config.structure.prj_root
config.get_db_path()
config.get_template_path("vorlage.xlsx")
config.get_output_path()
config.formatting.locale
config.formatting.currency
config.get_currency()
config.templates.invoice_template_name
config.templates.time_sheet_template
config.service_provider.name
config.service_provider.iban
config.masterdata_source.remote_dir
config.models["employee"].fields
config.models["client"].fields
config.get_expected_columns()
```

---

## Betriebsstabilität

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

## Review-Regel

Ein Patch ist nicht akzeptabel, wenn er gegen die Projektprioritäten verstößt.

Unzulässig sind insbesondere:

- Vereinfachungen mit fachlichen Risiken
- Optimierungen mit Verlust an Transparenz
- Automatisierungen ohne ausreichendes Logging
