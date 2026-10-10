# DM-05: Finaler Build, 10.10.2026

Archivhinweis 10.10.2026: Die folgenden `sandbox/`-Pfade sind historische Build-Pfade.
Alle damaligen Dateien liegen nun unter `archiv/umstellung_datenmodell_2026-10-10/sandbox/`.
Der bytegleiche Übergabestand mit Befundliste liegt unter
`output/uebergabe_datenmodell_2026-10-10/`; Windows-Excel-Prüfung weiterhin offen.


Erstellt: `sandbox/wegpiraten_datenbank_final.xlsx`. Begleitliste:
`sandbox/befundliste_final_2026-10-10.md`. Beide bleiben lokal, ausserhalb von Git.
Die eingefrorene Originaldatei und der Testbuild sind unverändert (Hashvergleich bestanden).

| Inhalt | Anzahl |
| --- | ---: |
| Kinder | 87 |
| Aufträge | 94 |
| Betreuungen | 94 |
| MA-Zuordnungen | 101 |
| Ansprechpersonen | 49 |
| Berichte | 153 |
| Familien | 0 |

Alle 91 bestehenden Auftragsnummern sind unverändert. Ergänzt: C1089 → A26047,
C1091 → A26048, C1090 → A26049, nach Beginn und alter Nummer. Die vier bekannten
Zusammenführungen bleiben: C1019/C1070, C1035/C1059, C1050/C1077, C1053/C1054.

## Nachweis

- Kindfelder für jede Originalzeile mit dem zugeordneten Kind verglichen.
- Auftragsfelder, Kontaktfelder und Betreuungsfelder je Originalzeile verglichen;
  für die drei Folgeaufträge nur die in DM-04 beschriebenen Abweichungen zugelassen.
- Originalbemerkungen erhalten. Keine historische Anredekorrektur aus `CONTACT_RULINGS`
  angewendet; Widersprüche würden in der Ansprechpersonen-Bemerkung erhalten bleiben.
- Alle Original-MA-Paare erhalten, vier Paare für die drei Folgeaufträge zusätzlich.
  Rolle P nur bei genau einer Person am Auftrag, keine Demo-Rollen übernommen.
- Alle 153 Berichte einzeln gegen den Testbuild geprüft, einschliesslich Auftrag,
  Termin, Form, Status, Erledigt-Datum und bestehender Bemerkung.
- Keine unerklärten Feldabweichungen. 6 Aufträge und 153 Berichte mit `ZU PRÜFEN:`.
- Excel-Strukturprüfung auch nach LibreOffice-Neuberechnung bestanden, 22 benannte
  Bereiche und keine externen Links. Keine gecachten Excel-Formelfehler.

43 Workbook-Prüfungen, davon 14 offen. Der Kunde korrigiert die Daten; diese Befunde
blockieren den Build nicht. Die Befundliste enthält sämtliche offenen Prüfungen und
die nicht automatisch erkennbaren Befunde. Die 48 bekannten Berichtabweichungen aus
der Klärungsliste vom 25.09. bleiben zur kundenseitigen Prüfung benannt.

DM-63 ist mitgebaut: zwei Abschlussberichte auf Aufträgen mit Nachfolger werden als
Hinweis in Prüfungen und Fehlerliste markiert. Invarianten 49 und 50 sind im Datenmodell
ergänzt. Keine Berichte verändert oder entfernt.

## Wiederholung des Builds

Vor dem ersten Lauf die Nummernzuordnung sichern. Für den Vergleich zum damaligen Stand
kann sie aus dem Commit vor DM-05 gelesen werden:

```bash
git show 170df57:sandbox/mandate_numbers.json > /tmp/mandate_numbers_before.json
.venv/bin/python sandbox/migrate.py
.venv/bin/python sandbox/prepare.py
WEGPIRATEN_DST=sandbox/wegpiraten_datenbank_final.xlsx \
WEGPIRATEN_HAND=sandbox/wegpiraten_datenbank_neu.xlsx \
WEGPIRATEN_CARRY_FAMILIES=0 WEGPIRATEN_CARRY_ROLES=0 WEGPIRATEN_MARK_REPORTS=1 \
.venv/bin/python sandbox/build.py
```

Danach LibreOffice mit separatem Profil und separatem Ausgabeverzeichnis zum Neuberechnen
verwenden; die berechnete Datei ersetzt nur die finale Datei. Nicht nochmals mit openpyxl
speichern, sonst gehen die Formel-Caches verloren. Prüfung:

```bash
.venv/bin/python sandbox/verify_final.py \
  --workbook sandbox/wegpiraten_datenbank_final.xlsx \
  --numbers-before /tmp/mandate_numbers_before.json \
  --summary /tmp/dm05_verification.json
```

Der Prüfer liest die Quellen nur; sein Ergebnis enthält IDs, Zählungen und Prüfungsnamen,
keine Namen oder AHV-Nummern. Er ist ein einmaliges Migrationswerkzeug und wird bei DM-07
mit den übrigen Migrationsskripten entfernt oder extern archiviert. Die drei synthetischen
Regressionstests des Builds werden dann ebenfalls entfernt, falls die Skripte entfallen.

## Noch ausstehend

DM-06: Stephan prüft das finale Workbook in echtem Windows-Excel. Erst danach Übergabe
an Wegpiraten mit der Begleitliste (DM-60/52). LibreOffice und Strukturprüfung ersetzen
diese Kontrolle nicht. Änderungen des Kunden danach sind die neue Arbeitsgrundlage;
kein erneuter Build aus den Migrations-JSON-Dateien.
