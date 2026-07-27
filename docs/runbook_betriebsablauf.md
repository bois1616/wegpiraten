# Runbook – Monatlicher Abrechnungslauf (Übergangssystem WEGROSE-CLI)

## Geltungsbereich

Dieses Runbook beschreibt den vollständigen Ablauf eines monatlichen Abrechnungslaufs mit der `wegpiraten`-CLI.

Ziel:

* korrekte Rechnungen
* reproduzierbare Abläufe
* minimale Fehlerquote

---

## Voraussetzungen

* Zugriff auf Projektverzeichnis
* Aktive Python-Umgebung
* Aktuelle `wegpiraten.db`
* Gültige `.config/wegpiraten_config.yaml`
* Erhaltene Timesheets (Excel) via Proton

---

## 0. Initialer Stammdatenimport (einmalig / selten)

Nur bei Projektstart oder kompletter Neuinitialisierung.

### 0.1 Konfiguration prüfen

```bash
python -m cli validate
```

Nur bei „Konfiguration ist gültig“ fortfahren.

---

### 0.2 Stammdaten importieren

```bash
python -m cli import-master
```

Optional mit Quelle:

```bash
python -m cli import-master --source pfad/zur/datei.xlsx
```

---

### 0.3 Backup erstellen

```bash
cp wegpiraten.db backups/wegpiraten_init.db
```

---

## Monatlicher Ablauf

Beispiel: Abrechnung Februar 2026

---

## 1. Vorbereitung

### 1.1 Arbeitsverzeichnisse prüfen

Sicherstellen, dass leer sind:

* Import-Verzeichnis
* Output-Verzeichnis
* Temp-Verzeichnisse

Keine alten Dateien.

---

### 1.2 Datenbank sichern (Pflicht)

```bash
cp wegpiraten.db backups/wegpiraten_2026-02_pre.db
```

---

### 1.3 Konfiguration validieren

```bash
python -m cli validate
```

---

### 1.4 Stammdaten von Proton Drive holen (bei Änderungen)

Die Stammdaten-Datei `wegpiraten_datenbank.xlsx` liegt auf Proton Drive
(Verzeichnis `masterdata_source.remote_dir` in der Config). Zugriff nur über
die proton-drive CLI (E2E-verschlüsselt, kein Mount); die Aufrufe laufen
unter dem zentralen flock (`~/proton-drive/.proton.lock`), damit sie sich
nicht mit den Sync-Timern um den lokalen CLI-Cache streiten (SQLITE_BUSY).

```bash
python -m cli fetch-master          # nur holen (legt Datei in den Import-Ordner)
python -m cli import-master --fetch # holen + direkt importieren
```

`fetch-master` wählt remote die richtige Datei (exakter Dateiname vor
Varianten, sonst neueste), vergleicht per SHA1 mit der lokalen Kopie und
lädt nur bei Abweichung. Die Remote-Datei bleibt unverändert.

---

## 2. Timesheets übernehmen

### 2.1 Dateien ablegen

Erhaltene Excel-Dateien in Import-Verzeichnis kopieren.

Alternativ direkt von Proton Drive holen (gleicher Mechanismus wie
`fetch-master`, s. 1.4): das Monatsverzeichnis relativ zum Basis-Ordner
`masterdata_source.remote_dir` angeben. Beim Makefile-Aufruf wird das
Verzeichnis in `.tsdir` gecacht -- Folgeaufrufe brauchen kein TSDIR mehr,
ein neues TSDIR= überschreibt den Cache.

```bash
python -m cli fetch-timesheets "Timesheets - Rechnungen-Auswertungen/2026-06 Juni/Timesheets (ausgefüllt)"
# oder: make fetch-timesheets TSDIR="Timesheets - .../2026-06 Juni/Timesheets (ausgefüllt)"
# danach: make fetch-timesheets
```

Bereits aktuelle lokale Kopien werden übersprungen (SHA1-Vergleich),
Remote-Dateien bleiben unverändert.

Dateinamen prüfen:

* Monat korrekt
* keine Dubletten

---

## 3. Timesheets importieren

### 3.1 Import ausführen

Mit Monatsangabe (empfohlen):

```bash
python -m cli import-sheets 2026-02
```

Oder ohne Filter:

```bash
python -m cli import-sheets
```

---

### 3.2 Ergebnis prüfen

Ausgabe muss enthalten:

```
X Einträge importiert.
```

Bei Fehler:
→ Abbruch, Log prüfen, kein Weiterarbeiten.

---

## 4. Rechnungslauf

### 4.1 Rechnungserstellung starten

Format: MM.YYYY

```bash
python -m cli invoice 02.2026
```

---

### 4.2 Ergebnis prüfen

Erwartet:

```
Rechnungserstellung erfolgreich abgeschlossen.
```

Prüfen:

* PDFs vorhanden
* DOCX vorhanden
* Dateigrößen plausibel

---

## 5. Fachliche Kontrolle

Pflichtkontrolle (Stichprobe):

Mindestens 2–3 Rechnungen prüfen:

* Stunden vs. Timesheet
* Betrag
* Klient
* Monat
* IBAN / SPC

Bei Abweichung:
→ stoppen, Ursache klären.

---

## 6. Versand

### 6.1 Versand durchführen

* PDFs per Mail versenden
* Empfänger prüfen
* Versanddatum notieren

---

## 7. Archivierung

### 7.1 Archiv erstellen

```bash
zip -r archive_2026-02.zip \
  input/ \
  output/ \
  logs/ \
  backups/wegpiraten_2026-02_pre.db
```

---

### 7.2 Archiv prüfen

* ZIP öffnen
* Dateien sichtbar
* vollständig

---

### 7.3 Arbeitsverzeichnisse leeren

Nur nach erfolgreicher Archivprüfung.

---

## 8. Neue Timesheets erzeugen

Für Folgemonat (März 2026):

```bash
python -m cli timesheet 2026-03
```

---

### 8.1 Ergebnis prüfen

* Dateien vorhanden
* pro Klient ein Sheet
* Header korrekt

---

### 8.2 Verteilung

Timesheets an Mitarbeitende weitergeben.

---

## 9. Korrekturen (falls nötig)

### 9.1 Manuelle Korrektur

* Nur in DOCX
* PDF neu erzeugen
* Datei kennzeichnen:

```
invoice_4711_02-2026_KORREKTUR.docx
```

---

### 9.2 Dokumentation

Im Archiv:

```
KORREKTUREN.txt
```

Mit:

* Datum
* Grund
* Betrag alt/neu

---

## 10. Abschluss

### 10.1 Abschluss-Backup

```bash
cp wegpiraten.db backups/wegpiraten_2026-02_final.db
```

---

### 10.2 Monatsmarker erstellen

Datei:

```
run_2026-02.txt
```

Inhalt:

```
Monat: 02.2026
Import: OK
Rechnungen: 14
Korrekturen: Nein
Archiv: archive_2026-02.zip
Abschluss: 2026-03-05
```

---

## Fehlerbehandlung

### Import-Fehler

* Keine Weiterarbeit
* Log prüfen
* DB aus Backup wiederherstellen

### Rechnungsfehler

* DB-Backup zurückspielen
* Ursache beheben
* Neu starten

### Unklare Abweichung

→ Kein Versand.

---

## Grundregeln

1. Kein Lauf ohne Backup
2. Kein Versand ohne Kontrolle
3. Kein Löschen ohne Archiv
4. Kein Überspringen von Schritten

---

## Projektcharakter

Dieses Runbook dient dem Übergangsbetrieb.

Ziel:

* sichere Abrechnung
* minimale Risiken
* geringe Abhängigkeit vom Gedächtnis einzelner Personen

Nicht-Ziel:

* Automatisierte Vollabwicklung
* Self-Service-Betrieb
* Skalierung

---

## Einordnung

Mit diesem Runbook:

* ist das Wissen externalisiert
* ist eine Vertretung möglich
* ist das Risiko begrenzt
* bleibt der Betrieb beherrschbar
