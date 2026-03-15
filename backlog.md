# Backlog Wegpiraten CLI

Stand 2026-03-14: Nachträglich aus Git-Historie rekonstruiert.

## P0 Must

- [x] [P0] [Architektur] CLI-only Entry-Point mit typer. Hinweis: `src/cli.py` mit typer; GUI/Flask nach `src/unused/` verschoben.
- [x] [P0] [Import] Stammdaten (Mitarbeiter, Klienten, Zahlungsdienstleister) aus Excel in SQLite importieren. Hinweis: `import_masterdata.py` vollständig umgesetzt inkl. FK-Diagnostik.
- [x] [P0] [Import] Zeiterfassungsbögen batch-weise einlesen und in SQLite speichern. Hinweis: `batch_import_timesheets.py` mit Datumsprüfung, Nullwert-Filter und Fehlerprotokoll.
- [x] [P0] [Rechnung] Rechnungserstellung als DOCX + PDF für einen Abrechnungsmonat. Hinweis: `invoice_batch.py` + `invoice_factory.py` + `invoice_processor.py`; Jinja2-Template + docxtpl.
- [x] [P0] [Rechnung] SPC-konformer Einzahlungsschein je Rechnung. Hinweis: SPC/QR-Code korrekt formatiert; Tenant-IBAN und -Anschrift klientenspezifisch gesetzt.
- [x] [P0] [Zeiterfassung] Leere Zeiterfassungsbögen für Folgemonat erzeugen. Hinweis: `time_sheet_factory.py` + `time_sheet_batch_processor.py`; Template-basiert mit openpyxl.
- [x] [P0] [Config] Zentrale YAML-Konfiguration + Singleton `Config`-Klasse. Hinweis: `.config/wegpiraten_config.yaml`; Zugriff ausschliesslich über `Config()`-Singleton.
- [x] [P0] [QA] Pyright-Fehlerfreiheit (strikte Typprüfung). Hinweis: 60+ Pyright-Fehler behoben; `pyrightconfig.json` + `noxfile.py` eingerichtet.

## P1 Should

- [x] [P1] [Rechnung] Rechnungsnummer-Konvention einheitlich (z.B. 2026-02-C1010). Hinweis: Trenner `_` → `-` in `invoice_factory.py`.
- [x] [P1] [Rechnung] Gruppierung nach Zahlungsdienstleister; Sammel-PDF je ZD. Hinweis: `invoice_processor.py`; PDFs zusammengefasst per ZD.
- [x] [P1] [Rechnung] Rechnungsübersicht als Excel (Soll/Ist je Fallkategorie). Hinweis: `document_utils.py`; Spalten Zahlungsträger, Klient, Büro + Max/Ist-Spalten mit bedingter Formatierung.
- [x] [P1] [Rechnung] Rechnungen mit Zeitsumme 0 oder Betrag 0 überspringen. Hinweis: `invoice_processor.py`; Guard vor Positionserstellung.
- [x] [P1] [Rechnung] Rechnungspositionen tagesweise aggregieren (mehrere Einsätze = eine Position). Hinweis: `groupby`-Summe in `invoice_processor.py` vor Positionserstellung.
- [x] [P1] [Rechnung] CLIENT-Filter für selektiven Rechnungslauf. Hinweis: `make invoices CLIENT=C1017,C1038`; `src/cli.py` + Makefile.
- [x] [P1] [Rechnung] Kostenloses Einführungsgespräch (15 min) bei Privatleistungen im Startmonat ausweisen. Hinweis: `invoice_processor.py`; `c.start_date` im SQL ergänzt; Intro-Splitting in der date_groups-Schleife; `is_intro`-Flag + `Bezeichnung`-Feld in Positions-Dict; Null-Kosten-Guard für Startmonat deaktiviert. `rechnungsvorlage.docx`: Datumszelle zeigt bei Intro-Positionen `item.Bezeichnung` statt `item.Leistungsdatum|date`.

  **Fachliche Regel:**
  - Gilt wenn `service_type_code == "ST99"` UND Abrechnungsmonat = Monat aus `clients.start_date`
  - 15 min werden von `direct_time` (chronologisch am ersten Tag mit Direktzeit) als Gratis-Position ausgewiesen
  - Verbleibende Minuten werden normal berechnet
  - Bei < 15 min total: gesamte Zeit kostenlos; Rechnung wird trotzdem ausgestellt (Ausnahme von der sonst geltenden Betrag-0-Filterung)
  - Konstanten: `_PRIVATE_SERVICE_TYPE_CODE = "ST99"`, `_INTRO_FREE_MINUTES = 15`
  - Template-Ausdruck: `{{item.Leistungsdatum|date if not item.is_intro else item.Bezeichnung}}`

- [x] [P1] [Import] Tolerante Datumsergänzung im Timesheet-Import: Texteingaben wie «12», «12.», «12.3», «12.3.» werden zusammen mit dem Abrechnungsmonat zu vollständigen Daten ergänzt. Nicht erkennbare Werte erzeugen Logeintrag, stoppen den Import nicht. Hinweis: `_parse_partial_service_date` in `batch_import_timesheets.py` erweitert; zweites Pattern `_DAY_ONLY_PATTERN` für bare Tag-Eingaben.
- [x] [P1] [Import] Doubletten beim mehrfachen Timesheet-Import verhindern (Upsert). Hinweis: ursprünglich Hash-basierte Dedup; später vereinfacht auf direkten Import ohne Dedup (jede Zeile eigenständig).
- [x] [P1] [Import] Datum-Validierung beim Timesheet-Import (fehlendes/fehlerhaftes Jahr; Datum ausserhalb Monat). Hinweis: Warnung + Fehlerprotokoll in `batch_import_timesheets.py`.
- [x] [P1] [Import] Abrechnungsmonat aus Bogen-Header (C6) gegen CLI-Monat prüfen. Hinweis: Warnung wenn Monat abweicht.
- [x] [P1] [Import] FK-Diagnostik bei IntegrityError (konkrete Verletzungen ausgeben). Hinweis: `import_masterdata.py`; zeigt betroffene Datensätze.
- [x] [P1] [Zeiterfassung] Budget-Felder je Klient (Fahrtzeit, Direkter Fallkontakt, Indirekte Fallbearbeitung). Hinweis: `allowed_travel_time`, `allowed_direct_effort`, `allowed_indirect_effort` in Integer-Minuten; Stammdaten-Import mit `multiply_by: 60`.
- [x] [P1] [Zeiterfassung] Zeiterfassung in Integer-Minuten statt Dezimalstunden. Hinweis: `service_data.travel_time/direct_time/indirect_time` als INTEGER; Umrechnung bei Import.
- [x] [P1] [Zeiterfassung] Budget-Tracking je Spalte im Zeiterfassungsbogen-Template. Hinweis: Obergrenze-Zeile (Row 30) + Differenz-Zeile (Row 31) mit bedingter Formatierung (Grün/Gelb/Rot).
- [x] [P1] [Zeiterfassung] Validierungslogik im Template. Hinweis: C32 Warnformel (Budget überzogen / indirekte Zeiten > 50% direkt); E29 bedingte Formatierung hellrot.
- [x] [P1] [Report] Arbeitszeitprotokoll als Excel-Export. Hinweis: `src/reports/arbeitszeit_report.py`; Detail-Sheet + Zusammenfassung je Mitarbeiter; CLI `report`; `make report`.
- [x] [P1] [Tooling] Makefile mit Targets für alle CLI-Befehle. Hinweis: `make invoices`, `make timesheets`, `make import-master`, `make import-sheets`, `make report`; MONTH-Persistenz.
- [x] [P1] [Tooling] Pre-commit Hooks + nox-Sessions (lint, typecheck, format). Hinweis: ruff + pyright; `.pre-commit-config.yaml` + `noxfile.py`.
- [x] [P1] [Tooling] direnv für automatische venv-Aktivierung. Hinweis: `.envrc` mit `scripts/load_env.sh`.
- [x] [P1] [Daten] SQLite-DB aus Git-History entfernt. Hinweis: `data/wegpiraten.sqlite3` entfernt (2026-03-02).

## P2 Nice

- [x] [P2] [QA] Font-Fallback-Kette für DOCX-Ausgabe (WSL-Kompatibilität). Hinweis: Calibri → Liberation Sans → DejaVu in `invoice_factory.py`.
- [x] [P2] [Doku] Konzept-Dokument (`docs/konzept.md`). Hinweis: Ablaufdiagramm, Datenbankstruktur, Technologieentscheide.
- [x] [P2] [Doku] Runbook Betriebsablauf (`docs/runbook_betriebsablauf.md`). Hinweis: Monats-Ablauf, Befehle, Fehlerbehandlung.
- [x] [P2] [Doku] Externes Abrechnungsmodalitäten-Dokument eingepflegt (`docs/Annex 4_Abrechnungsmodalitäten_de.pdf`).
