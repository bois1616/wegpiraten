# Monatlicher Dokumentlauf mit dem neuen Datenmodell

Stand 10.10.2026. Workaround bis WEGROSE einsetzbar ist. Der Kunde pflegt die XLSX-Datenbank
und füllt Timesheets aus; Stephan erzeugt daraus die Dokumente. Befunde gehen an den Kunden,
nach dessen Korrektur beginnt der Lauf erneut mit einer neu aufgebauten SQLite-DB.

Korrektur gegenüber dem bisherigen Runbook: SQLite ist kein dauerhaft gepflegter Datenbestand.
Der Import ist Bestandteil jedes Neuaufbaus. Pfade kommen aus Config; die alten Beispiele mit
`wegpiraten.db` sind ersetzt. SMTP/automatischer Versand sind kein Bestandteil dieses Laufs.

## Monatslauf

1. **Monat festlegen und aktuelle Stammdaten holen.** Beispiel September:

   ```bash
   make fetch-master
   make validate
   ```

   Erwartet: das aktuelle neue Workbook im konfigurierten Import-Ordner, Config gültig.
   Fehlt eine Datei oder ist die Cloud-Holung gescheitert, Quelle prüfen; keine Stammdateien
   anderer Monate oder alte Klientenstruktur als Ersatz verwenden. Proton-Zugriff bleibt
   unter dem zentralen flock. Eine fehlende Arbeits-DB ist beim Validieren zulässig.

2. **Bestehende Arbeits-DB sichern und entfernen.** Nur die konfigurierte SQLite-Datei:

   ```bash
   PYTHONPATH=src .venv/bin/python - <<'PY'
   from datetime import datetime
   import sqlite3
   from shared_modules.config import Config
   from loguru import logger
   db = Config().get_db_path()
   if db.exists():
       backup = db.with_name(f"{db.stem}_vor_neuaufbau_{datetime.now():%Y%m%d_%H%M%S}.sqlite3")
       with sqlite3.connect(db) as source, sqlite3.connect(backup) as destination:
           source.backup(destination)
       db.unlink()
       logger.info("Arbeits-DB gesichert nach {}, Neuaufbau folgt", backup)
   PY
   ```

   Erwartet: Sicherung vorhanden, aktive DB entfernt. Bei Sicherungsfehler nicht löschen.
   Die Original-XLSX und archivierten Bögen bleiben erhalten.

3. **Stammdaten importieren.**

   ```bash
   make import-master
   ```

   Erwartet: neue Tabellen, Importzählung und `output/stammdaten_befunde.json` (Ausgabepfad
   gemäss Config). Fehlerhafte Daten werden gewarnt; fachliche Korrektur im Workbook durch
   den Kunden. Fehlende Tabellen/Spalten oder eine nicht leere DB sind technische Fehler:
   richtige Datei bzw. Schritt 2 prüfen. Die verarbeitete Importdatei wandert nach `done`.

4. **Ausgefüllte Bögen holen.**

   ```bash
   make fetch-timesheets TSDIR="relativer Remote-Pfad zum Monatsordner"
   ```

   Den tatsächlichen Monatsordner einsetzen. Erwartet: Kopien der ausgefüllten Bögen im
   Import-Ordner. Alte fremde Monatsdateien dort vorher prüfen und passend archivieren.

5. **Bögen importieren.**

   ```bash
   make import-sheets MONTH=2026-09
   ```

   Erwartet: Zählung, Sammel-Excel im Output, verarbeitete Bögen in `done`. Ein Bogen mit
   unbekannter/mehrdeutiger Auftragsnummer bleibt unverarbeitet liegen; Fehlerprotokoll nennt
   Datei und Zeile. Keine Teilzeilen einer solchen Datei werden gespeichert. Leere Bögen
   bleiben ebenfalls liegen. Andere Dateien laufen weiter. Nach Kundenkorrektur gesamten
   Lauf ab Schritt 2 neu aufbauen; keine einzelnen SQLite-Werte fachlich nachpflegen.

6. **Rechnungen erzeugen und Übersicht prüfen.**

   ```bash
   make invoices MONTH=09.2026
   ```

   Erwartet: DOCX, Einzel-PDFs, Sammel-PDFs und ZIP-Dateien sowie Rechnungsübersicht mit
   Auftrag, Indexkind und Prüfkennzeichen. Nicht berechenbare Aufträge werden mit Warnung
   ausgelassen; die Ausgabe ist dann zur Nacharbeit unvollständig. `PRÜFEN`-Dateien werden
   vor Versand durchgesehen. Zeiten/Tarife, Betrag, Empfänger und Geschäftsnummer kontrollieren.
   Eine manuell gesplittete Timesheet-Position `Ohne Berechnung` erscheint mit Wert 0 CHF.

   Einzelauftrag: `make invoices MONTH=09.2026 CLIENT=A26001`. Eine C-Nummer filtert alle
   Aufträge mit diesem heutigen Indexkind. Sie ist hier keine alte Auftragsnummer.

7. **Arbeitszeitprotokoll und bei Fälligkeit Accordix erstellen.**

   ```bash
   make report MONTH=2026-09
   make accordix MONTH=2026-09
   ```

   Erwartet: Arbeitszeit einschliesslich SA; Accordix je tatsächlicher Betreuung für die
   konfigurierten Kostenträger. Folgeaufträge erzeugen keine zusätzlichen Meldefälle allein
   durch eine Verlängerung. Unvollständige/ungültige Zeilen werden mit Gründen ausgelassen.
   Bewilligungsende ist kein Austritt. Protokoll lesen und Kundenkorrekturen anfordern.

8. **Manuell versenden und Monat archivieren.** Erst geprüfte Dokumente versenden.
   Workbook, verarbeitete und verbleibende Bögen, Befundlisten, Rechnungen/DOCX/PDF/ZIP,
   Arbeitszeit und Accordix-Ausgabe sowie Abschluss-DB im Monatsarchiv sichern. Archiv prüfen,
   bevor Arbeitsverzeichnisse geleert werden. Manuelle DOCX-Korrekturen dokumentieren und
   zugehörige PDF neu erstellen.

9. **Bögen für den Folgemonat erzeugen.**

   ```bash
   make timesheets MONTH=2026-10
   ```

   Erwartet: ein Bogen je aktiver MA-Auftragszuordnung, zusätzlich SA nach TS-Schalter.
   Neu beginnende/abgelaufene Bewilligungen werden für den Erfassungsmonat berücksichtigt.
   Diagnose nennt nicht erzeugte Zuordnungen und Gründe. Blattschutz-Passwort kommt wie
   bisher aus der bestehenden Secret-Konfiguration. Nur die geprüften Bögen verteilen.

## Erster Lauf nach der Umstellung

Die ersten ausgefüllten Bögen tragen noch C-Nummern. Sie werden anhand der versionierten
Zuordnung und des Leistungsdatums auf Aufträge aufgelöst. Die neue DB braucht dafür keine
Altdaten und die Sandbox ist nicht die laufende Zuordnungsquelle. Die Rechnungsnummer enthält
künftig A statt C. Das heutige Indexkind wird auch beim erneuten Lauf alter Monate verwendet.

Korrektur der früheren Zellangabe G8: Die aktuelle Config und die September-Bögen verwenden
F8 für die Nummer und F5 für Mitarbeitende. Der Code liest die konfigurierten Zellen; Layout
und Zellpositionen bleiben unverändert.

Der lokale September-Vergleich und seine Grenzen stehen in
[dm34_september_2026.md](dev/dm34_september_2026.md). Windows-Excel-Abnahme des neuen Workbooks,
Kundenübergabe und Merge bleiben separate Schritte. Die neue Datei nicht mit dem alten
Programmstand kombinieren; für den Rückweg immer alten Branch **und** alte Stammdatei verwenden.
