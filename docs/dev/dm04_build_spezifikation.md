# DM-04: Spezifikation für den finalen Build

Stand 2026-10-09, `[Opus 5.5]`. Vorgabe für DM-05 (`[Sonnet]`). Ergebnis ist das Workbook, das
Wegpiraten Ende Oktober bekommt; danach ist das Workbook beim Kunden die einzige Quelle.

## Grundsatz: nur die Daten der originalen Datenbank

Stephan, 2026-10-09: **Relevant sind nur die Daten aus der originalen Datenbank**
(`sandbox/wegpiraten_datenbank.xlsx`). Alles, was der Testbuild `_neu.xlsx` darüber hinaus enthält
(Familien, Rollen P/S, Berichte, nachgetragene Folgeaufträge), ist Demo und wird nicht übernommen.
Der Build überführt die Originaldaten in die neue Struktur, ohne sie zu pflegen. Inkonsistenzen
werden benannt und markiert (Blatt «Prüfungen», «Fehlerliste», Befundliste), aber nicht korrigiert
und nicht als Grund genommen, den Build anzuhalten. Abgeleitet werden nur Werte, die sich aus den
Originaldaten eindeutig ergeben: Kinder (Zusammenführung nach AHV-Nummer und Name), Ansprechpersonen,
Kurzzeichen, Auftragsnummern und die Rolle P, wo genau eine Person am Auftrag arbeitet.

## Ausgangslage, geprüft am 2026-10-09

| Datei | Stand | Inhalt |
| --- | --- | --- |
| `sandbox/wegpiraten_datenbank.xlsx` | 09.10., eingefroren | alte Struktur, von Wegpiraten bis heute gepflegt: 91 Klienten, 97 Zuordnungen |
| `sandbox/wegpiraten_datenbank_neu.xlsx` | 30.09. | Testbuild aus der Datei vom 24.09. (88 Klienten) plus Demo-Ergänzungen: 84 Kinder, 91 Aufträge (davon 3 nachgetragene Folgeaufträge), 91 Betreuungen, 101 Zuordnungen, 153 Berichte; nur noch Strukturvorlage |
| `sandbox/mandate_numbers.json` | 25.09. | 91 eingefrorene Auftragsnummern (alte Klientennummer bzw. `C…+` für Folgeaufträge → `A…`), höchste 2026er Nummer `A26046` |

Die Datei vom 24.09. (`wegpiraten_datenbank(1).xlsx`), aus der `migrate.py` und `build.py` lesen,
gibt es nicht mehr. Ihr Inhalt steht eingefroren im versteckten Blatt «Klienten (alt)» des
Testbuilds; damit wurde der Vergleich unten gemacht.

### Was sich zwischen 24.09. und 09.10. geändert hat

- **Neu:** C1089, C1090, C1091 (Beginn Oktober 2026). C1091 ohne Geschäftsnummer.
- **Geschäftsnummer:** C1000 (neu 260916002), C1024 (neu 260918020, die Nummer des Folgeauftrags),
  C1088 (jetzt gesetzt: 260925017).
- **Ende und Austritt:** C1028 und C1073 enden früher und haben Austrittsangaben, C1062 hat
  Austrittsangaben bei gleichem Ende; C1065 endet später (30.04.2027).
- **Sonstiges:** C1022 Situation nach Austritt, C1040 Vorname, C1062 Geschlecht, C1079 Kostenträger
  (P9998 → P9996).
- **Zuordnung MA:** 8 Paare nur in der alten Datei (u.a. die neuen Klienten), 8 nur im Testbuild.
  Die alte Datei ist der neuere Stand, weil Wegpiraten dort bis zum 09.10. gepflegt hat.

## Quelle je Blatt

| Blatt | Quelle | Wie |
| --- | --- | --- |
| Kinder, Aufträge, Betreuungen, Ansprechpersonen | Original 09.10. | `migrate.py` → `prepare.py` → `build.py`; eine Klientenzeile wird ein Auftrag und eine Betreuung |
| Zuordnung MA | Original 09.10. | ein Paar je Zeile der «Relation Klient-MA»; Rolle P nur, wo genau eine Person am Auftrag arbeitet, sonst leer |
| Kinder (Familie) | **leer** | Familien definiert der Kunde |
| Berichte | **leer** | Die 153 Berichte im Testbuild stammen aus der Klientenübersicht, nicht aus der Datenbank: Demo |
| Stammdaten (Kostenträger, Leistungsbesteller, Leistungstypen, Mitarbeiter, Büros, Hilfsdaten, Wertelisten) | Original 09.10. | wie im Testbuild |

Der Testbuild dient nur noch als Vergleich für die Struktur (Blätter, Spalten, Prüfungen), nicht für
Inhalte.

## Schritte für DM-05

Jeder Schritt ist für sich stabil; bricht die Sitzung ab, gilt der letzte im Log vermerkte.

1. **Pfade.** `migrate.py` und `build.py`: `SRC` auf `wegpiraten_datenbank.xlsx`. Ziel
   `WEGPIRATEN_DST=sandbox/wegpiraten_datenbank_final.xlsx`; der Testbuild bleibt unverändert liegen.
   `WEGPIRATEN_HAND` auf eine nicht vorhandene Datei setzen, damit `carry_over_handwork` nichts
   übernimmt (die Funktion kehrt dann leer zurück), und `REPORTS_SEED` nicht laden.
2. **Keine nachgetragenen Folgeaufträge.** `FOLLOW_UPS` in `prepare.py` leeren. Die drei Einträge
   (C1024, C1068, C1082) hatte Wegpiraten am 25.09. bestätigt, ihre Vorgängerwerte stammen aber aus
   einem älteren Stand, nicht aus der originalen Datenbank; Wegpiraten trägt sie als Datenpflege nach.
   Damit entfällt auch der Fehler mit der Geschäftsnummer des Vorgängers bei C1024.
3. **Nummern.** `mandate_numbers.json` nur ergänzen, nicht neu schreiben (das tut
   `build_mandate_numbers` bereits). Die 88 Nummern der Klienten bis C1088 bleiben gleich. Die drei
   für die Folgeaufträge vergebenen Nummern (A26042, A26045, A26046) bleiben unbenutzt und werden
   nicht wiederverwendet. C1089 bis C1091 bekommen die nächsten Zähler ab `A26047`, nach Beginn und
   alter Klientennummer. Vergleich vorher/nachher ins Log.
4. **Rollen.** P, wo genau eine Person am Auftrag arbeitet (das tut der Build bereits); sonst leer.
   Die Prüfung «Auftrag ohne primäre Betreuungsperson» markiert den Rest.
5. **Schreibweisen** werden nicht angeglichen. Die Prüfung «Schreibweise eines Codewerts» markiert sie.
6. **Build und Prüfung.** `verify_excel_strict` muss bestehen. Danach in LibreOffice neu berechnen
   und die gecachten Werte lesen (der Import liest `data_only=True`).
7. **Vollständigkeit gegen das Original.** Jede Klientenzeile des Originals ist genau ein Auftrag mit
   genau einer Betreuung, jedes Feld mit gleichem Wert an seinem neuen Ort (Zuordnung der Felder wie
   in `migrate.py`); jede Zeile der «Relation Klient-MA» ist genau eine Zeile in «Zuordnung MA». Die
   Zahl der Kinder ergibt sich aus der Zusammenführungsregel; jede Zusammenführung wird mit den
   beteiligten Klientennummern ins Log geschrieben. Ein Wert, der fehlt oder sich verändert hat, ist
   ein Fehler des Builds und wird behoben, nicht als Befund geführt.
8. **Zählung, Prüfstand und Befundliste:** Kinder, Aufträge (erwartet 91), Betreuungen (91),
   Zuordnungen (97), Berichte (0), Familien (0) ins Log; Blatt «Prüfungen» mit Anzahl je Prüfung. Die
   Befundliste aus `dm02_fachfragen.md`, Gruppe B, mit dem Stand nach dem Build nachführen; sie geht
   mit dem Workbook an Wegpiraten.

## Abnahme

- Schritt 7 ohne Abweichung: Das Workbook enthält genau die Daten der originalen Datenbank, nichts
  weniger und nichts aus dem Testbuild.
- Die 88 bestehenden Nummern sind unverändert, neue beginnen bei `A26047`.
- Keine Familien, keine Berichte, Rolle P nur bei Aufträgen mit einer einzigen Person.
- Jeder Fehler und Hinweis im Blatt «Prüfungen» steht in der Befundliste. Offene Befunde halten die
  Übergabe nicht auf.
- Danach DM-06 (Excel unter Windows) durch Stephan.

## Entscheide aus DM-02

Hier trägt ein, wer Antworten zu den Regeln in [dm02_fachfragen.md](dm02_fachfragen.md), Gruppe A,
erhält: Nummer, Antwort, Datum, von wem. Bis dahin gelten die Vorschläge dort. Die Gruppe A betrifft
die Programme, nicht diesen Build; der Build hängt an keiner Antwort.

| # | Antwort | Datum | Quelle |
| --- | --- | --- | --- |
| A1 | Accordix-Meldepflicht hängt am Kostenträger: P1000 (KJA-FS) ja, alle anderen bisher nein. KOB fällt damit heraus. | 2026-10-09 | Stephan |
| A2 | Einführungsgespräch: 15 Minuten einmalig, nicht pro Monat. | 2026-10-09 | Stephan |
| A3 | Neue Rechnungsnummern werden niemandem angekündigt, auch dem KJA nicht. | 2026-10-09 | Stephan |
