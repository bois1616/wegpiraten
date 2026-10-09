# DM-04: Spezifikation für den finalen Build

Stand 2026-10-09, `[Opus 5.5]`. Vorgabe für DM-05 (`[Sonnet]`). Ergebnis ist das Workbook, das
Wegpiraten Ende Oktober bekommt; danach ist das Workbook beim Kunden die einzige Quelle.

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
| Kinder (Familie) | Testbuild, korrigiert nach DM-02 A1 und B4 | `carry_over_handwork` |
| Berichte (ganzes Blatt) | Testbuild | `carry_over_handwork` |
| Stammdaten (Kostenträger, Leistungsbesteller, Leistungstypen, Mitarbeiter, Büros, Hilfsdaten, Wertelisten) | alte Datei 09.10. | wie im Testbuild |

## Schritte für DM-05

Jeder Schritt ist für sich stabil; bricht die Sitzung ab, gilt der letzte im Log vermerkte.

1. **Pfade.** `migrate.py` und `build.py`: `SRC` auf `wegpiraten_datenbank.xlsx`. Den Build nicht über
   den Testbuild schreiben: `WEGPIRATEN_DST=sandbox/wegpiraten_datenbank_final.xlsx`,
   `WEGPIRATEN_HAND=sandbox/wegpiraten_datenbank_neu.xlsx`. Der Testbuild bleibt als Vergleich
   unverändert liegen.
2. **Folgeaufträge.** In `prepare.py`, `FOLLOW_UPS`:
   - C1024: Der Vorgänger behält die Nummer aus dem Stand 02.09. (250911003), der Nachfolger bekommt
     die aus der Quelle (260918020). Dafür ein Feld `old_application_number`; heute kopiert
     `apply_follow_ups` die Quellnummer auf beide, was seit dem 09.10. falsch ist.
   - C1068, C1082: neue Geschäftsnummer des Nachfolgers nach DM-02 A2; ohne Antwort unverändert
     (der Fehler bleibt sichtbar).
   - C1000, C1065: nach DM-02 A3. Bei «Folgeauftrag» je ein Eintrag mit `old_end` (C1065: 31.08.2026)
     bzw. `old_application_number` (C1000: 260401001) und dem alten Ende; bei «Korrektur» nichts.
   - C1011, C1015: nach DM-02 A4; ohne Antwort nichts.
3. **Nummern.** `mandate_numbers.json` nicht neu schreiben lassen, sondern nur ergänzen (das tut
   `build_mandate_numbers` bereits). Erwartet: C1089 bis C1091 und jeder neue Folgeauftrag bekommen
   die nächsten Zähler ab `A26047`, nach Beginn und alter Klientennummer. Die 91 bestehenden Nummern
   bleiben gleich; das wird im Log mit einem Vergleich vorher/nachher belegt.
4. **Handarbeit.** `carry_over_handwork` übernimmt Familie, Rolle und Berichte. Danach:
   - Familie nach DM-02 A1 (Nipote) und B4 (Perren, Burri leeren) setzen. Das ist eine Korrektur der
     Handarbeit, also im Testbuild selbst vor dem Build oder als dokumentierte Ausnahme im Build,
     nicht stillschweigend.
   - Neue Zuordnungen ohne Rolle: ist die Person die einzige am Auftrag, P (wie bisher); sonst leer
     lassen und in die Liste für DM-02 B7.
   - Berichte, deren Auftrag es nicht mehr gibt, melden; es darf keiner verloren gehen. Erwartet:
     153 Berichte, alle zugeordnet.
5. **Schreibweisen.** Die 16 Codewerte mit abweichender Schreibweise (Invariante 18) dort angleichen,
   wo der Wert der Werteliste bis auf Gross- und Kleinschreibung gleich ist. Alles andere bleibt und
   steht als Hinweis im Workbook.
6. **Build und Prüfung.** `verify_excel_strict` muss bestehen. Danach in LibreOffice neu berechnen
   und die gecachten Werte lesen (der Import liest `data_only=True`).
7. **Differenz belegen.** Für jedes editierbare Feld der Blätter Kinder, Aufträge, Betreuungen,
   Ansprechpersonen und Zuordnung MA: finaler Build gegen Testbuild. Jede Abweichung muss durch die
   Liste «Was sich geändert hat» oder einen Entscheid aus DM-02 erklärt sein. Eine unerklärte
   Abweichung heisst, dass im Testbuild von Hand etwas korrigiert wurde, das der Build nicht kennt:
   auflisten und vor der Übergabe entscheiden, nicht überschreiben.
8. **Zählung und Prüfstand ins Log:** Kinder, Aufträge, Betreuungen, Zuordnungen, Berichte, Familien;
   Blatt «Prüfungen» mit Anzahl je Prüfung, verglichen mit dem Stand im Testbuild (4 Fehlerarten,
   8 Hinweisarten am 30.09.).

## Abnahme

- Die 91 eingefrorenen Nummern sind unverändert, neue Nummern beginnen bei `A26047`.
- 153 Berichte übernommen, Rollen aller Paare aus dem Testbuild übernommen, die noch existieren.
- Jede Abweichung zum Testbuild ist erklärt (Schritt 7).
- Fehler im Blatt «Prüfungen» sind nur solche aus DM-02 B oder unbeantwortete Fragen aus DM-02 A.
- Danach DM-06 (Excel unter Windows) durch Stephan.

## Entscheide aus DM-02

Hier trägt ein, wer die Antworten aus [dm02_fachfragen.md](dm02_fachfragen.md) erhält: Nummer, Antwort,
Datum, von wem. Bis dahin gelten die Vorschläge dort.

| # | Antwort | Datum | Quelle |
| --- | --- | --- | --- |
