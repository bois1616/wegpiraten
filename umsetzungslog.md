# Umsetzungs-Log (Neueste Einträge zuerst)

## 2026-03-15

- **Feature: Genehmigungshinweis bei überzogenem Budget (`budget_exceeded`)**: Masterdata-Tabelle `masterdata_client` in `wegpiraten_datenbank.xlsx` hat neue Spalten `sr_ap_first_name`, `sr_ap_last_name`, `sr_ap_gender` (Ansprechperson direkt am Klienten). (1) `wegpiraten_config.yaml` / Modell `client`: drei Felder als `type: str`, `optional: true` ergänzt. (2) `invoice_processor.py`: SQL-SELECT um `c.sr_ap_first_name/last_name/gender` erweitert. `budget_exceeded`-Flag: `True` wenn für mindestens eine Zeitart `sum > allowed > 0`. Flag + AP-Felder in `InvoiceContext` eingetragen; `allowed_*`-Werte aus bereits berechneten Variablen bezogen (keine Doppelberechnung). (3) `rechnungsvorlage.docx`: Block `{%p if budget_exceeded %}…{%p endif %}` über Danksagung auf Seite 2 — manuell eingefügt. Pyright: 0 Fehler.

- **Fix: Bedingte Formatierung in `wegpiraten_datenbank.xlsx`**: Tabelle `masterdata_client`, Spalte `end_date`: neue Regel – wenn `HEUTE()` weniger als 40 Tage vor `end_date` liegt, wird die Zelle gelb hinterlegt (Frühwarnung auslaufende Aufträge).

- **Fix: Tolerante Datumsergänzung im Timesheet-Import**: Datumsfeld im Timesheet ist neu als Text formatiert; Eingaben wie «12», «12.», «12.3», «12.3.» werden jetzt tolerant zusammen mit dem bekannten Abrechnungsmonat zu vollständigen Daten ergänzt. `batch_import_timesheets.py`: (1) `_DAY_ONLY_PATTERN = re.compile(r"^\s*(\d{1,2})\.?\s*$")` als zweites Klassenmuster ergänzt. (2) `_parse_partial_service_date` auf Signatur `(raw_value, reporting_period: MonthPeriod)` umgestellt (statt `reporting_year: int`). (3) Methode prüft zuerst `_SHORT_DATE_PATTERN` (tt.mm/tt.mm.), dann `_DAY_ONLY_PATTERN` (nur tt/tt.); Monat und/oder Jahr werden aus `reporting_period.start` ergänzt. Nicht erkennbare Werte geben `None` zurück → bestehende Fehlerprotokoll-Logik greift. Pyright: 0 Fehler.

## 2026-03-14

- **Feature Einführungsgespräch kostenfrei bei Privatleistungen (ST99) im Startmonat**: `invoice_processor.py`: (1) `c.start_date AS client_start_date` in den SQL-SELECT aufgenommen. (2) Modulkonstanten `_PRIVATE_SERVICE_TYPE_CODE = "ST99"` und `_INTRO_FREE_MINUTES = 15` definiert. (3) Nach Auflösung von `service_type` wird `is_private_intro_month` ermittelt: gilt wenn Code = ST99 und Abrechnungsmonat = Monat aus `client_start_date`. (4) `remaining_intro_minutes = 15` vor der date_groups-Schleife. In der Schleife werden die ersten 15 min `direct_time` (chronologisch; über mehrere Tage wenn nötig) als eigene Position mit `Kosten = 0.0`, `Bezeichnung = "Einführungsgespräch – ohne Berechnung"` und `is_intro = True` eingefügt; die verbleibende `direct_time` des Tages wird normal berechnet. Normale Positionen erhalten `Bezeichnung = ""` und `is_intro = False`. (5) `sum_kosten == 0`-Guard angepasst: bei `is_private_intro_month` wird auch eine Null-Kosten-Rechnung ausgestellt (Ausnahme der sonst geltenden Filterregel). Pyright: 0 Fehler. Noch offen: Rechnungsvorlage anpassen (Template-Felder `is_intro` und `Bezeichnung` einbauen).

## 2026-03-11

- **Rechnungsvorlage aktualisiert**: `templates/rechnungsvorlage.docx` überarbeitet (kleinere Layout-Anpassungen).

## 2026-03-09

- **Feature CLIENT-Filter für Rechnungslauf**: `make invoices` unterstützt jetzt optionalen `CLIENT=`-Parameter (kommagetrennte Klienten-IDs, z.B. `CLIENT=C1017,C1038`). Nur die angegebenen Klienten werden abgerechnet. Umgesetzt in `src/cli.py` + Makefile.

## 2026-03-07

- **Formate korrigiert (dezimale Stunden → Minuten)**: Dezimale Stundenangaben im Stammdaten-Import wurden fälschlicherweise ohne vorherige Multiplikation konvertiert. Fix: erst `× 60`, dann Konversion zu `int`. Betrifft `src/data_imports/import_masterdata.py`. Rechnungsvorlage ebenfalls aktualisiert.

- **Feature Validierungslogik im Zeiterfassungsbogen-Template**: Excel-Template `templates/time_sheet_template.xlsx` um zwei Validierungen erweitert: (1) C32 Warnformel — zeigt «Budget überzogen!» wenn C31/D31/E31 negativ (Prio 1) oder «Zeiten für indirekte Fallbearbeitung überprüfen!» wenn E29 > 50% von D29 (Prio 2). (2) E29 bedingte Formatierung (hellrot) wenn indirekte Summe > 50% der direkten Summe.

## 2026-03-06

- **Bugfix SPC-Zahlschein Tenant-Daten**: SPC/Zahlschein nutzte globale Config-Daten statt klientenspezifische Tenant-IBAN und -Anschrift. Fix: `invoice_factory.py` und `invoice_processor.py` verwenden nun klientenspezifische Tenant-Daten. Tenant-Modell um `name`-Feld erweitert (YAML, SQL, Context, Factory); ALTER TABLE-Migration für bestehende DBs ergänzt. `make timesheets` speichert MONTH nicht mehr in `.month`-Datei. Zeiterfassungsbögen-Template ebenfalls aktualisiert.

## 2026-03-05

- **Feature Budget-Tracking je Spalte in Zeiterfassungsbögen**: Excel-Template um Obergrenze-Zeile (Row 30) mit Budget je Spalte (Fahrtzeit, Direkter Fallkontakt, Indirekte Fallbearbeitung) und Differenz-Zeile (Row 31) mit bedingter Formatierung erweitert (Grün ≤80% verbraucht, Gelb 80–100%, Rot über Obergrenze). `HeaderDataModel` um Budget-Felder ergänzt; `TimeSheetHeaderCells` mit Zellreferenzen C30/D30/E30 konfiguriert; `TimeSheetFactory` + `TimeSheetBatchProcessor` schreiben int-Werte (Minuten) in Obergrenze-Zeile, `allowed_hours_per_month` in Stunden (÷60) in C7. Makefile: `help`-Target ergänzt. Diverse Pyright-Fixes in `data_imports`, `invoices` (`cast()`, NaN-Prüfung, sort_values).

## 2026-03-03

- **Bugfix Legacy-Dedup-Tabelle**: `service_data_import_dedup` hatte einen FK auf `service_data`. Ohne vorheriges DELETE wurde `DELETE FROM service_data` blockiert. Tabelle wird jetzt in `_ensure_schema_and_dedup` automatisch vor dem Schema-Setup gedropt.

- **Doubletten entfernt, Rechnungspositionen tagesweise aggregiert**: Vollständige Hash-basierte Doubletten-Prüfung aus `batch_import_timesheets.py` entfernt (hashlib, `_dedup_signature`, `service_data_import_dedup`, `merge_target`); jede Zeile wird direkt als eigenständiger Datensatz importiert. In `invoice_processor.py` werden Einträge desselben Clients am gleichen Datum per `groupby` summiert, sodass mehrere Einsätze als eine Rechnungsposition erscheinen.

- **Neues Modul Arbeitszeitprotokoll**: `src/reports/arbeitszeit_report.py` erstellt Excel-Protokoll aus `service_data` (Detail-Sheet + Zusammenfassung je Mitarbeiter). Neuer CLI-Befehl `report`; `make report` im Makefile. `batch_import_timesheets.py`: `_record_info`-Methode; Doubletten werden als Info/Doublette mit vollständigen Felddaten ins Fehlerprotokoll eingetragen. Rechnungsvorlage aktualisiert.

- **Makefile, Formatierungen, Rechnungsvorlage**: Makefile mit make-Targets für alle CLI-Befehle; MONTH-Persistenz via `.month`-Datei. `.gitignore`: `.month` ergänzt. `invoice_factory.py`: Rechnungsnummer-Trenner `_` → `-` (Format: `2026-02-C1010`). `filters.py`: Zeitformat `XhYYm` → `X:YY h`. `templates/rechnungsvorlage.docx` aktualisiert.

## 2026-03-02

- **SQLite-DB aus Git entfernt**: `data/wegpiraten.sqlite3` aus dem Repository entfernt (Produktivdaten gehören nicht ins Repo).

- **Timesheet-Import gehärtet**: C6-Abrechnungsmonat gegen CLI-Monat prüfen (Warnung bei Abweichung); `_record_warning`-Methode; Datum ausserhalb Monat im Fehlerbericht; unidentifizierbares Datum mit Zeiten = fataler Fehler (kein Done-Move); `date.today()`-Fallback entfernt; Zeitsumme-0-Warnung; kein Timestamp beim Verschieben nach Done. `import_masterdata.py`: FK-Diagnostik bei IntegrityError; kein Timestamp beim Verschieben nach Done. `invoice_processor.py`: Rechnungen mit Zeitsumme 0 oder Betrag 0 überspringen.

## 2026-02-27

- **Externes Dokument eingepflegt**: `docs/Annex 4_Abrechnungsmodalitäten_de.pdf` ins Repository aufgenommen.

- **Bugfixes Font-Fallback, Spaltennamen, FK-Feldnamen**: `invoice_factory.py`: Font-Fallback-Kette (Calibri via WSL → Liberation Sans → DejaVu) für WSL2-Kompatibilität. `document_utils.py`: Spalten umbenannt (Soll → Max, Leistungszeit entfernt); bedingte Formatierung hellrot wenn Ist > Max für alle Max/Ist-Paare. `batch_import_timesheets.py`: Zeiten nicht mehr mit 60 multiplizieren (bereits Minuten). `time_sheet_factory.py` + `time_sheet_batch_processor.py`: FK-Feldnamen auf `allowed_travel_time`, `allowed_direct_effort`, `allowed_indirect_effort` korrigiert.

- **Budget-Felder für Klienten; Integer-Minuten; Rechnungsübersicht erweitert**: Clients-Stammdaten: `allowed_travel_time`, `allowed_direct_effort`, `allowed_indirect_effort` (int, Minuten) statt float Stunden; `multiply_by: 60` im Import. `service_data`: Zeitfelder jetzt INTEGER (Minuten) statt REAL (Dezimalstunden); `_minutes_to_hours` entfernt. Rechnungsübersicht: Spalten Zahlungsträger, Klient, Büro + Soll/Ist-Spalten je Fallkategorie + Max Total.

## 2026-02-16

- **Datumsanpassungen, Namenskonvention, `--no-reset`-Option**: Fehlendes oder fehlerhaftes Jahr im Leistungsdatum wird korrigiert. Namenskonvention für Rechnungen als DOCX und PDF vereinheitlicht. CLI um `--no-reset`-Flag für `import-sheets` erweitert (verhindert `DELETE FROM service_data` vor Import). `batch_import_timesheets.py` grundlegend überarbeitet (+450 LOC); `import_masterdata.py` angepasst; `invoice_processor.py` erweitert. Rechnungsvorlage aktualisiert.

## 2026-02-15

- **Doubletten-Logik erweitert, Fehlerlogs definiert**: `batch_import_timesheets.py`: Hash-basierte Doubletten-Erkennung (`_dedup_signature`, `service_data_import_dedup`); Fehlerlogs mit vollständigen Felddaten je Doublette. `import_masterdata.py` vereinfacht. Rechnungsvorlage angepasst (`.bak` als Sicherung).

- **Rechnungsvorlage: Summe min und hh:mm; Upsert-Logik für Timesheet-Import**: Template um Summenzeilen in Minuten und im Format `hh:mm` erweitert. Upsert-Logik in `batch_import_timesheets.py` eingeführt, um Doubletten bei mehrfachem Import zu vermeiden. `docs/konzept.md` erstellt.

## 2026-02-06

- **Invoice Batch Lauf und Feintuning Invoice Template**: Vollständiger Rechnungslauf auf realen Daten durchgeführt. `invoice_processor.py` grundlegend erweitert (+280 LOC); `invoice_factory.py` ausgebaut; `filters.py` für Jinja2-Zeitformate neu erstellt; `import_masterdata.py` mit Payer/Provider-Import ausgebaut; Config überarbeitet; Rechnungsvorlage überarbeitet; alte `rechnungsvorlage_obsolet.docx` entfernt.

- **Feintuning Invoice Template**: Template-Layout finalisiert; Import-Skript um weitere Felder ergänzt.

## 2026-02-05

- **Erzeugung von Timesheets**: `src/shared_modules/config.py` erweitert; `src/utils/encrypt_secret.py` ausgebaut; Timesheet-Template angepasst.

- **Schema-Anpassungen, Timesheet Import**: `.config/wegpiraten_config.yaml` erweitert; `batch_import_timesheets.py` grundlegend überarbeitet; SQLite-Schema um fehlende Spalten ergänzt; `table_range.py` und `time_sheet_factory.py` angepasst.

- **fix(import): Stammdaten-Import an aktuelle Tabellen anpassen**: `import_masterdata.py` an aktuelle DB-Tabellen angepasst; `templates_config.py` überarbeitet; `wegpiraten.sqlite3` neu angelegt; CLI (`src/cli.py`) mit ersten Befehlen befüllt.

- **Refactor: CLI-only Architektur mit typer, Tooling und Codequalität**: Neuer zentraler CLI Entry-Point `src/cli.py` mit typer. GUI/Flask-Abhängigkeiten nach `src/unused/gui` verschoben. `noxfile.py` für Linting (ruff) und Type-Checking (pyright). Pre-commit Hook. direnv (`.envrc`). `pyrightconfig.json` (strikt). Alle Pyright-Fehler (60+) behoben. Pydantic v1 → v2 (field_validator → model_validator). `entity.py` + `month_period.py` nach `src/shared_modules/`. `CLAUDE.md` + `AGENTS.md` angelegt. `docs/runbook_betriebsablauf.md` erstellt.

## 2025-10-09

- **Archivierung alter Stand**: Letzter Commit der alten Version vor Komplett-Neustart als Archiv markiert.

## 2025-10-07

- **Pydantic Modelle statisch; Pfade refactored**: Viele dynamisch generierte Pydantic Modelle wieder statisch gemacht (besser wartbar), aber weiterhin mit `config.py` abgeglichen. Pfade refactored; Zeiterfassungsbögen angepasst und geprüft.

- **Config maximal dynamisiert**: Dateiablage konsistenter; Logos nach `graphics/` verschoben.

## 2025-10-06

- **Anlage eines neuen Monats umgestellt**: Modul für `neuen_monat_anlegen` auf Processor/Factory-Muster umgestellt (noch nicht final getestet).

- **Import beendet, Pydantic dynamisiert**: Stammdaten-Import abgeschlossen; Pydantic-Modelle dynamisiert; optionale Felder über Config konfigurierbar.

- **Pydantic Modelle mit field_mappings dynamisiert**: `field_mappings` in Config zusammengefasst; Pydantic-Modelle durch Spec in Config gesteuert.

## 2025-10-05

- **Import Stammdaten über Config-Objekt**: Vollständiger Stammdaten-Import (Klienten, Provider, Payer) über Config-Singleton. Pydantic-Modell aufwändig angepasst.

- **Import Stammdaten aus Excel begonnen**: Erste Version des Excel-Imports. Pydantic-Modell initial an Config angepasst. TODO: `invoice_batch` auf SQLite umstellen.

## 2025-10-04

- **Schutz von Erfassungsdateien verstärkt**: Schutzmechanismen gegen versehentliches Überschreiben von ausgefüllten Zeiterfassungsbögen eingebaut.

- **Logger in Config konfiguriert**: Config-Klassen für Reporting in eigene Dateien ausgelagert; `raise` durch Logging abgesichert.

## 2025-10-03

- **Module geteilt und refactored**: Codebase in kleinere Module aufgeteilt.

- **Reporting abgesichert, Passwörter in .env**: Passwörter nach `.env` ausgelagert; `Config`-Klasse entsprechend angepasst; Programm zur Erstellung von Passwörtern für `.env` erstellt; Flask-App (`app.py`) berücksichtigt.

- **Pydantic Umstellung komplettiert**: Ausgabe getestet und verifiziert.

## 2025-10-01–10-02

- **Datenkonversionsfehler behoben**: `safe_str`-Hilfsfunktion eingeführt. Weitere Umstellung auf Pydantic; type hints und Kommentierung vervollständigt.

## 2025-09-22

- **Neuen Monat anlegen refactored**: `create_new_time_sheets_batch.py` auf Processor-/Factory-Muster umgestellt (ungeprüft).

- **Module umstrukturiert**: Module eine Ebene nach oben verschoben; `.env`-Datei angelegt; alle Imports angepasst und geprüft.

- **Kontext mit Template abgeglichen**: Kontextobjekt mit Template-Felder final abgeglichen; Aufrufe durch Exceptions abgesichert; Ablauf geprüft, Fehler behoben.

## 2025-09-21

- **Komplettes Refactoring, Jinja2-Filter**: Umstellung auf Jinja2-Filter; Ausdünnung des Codes; Kontext an Template-Felder angepasst.

## 2025-09-18

- **Kontextobjekt implementiert**: Datentransfer-Objekt zwischen Datenbank und Jinja2-Template implementiert.

## 2025-09-17

- **Flask GUI begonnen**: Erste Flask-Webanwendung für Stammdatenverwaltung aufgesetzt (später archiviert zugunsten CLI).

## 2025-09-16

- **Sammel-PDF je Zahlungsdienstleister**: Rechnungs-PDFs je Zahlungsdienstleister gebündelt und im Output-Verzeichnis abgelegt.

- **PDFs zusammengefasst**: Einzeln erzeugte PDFs zusammengeführt; Dateibenennung noch ausstehend (TODO).

- **Weitere Aufteilung in Komponenten**: Abrechnungsperiode dynamisiert.

## 2025-09-15

- **Formatierung, Logs**: Code-Formatierung bereinigt; Log-Ausgaben verbessert.

- **Modularisierung, Loguru**: Code in Module aufgeteilt; Logging auf Loguru umgestellt.

## 2025-09-14

- **OO-Version begonnen**: Neustart als objektorientierte Version; `data_path`-Fehler identifiziert.

## 2025-09-13

- **Einzahlungsschein und SPC exakter formatiert**: SPC-konformer Einzahlungsschein (Swiss Payment Standard) genauer formatiert.

- **Config erweitert, Programm angepasst**: `Config`-Klasse um weitere Felder erweitert; Rechnungserzeugung darauf angepasst.

## 2025-09-12

- **Rechnungserstellung fast final formatiert**: Layout und Inhalt der Rechnungen finalisiert; Einzahlungsschein korrekt eingebunden.

## 2025-09-11

- **Empfängerdaten in Config, erster Aufschlag Einzahlungsschein**: Empfängerangaben (IBAN, Name, Adresse) in Config ausgelagert; erster Einzahlungsschein als Anhang der Rechnung.

- **Refactoring, tmp-Verzeichnis, ZIP-Ausgabe**: Code weiter refactored; temporäres Arbeitsverzeichnis eingebunden; Rechnungen als ZIP-Archiv ausgegeben; Satzbettkontrolle ergänzt.

## 2025-09-10

- **Gruppierung nach Zahlungsdienstleister, Übersichtstabelle**: Rechnungen nach Zahlungsdienstleister gruppiert; erste Übersichtstabelle erzeugt (TODO: Namen + Rechnungsdatum).

- **Refactored in Funktionen**: Skript in wiederverwendbare Funktionen aufgeteilt.

## 2025-09-08

- **Summen über Spalten, Formatanpassungen**: Spaltensummen in Rechnungsübersicht; Formatierungen angepasst.

## 2025-09-07

- **Formatanpassungen**: Layout-Feinschliff der Rechnungsausgabe.

## 2025-09-06

- **Rechnungserstellung: Serienbrief**: Erste funktionsfähige Rechnungserzeugung als DOCX-Serienbrief via docxtpl.

## 2025-09-04

- **Anlage neuer Zeiterfassungs-Sheets**: Neue leere Zeiterfassungsbögen gem. Kliententabelle werden erzeugt; aktiv-Status wird berücksichtigt.

## 2025-09-03

- **QR Code für IBAN**: QR-Code für IBAN (Swiss Payment Standard) in Rechnung integriert.

- **Test für Vorlagen und Testdatensätze**: Umgang mit Vorlagen (Tabelle im Serienbrief) und Testdatensätzen erprobt.

- **Initial Commit**: Erstes Commit; Grundstruktur des Projekts.
