# DM-04: Spezifikation für den finalen Build

Stand 2026-10-09, `[Opus 5.5]`. Vorgabe für DM-05 (`[Sonnet]`). Ergebnis ist das Workbook, das
Wegpiraten Ende Oktober bekommt; danach ist das Workbook beim Kunden die einzige Quelle.

## Grundsatz: Daten werden übernommen, nicht gepflegt

Stephan, 2026-10-09: Datenpflege ist nicht Aufgabe der Umstellung. Der Build übernimmt die Daten so,
wie sie in der Quelle stehen. Inkonsistenzen werden benannt und markiert (Blatt «Prüfungen»,
«Fehlerliste», Logeintrag), aber nicht korrigiert und nicht als Grund genommen, den Build anzuhalten.
Ausnahme ist nur, was der Build selbst falsch machen würde (Schritt 2).

## Ausgangslage, geprüft am 2026-10-09

| Datei | Stand | Inhalt |
| --- | --- | --- |
| `sandbox/wegpiraten_datenbank.xlsx` | 09.10., eingefroren | alte Struktur, von Wegpiraten bis heute gepflegt: 91 Klienten, 97 Zuordnungen |
| `sandbox/wegpiraten_datenbank_neu.xlsx` | 30.09. | Testbuild aus der Datei vom 24.09. (88 Klienten) plus Handarbeit: 84 Kinder, 91 Aufträge, 91 Betreuungen, 101 Zuordnungen, 153 Berichte |
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
| Kinder, Aufträge, Betreuungen, Ansprechpersonen | alte Datei 09.10. | `migrate.py` → `prepare.py` → `build.py`, wie im Testbuild |
| Zuordnung MA (welche Paare) | alte Datei 09.10. | wie oben |
| Zuordnung MA (Rolle P/S) | Testbuild | `carry_over_handwork`, Schlüssel (Auftrag, Mitarbeitende) |
| Kinder (Familie) | **keine**: leer übergeben | Die Einträge im Testbuild waren Demo (Stephan, 2026-10-09); Familien definiert der Kunde |
| Berichte (ganzes Blatt) | Testbuild | `carry_over_handwork` |
| Stammdaten (Kostenträger, Leistungsbesteller, Leistungstypen, Mitarbeiter, Büros, Hilfsdaten, Wertelisten) | alte Datei 09.10. | wie im Testbuild |

## Schritte für DM-05

Jeder Schritt ist für sich stabil; bricht die Sitzung ab, gilt der letzte im Log vermerkte.

1. **Pfade.** `migrate.py` und `build.py`: `SRC` auf `wegpiraten_datenbank.xlsx`. Den Build nicht über
   den Testbuild schreiben: `WEGPIRATEN_DST=sandbox/wegpiraten_datenbank_final.xlsx`,
   `WEGPIRATEN_HAND=sandbox/wegpiraten_datenbank_neu.xlsx`. Der Testbuild bleibt als Vergleich
   unverändert liegen.
2. **Folgeaufträge.** In `prepare.py`, `FOLLOW_UPS`, nur die drei von Wegpiraten bestätigten
   (C1024, C1068, C1082), keine neuen.
   - C1024: Der Vorgänger behält die Nummer aus dem Stand 02.09. (250911003), der Nachfolger bekommt
     die aus der Quelle (260918020). Dafür ein Feld `old_application_number`; heute kopiert
     `apply_follow_ups` die Quellnummer auf beide. Das ist ein Fehler des Builds, keine Datenpflege.
   - Alles Weitere (doppelte Nummern bei C1068/C1082, Verlängerungsmuster bei C1000/C1065, C1011,
     C1015) bleibt, wie es ist, und steht als Befund in der Liste aus Schritt 7.
3. **Nummern.** `mandate_numbers.json` nicht neu schreiben lassen, sondern nur ergänzen (das tut
   `build_mandate_numbers` bereits). Erwartet: C1089 bis C1091 und jeder neue Folgeauftrag bekommen
   die nächsten Zähler ab `A26047`, nach Beginn und alter Klientennummer. Die 91 bestehenden Nummern
   bleiben gleich; das wird im Log mit einem Vergleich vorher/nachher belegt.
4. **Handarbeit.** `carry_over_handwork` übernimmt Rolle und Berichte unverändert. **Die Familie
   wird nicht übernommen**: Die Einträge im Testbuild (Nipote, Stauffer, Perren, Burri) waren zu
   Demo-Zwecken gesetzt, und Familien definiert der Kunde (Stephan, 2026-10-09). Dafür in
   `carry_over_handwork` die Übernahme von `family_id` abschalten (Schalter, nicht löschen); das Feld
   bleibt leer, wie nach der ersten Migration.
   - Neue Zuordnungen ohne Rolle: ist die Person die einzige am Auftrag, P (wie bisher); sonst leer
     lassen, die Prüfung «Auftrag ohne primäre Betreuungsperson» markiert es.
   - Berichte, deren Auftrag es nicht mehr gibt, melden; es darf keiner verloren gehen. Erwartet:
     153 Berichte, alle zugeordnet.
5. **Schreibweisen** werden nicht angeglichen. Die Prüfung «Schreibweise eines Codewerts» markiert sie.
6. **Build und Prüfung.** `verify_excel_strict` muss bestehen. Danach in LibreOffice neu berechnen
   und die gecachten Werte lesen (der Import liest `data_only=True`).
7. **Differenz belegen.** Für jedes editierbare Feld der Blätter Kinder, Aufträge, Betreuungen,
   Ansprechpersonen und Zuordnung MA: finaler Build gegen Testbuild. Jede Abweichung muss durch die
   Liste «Was sich geändert hat» oder einen Entscheid aus DM-02 erklärt sein. Eine unerklärte
   Abweichung heisst, dass im Testbuild von Hand etwas korrigiert wurde, das der Build nicht kennt:
   auflisten; Stephan entscheidet, ob die Korrektur in den Build gehört (dann wie Schritt 2) oder
   als Befund bleibt.
8. **Zählung, Prüfstand und Befundliste:** Kinder, Aufträge, Betreuungen, Zuordnungen, Berichte,
   Familien (erwartet: 0) ins Log; Blatt «Prüfungen» mit Anzahl je Prüfung, verglichen mit dem Stand im Testbuild
   (4 Fehlerarten, 8 Hinweisarten am 30.09.). Die Befunde aus `dm02_fachfragen.md`, Gruppe B, mit dem
   Stand nach dem Build nachführen; die Liste geht mit dem Workbook an Wegpiraten.

## Abnahme

- Die 91 eingefrorenen Nummern sind unverändert, neue Nummern beginnen bei `A26047`.
- Kein Kind trägt eine Familie.
- 153 Berichte übernommen, Rollen aller Paare aus dem Testbuild übernommen, die noch existieren.
- Jede Abweichung zum Testbuild ist erklärt (Schritt 7).
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
