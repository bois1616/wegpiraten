# DM-34: September-Vergleich 2026

Stand 10.10.2026. Alter Programmstand: `backup/pre-datamodel-v2` (`e960512`). Neuer Stand:
Umstellung auf Aufträge in `feature/datamodel-v2`. Getrennte Configs, DBs, Import-, Done-,
Temp- und Ausgabeordner unter `/tmp/wegpiraten-september`; nur Kopien verwendet.

Quellen: 66 archivierte September-Timesheets, Original-Stammdatei vom 09.10.2026 für den
alten Lauf, verlustgeprüfter finaler Build für den neuen Lauf. Der Vergleich rekonstruiert
keinen historischen Stammdatenstand; es gelten wie entschieden heutige Person-/Indexdaten.
Die archivierten September-PDFs sind zusätzlich die Referenz für die Einzelbeträge.

| Prüfung | Alt | Neu |
| --- | ---: | ---: |
| Importierte Leistungszeilen | 167 | 167 |
| Fahrtzeit (Minuten) | 6.180 | 6.180 |
| Direktkontakt (Minuten) | 15.380 | 15.380 |
| Indirekte Bearbeitung (Minuten) | 6.585 | 6.585 |
| Einzelrechnungen/DOCX | 53 | 53 |
| Einzel- und Sammel-PDFs | 60 | 60 |
| Summe der gerundeten Einzelbeträge (CHF) | 60.385,93 | 60.385,93 |

Keine Abweichung der Rohzeilen (Datei, Mitarbeitende, Datum, Minutenarten, Kilometer,
Notiz). Nach C→A-Zuordnung identische Rechnungspositionen, Zeiten, Tarife und Beträge,
Kostenträger, Besteller, Standort und Zahlungsdaten. Alle 53 archivierten Einzel-PDF-Beträge
stimmen ebenfalls mit den neu berechneten Einzelbeträgen überein. Alle 53 neuen SCOR-
Prüfziffern gültig. Jede Einzelrechnung hat wie zuvor zwei Seiten; Rechnungsseite und
Zahlteil sind visuell stichprobenweise geprüft, ohne Layoutbruch.

## Erklärte Abweichungen

- Rechnungsnummer/SCOR-Referenz/Dateiname wechseln C→A; Rechnungsdatum ist das Datum der
  Neuberechnung. Die neue Übersicht zeigt zusätzlich Auftrag, Indexkind und Prüfkennzeichen.
- Rand-Leerzeichen an Namen/Kontakten entfallen durch die bereits spezifizierte Überführung.
- Zwei Anreden unterscheiden sich: C1001/A23003 und C1081/A26036. Die zusammengeführte
  Ansprechperson AP015 hat widersprüchliche Anreden im Original. Der finale Build erhält
  die Mehrheitsanrede und einen Hinweis zur Herkunft. Zugehörige Rechnungen werden zur
  Kundenprüfung markiert; keine Behauptung, die fachlich richtige Anrede sei automatisch
  bestimmt worden. Die fachliche Korrektur erfolgt durch den Kunden im Workbook.
- C1068/A26042: alte Bogenbudgets 480/480/240 Minuten, aktuelles Auftragskontingent
  1440/1800/900. Das Workbook ist die Quelle; abweichende Bogenbudgets werden gewarnt.
  Positionen und Betrag sind identisch, die Kontingentanzeige wird aktualisiert.
- Ein fehlender AHV-Wert führte im neuen SQL/pandas-Pfad zunächst zum Text `nan`. Der Fehler
  wurde vor Abschluss behoben; fehlender Wert bleibt leer, entsprechender Test ergänzt.
- Die zuerst gemeldete Gesamtsumme 60.385,92 war die Summe der ungerundeten Rechenwerte.
  Die Summe der tatsächlichen, auf Rappen gerundeten 53 Einzelrechnungen ist 60.385,93.
  Dieser Unterschied besteht auch im alten Code und ist keine Schemaabweichung. Die
  bestehende Berechnungs-/Summenlogik wurde dafür nicht nebenbei verändert.

Neun Rechnungen sind wegen Datenbefunden als `PRÜFEN` markiert. Drei Bögen bleiben in beiden
Läufen mangels importierbarer Zeilen liegen. Diese Fälle wurden nicht still entfernt.

## Weitere Integration

Arbeitszeitprotokoll und Accordix September wurden mit dem neuen Schema erzeugt. 78 leere
Oktober-Bögen im isolierten Testlauf, mit einem ausschliesslich dafür gesetzten Testpasswort;
diese Bögen sind nicht zur Kundenverteilung bestimmt. Ein synthetischer neuer Bogen wurde
befüllt und erfolgreich wieder importiert. Ein synthetisches Einführungsgespräch bleibt als
15-Minuten-Position mit Betrag 0 CHF sichtbar; im echten September gab es keinen solchen
Notizfall. Fehlender Tarif lässt die ganze betroffene Rechnung mit Warnung aus.

## Lokale Ausgabe und Wiederholung

Die neue Ausgabe liegt unter `output/test_datamodel_2026-09_20261010`, einschliesslich
DOCX/PDF-ZIPs, Übersicht und lokalem Vergleichsbericht. Diese Dateien mit Kundendaten
bleiben ausserhalb von Git. Der Test-Bogensatz verwendet nur ein Testpasswort.

Ein erneuter Kontextvergleich ist mit dem versionierten Prüfer möglich:

```bash
PYTHONPATH=src .venv/bin/python tools/compare_invoice_contexts.py \
  --old /tmp/wegpiraten-september/old/contexts.json \
  --new /tmp/wegpiraten-september/new/contexts.json \
  --database /tmp/wegpiraten-september/new/data/wegpiraten.sqlite3 \
  --mapping resources/legacy_mandate_mapping.json --month 2026-09 \
  --output /tmp/september_context_comparison.json
```

Die Kontexte wurden unmittelbar aus der tatsächlichen Rechnungserzeugung vor der
PDF-Konvertierung aufgezeichnet. Der Prüfer meldet IDs und Feldnamen, keine Namen oder
AHV-Nummern. Eine innerhalb des Monats auf mehrere Aufträge aufgeteilte Alt-Rechnung
wird ausdrücklich zur manuellen Gegenprüfung gemeldet.

## Abnahmegrenzen

Finanzieller Alt-Neu-Abgleich abgeschlossen. Fachliche Prüfung der Datenbefunde, insbesondere
Anrede und Kontingent, durch Stephan/Kunden steht aus. Kein Versand, keine Cloud-Änderung,
kein Push/Merge. DM-06 Windows-Excel und DM-41 Accordix August sind offen. Die Generalprobe
nach dem aktualisierten Betriebs-Runbook wird nicht als bereits durchgeführter Produktivlauf
behauptet. Die Original-DB und Monatsarchive sind unverändert.
