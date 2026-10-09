# DM-04: Spezifikation für den finalen Build

Stand 2026-10-09, `[Opus 5.5]`. Vorgabe für DM-05 (`[Sonnet]`). Ergebnis ist das Workbook, das
Wegpiraten Ende Oktober bekommt; danach ist das Workbook beim Kunden die einzige Quelle.

## Grundsatz: nur die Daten der originalen Datenbank

Stephan, 2026-10-09: **Relevant sind nur die Daten aus der originalen Datenbank**
(`sandbox/wegpiraten_datenbank.xlsx`). Alles, was der Testbuild `_neu.xlsx` darüber hinaus enthält
(Familien, Rollen P/S), ist Demo und wird nicht übernommen. **Ausnahme (Korrektur Stephan,
2026-10-09): Berichte und die drei Folgeaufträge werden übernommen, aber als «zu prüfen»
markiert** (Abschnitt «Markierung»).
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
| Berichte | Testbuild, **markiert «zu prüfen»** | `carry_over_handwork`, nur der Berichtsteil; die 153 Berichte stammen aus der Klientenübersicht |
| Folgeaufträge C1024, C1068, C1082 | `FOLLOW_UPS` in `prepare.py`, **markiert «zu prüfen»** | Vorgänger und Nachfolger, wie im Testbuild |
| Stammdaten (Kostenträger, Leistungsbesteller, Leistungstypen, Mitarbeiter, Büros, Hilfsdaten, Wertelisten) | Original 09.10. | wie im Testbuild |

Sonst dient der Testbuild nur als Vergleich für die Struktur (Blätter, Spalten, Prüfungen).

## Markierung «zu prüfen»

Was nicht aus der originalen Datenbank stammt, aber übernommen wird, beginnt in seiner Bemerkung mit
dem festen Text `ZU PRÜFEN:` und einem Satz zur Herkunft:

- Bericht (`report.notes`): `ZU PRÜFEN: aus der Klientenübersicht übernommen (Umstellung 10/2026).`
- Vorgänger und Nachfolger (`mandate.notes`): `ZU PRÜFEN: Folgeauftrag nachgetragen, Vorgängerwerte
  aus dem Stand 02.09.2026 (Umstellung 10/2026).`

Neue Prüfung im Workbook, Art Hinweis: «Übernommene Angabe zu prüfen», je Blatt Aufträge und Berichte,
zählt die Zeilen, deren Bemerkung mit `ZU PRÜFEN:` beginnt. Wer geprüft hat, löscht den Vorsatz;
dann verschwindet der Hinweis. Neue Invariantennummer 50 im Datenmodell (49 ist DM-63).

## Schritte für DM-05

Jeder Schritt ist für sich stabil; bricht die Sitzung ab, gilt der letzte im Log vermerkte.

1. **Pfade.** `migrate.py` und `build.py`: `SRC` auf `wegpiraten_datenbank.xlsx`. Ziel
   `WEGPIRATEN_DST=sandbox/wegpiraten_datenbank_final.xlsx`; der Testbuild bleibt unverändert liegen.
   `WEGPIRATEN_HAND=sandbox/wegpiraten_datenbank_neu.xlsx`; in `carry_over_handwork` die Übernahme
   von `family_id` und `role` per Schalter abschalten (nicht löschen), nur die Berichte übernehmen
   und mit `ZU PRÜFEN:` markieren.
2. **Folgeaufträge.** `FOLLOW_UPS` in `prepare.py` bleibt (C1024, C1068, C1082), Vorgänger und
   Nachfolger bekommen die Markierung `ZU PRÜFEN:`. Dazu eine Korrektur am Build: C1024 hat in der
   originalen Datenbank seit dem 09.10. die neue Geschäftsnummer (260918020); der Vorgänger behält
   die aus dem Stand 02.09. (250911003). Dafür ein Feld `old_application_number`; heute kopiert
   `apply_follow_ups` die Quellnummer auf beide.
3. **Nummern.** `mandate_numbers.json` nur ergänzen, nicht neu schreiben (das tut
   `build_mandate_numbers` bereits). Die 91 bestehenden Nummern bleiben gleich, die Folgeaufträge
   behalten A26042, A26045 und A26046. C1089 bis C1091 bekommen die nächsten Zähler ab `A26047`, nach
   Beginn und alter Klientennummer. Vergleich vorher/nachher ins Log.
4. **Rollen.** P, wo genau eine Person am Auftrag arbeitet (das tut der Build bereits); sonst leer.
   Die Prüfung «Auftrag ohne primäre Betreuungsperson» markiert den Rest.
5. **Schreibweisen** werden nicht angeglichen. Die Prüfung «Schreibweise eines Codewerts» markiert sie.
6. **Build und Prüfung.** `verify_excel_strict` muss bestehen. Danach in LibreOffice neu berechnen
   und die gecachten Werte lesen (der Import liest `data_only=True`).
7. **Vollständigkeit gegen das Original.** Jede Klientenzeile des Originals ist genau ein Auftrag mit
   genau einer Betreuung (bei den drei Folgeaufträgen: Vorgänger plus Nachfolger, deren Abweichungen
   vom Original genau die in `FOLLOW_UPS` beschriebenen sind), jedes Feld mit gleichem Wert an seinem neuen Ort (Zuordnung der Felder wie
   in `migrate.py`); jede Zeile der «Relation Klient-MA» ist genau eine Zeile in «Zuordnung MA». Die
   Zahl der Kinder ergibt sich aus der Zusammenführungsregel; jede Zusammenführung wird mit den
   beteiligten Klientennummern ins Log geschrieben. Ein Wert, der fehlt oder sich verändert hat, ist
   ein Fehler des Builds und wird behoben, nicht als Befund geführt.
8. **Zählung, Prüfstand und Befundliste:** Kinder, Aufträge (erwartet 94), Betreuungen (94),
   Zuordnungen (97 plus die kopierten der drei Nachfolger), Berichte (153, alle markiert, alle einem
   Auftrag zugeordnet), Familien (0) ins Log; Blatt «Prüfungen» mit Anzahl je Prüfung. Die
   Befundliste aus `dm02_fachfragen.md`, Gruppe B, mit dem Stand nach dem Build nachführen; sie geht
   mit dem Workbook an Wegpiraten.

## Abnahme

- Schritt 7 ohne Abweichung: Das Workbook enthält genau die Daten der originalen Datenbank, dazu nur
  die markierten Berichte und Folgeaufträge.
- Die 91 bestehenden Nummern sind unverändert, neue beginnen bei `A26047`.
- Keine Familien, Rolle P nur bei Aufträgen mit einer einzigen Person.
- Die Prüfung «Übernommene Angabe zu prüfen» zählt 153 Berichte und 6 Aufträge.
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
