# Konzept: Digitalisierung und Abrechnung von Erfassungsbögen

## 1. Manuelle Ablage der Erfassungsbögen
- Die in `zeiterfassungen/neuen_monat_anlegen` erzeugten Excel-Erfassungsbögen werden von den Mitarbeitenden manuell ausgefüllt.
- Die ausgefüllten Bögen werden gesammelt und manuell in ein definiertes Verzeichnis (z.B. `input/erfassungsboegen/YYYY-MM/`) abgelegt.

## 2. Modul: Einlesen und Konsolidierung in eine Datenbank
- Ein Python-Modul durchsucht das Verzeichnis und liest jeden Erfassungsbogen einzeln ein (z.B. mit `openpyxl` oder `pandas`).
- Die relevanten Daten (Klient, Leistungsdatum, Stunden, Kürzel, etc.) werden extrahiert.
- Die Daten werden in eine relationale Datenbank (z.B. SQLite) geschrieben.

## 3. Datenbankstruktur (Beispiel mit SQLite)
- **Tabelle `klienten`**: Stammdaten der Klienten
- **Tabelle `provider`**: Stammdaten der Leistungserbringer
- **Tabelle `payer`**: Stammdaten der Kostenträger
- **Tabelle `leistungen`**: Einzelne Leistungen aus den Erfassungsbögen, mit Fremdschlüsseln auf Klient, Provider, Payer, sowie Feldern für Leistungsdatum, Erfassungsmonat, Stunden, etc.

## 4. Initialer Import der Stammdaten
- Stammdaten für Klienten, Provider und Payer können initial aus Excel-Dateien importiert werden.
- Ein separates Import-Skript liest die Excel-Dateien ein und befüllt die jeweiligen Tabellen.

## 5. Webbasierte Verwaltungsoberfläche (Flask)
- Eine Flask-Webanwendung bietet eine Verwaltungsoberfläche für die Stammdaten (CRUD für Klienten, Provider, Payer).
- Die Oberfläche ermöglicht das Suchen, Bearbeiten und Anlegen von Stammdaten.
- Optional: Verwaltung und Übersicht der eingelesenen Leistungen.

## 6. Rechnungslauf (Batch)
- Ein separates Batch-Modul (z.B. `rechnungslauf.py`) erstellt für einen gewählten Abrechnungsmonat alle Rechnungen.
- Es werden alle Leistungen berücksichtigt, deren **Leistungsdatum** im Abrechnungsmonat liegt – unabhängig davon, in welchem Erfassungsbogen sie stehen.
- Leistungen, deren Leistungsdatum nicht im Monat des Erfassungsbogens liegt (z.B. Juli-Leistung im August-Bogen), werden erkannt und es erfolgt eine **Meldung** (z.B. Log, Hinweis im UI).

## 7. Sonderfall: Leistungsdatum außerhalb des Erfassungsbogen-Monats
- Beim Rechnungslauf wird für jede Leistung geprüft, ob das Leistungsdatum im Abrechnungsmonat, aber außerhalb des Erfassungsbogen-Monats liegt.
- In diesem Fall wird eine Meldung erzeugt (z.B. „Leistung vom 28.07.2025 in Bogen 2025-08.xlsx“).

## 8. Technologievorschläge
- **Backend:** Python, Flask, SQLAlchemy (ORM für SQLite)
- **Frontend:** Flask/Jinja2, Bootstrap (optional)
- **Import/Export:** pandas, openpyxl
- **Batch:** Separates Python-Skript, das per CLI oder Web-UI gestartet werden kann

---

**Ablaufdiagramm (Kurzform):**
1. Erfassungsbögen werden abgelegt
2. Import-Modul liest Bögen ein, speichert Leistungen in DB
3. Stammdaten werden initial importiert oder im Web gepflegt
4. Rechnungslauf wählt alle Leistungen im Abrechnungsmonat aus
5. Meldung bei Leistungen, die aus Bögen eines anderen Monats stammen
6. Rechnungen werden erzeugt

## Vorbereitung für den Import der Stammdaten aus der Datenbank

Um die Stammdaten aus der bestehenden Datenbank (`db_name`) im Verzeichnis `data_path` (siehe Konfiguration) zu importieren, sind folgende Vorbereitungen und Schritte notwendig:

### 1. Voraussetzungen & Installation

- **Python 3.x** muss installiert sein.
- **SQLite** ist in Python über das Modul `sqlite3` bereits integriert (keine separate Installation nötig).
- **Benötigte Python-Pakete:**
  - `pandas` (für den Import und die Verarbeitung von Excel/Tabellen)
  - `openpyxl` (für das Lesen von Excel-Dateien, falls nötig)
  - `sqlalchemy` (empfohlen für ORM und komfortablen Datenbankzugriff)
  - Optional: `flask` (für spätere Web-Oberfläche)

  Installation (z.B. im Projektordner):
  ```bash
  pip install pandas openpyxl sqlalchemy flask
  ```

### 2. Datenbank vorbereiten

- Stelle sicher, dass die SQLite-Datenbank (`db_name`, z.B. `Wegpiraten Datenbank.xlsx` oder `.db`) im Verzeichnis `data_path` existiert und die Tabellen enthält:
  - **MD_MA** (Mitarbeitende/Employees)
  - **Leistungsbesteller** (Service Requester)
  - **Zahlungsdienstleister** (Payer)
  - **MD_Client** (Klienten/Clients)

- Prüfe, ob die Tabellenstruktur den Anforderungen entspricht (z.B. Primärschlüssel, Spaltennamen).

### 3. Zugriff auf die Datenbank

- Der Pfad zur Datenbank ergibt sich aus der Konfiguration:
  ```python
  from pathlib import Path
  db_path = Path(config.structure.data_path) / config.db_name
  ```

- Beispiel für den Zugriff mit `sqlite3`:
  ```python
  import sqlite3
  conn = sqlite3.connect(str(db_path))
  ```

- Alternativ mit SQLAlchemy:
  ```python
  from sqlalchemy import create_engine
  engine = create_engine(f"sqlite:///{db_path}")
  ```

### 4. Tabellen auslesen

- Mit `pandas` können die Tabellen direkt ausgelesen werden:
  ```python
  import pandas as pd
  df_employees = pd.read_sql_query("SELECT * FROM MD_MA", conn)
  df_requester = pd.read_sql_query("SELECT * FROM Leistungsbesteller", conn)
  df_payer = pd.read_sql_query("SELECT * FROM Zahlungsdienstleister", conn)
  df_clients = pd.read_sql_query("SELECT * FROM MD_Client", conn)
  ```

### 5. Weitere Vorbereitungen

- **Backup:** Erstelle ein Backup der Datenbank, bevor du Änderungen vornimmst.
- **Zugriffsrechte:** Stelle sicher, dass du Schreib- und Leserechte auf das Datenbankverzeichnis hast.
- **Datenvalidierung:** Überprüfe die Daten auf Konsistenz und Vollständigkeit.

---

**Zusammengefasst:**
- Python-Umgebung mit den genannten Paketen einrichten.
- Sicherstellen, dass die SQLite-Datenbank und die benötigten Tabellen vorhanden sind.
- Zugriff auf die Datenbank und Tabellen mit `sqlite3` oder `sqlalchemy` vorbereiten.
- Daten mit `pandas` auslesen und weiterverarbeiten.