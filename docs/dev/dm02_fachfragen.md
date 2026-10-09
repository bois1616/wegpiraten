# DM-02: Offene Fachfragen, sortiert

Stand 2026-10-09, `[Opus 5.5]`. Ergebnis der Aufgabe DM-02 im
[Backlog](backlog_umstellung_datenmodell.md). Quellen: Konzept («Was offen ist»), Datenmodell
(«Open questions»), die Klärungsdateien vom 24./25.09., der Vergleich der eingefrorenen alten Datei
(09.10.) mit der Quelle des Testbuilds (24.09.) und das Blatt «Prüfungen» in
`wegpiraten_datenbank_neu.xlsx` (Stand 30.09.).

Kinder und Aufträge stehen mit Nummer. Die Klientennummer `C…` ist die alte Nummer, die Auftragsnummer
`A…` die des Testbuilds (eingefroren in `mandate_numbers.json`).

Drei Gruppen:

- **A: blockiert den finalen Build oder die Oktober-Abrechnung.** Ohne Antwort wird das Workbook
  falsch oder eine Rechnung geht falsch hinaus. Frist: vor DM-05.
- **B: Datenfehler, die Wegpiraten bis Ende Oktober korrigiert** (DM-60). Kein Entscheid nötig, nur
  die richtige Angabe. Sie dürfen im übergebenen Workbook als Fehler stehen, müssen aber vor der
  Oktober-Abrechnung weg sein, soweit sie Rechnungen betreffen.
- **C: kann warten.** Betrifft Berichte oder spätere Auswertungen, nicht Rechnung, Bögen oder Accordix.

## A: blockierend

| # | Frage | Warum blockierend | Vorschlag, wenn keine Antwort kommt |
| --- | --- | --- | --- |
| A1 | **Nipote: eine Familie oder zwei?** Im neuen Workbook tragen C1002 und C1068 die Familie «nipote». Laut Klärung vom 24.09. sind es nach Wegpiraten zwei Familien. | Mit Familie ist C1068 (geb. 2026) Indexkind beider Aufträge: Name und AHV-Nummer auf der Rechnung von C1002s Auftrag wechseln, und Invariante 28 ändert sich. | Zwei Familien (Feld leeren), weil das die letzte Aussage von Wegpiraten ist. |
| A2 | **Geschäftsnummer der Folgeaufträge C1068 und C1082.** Die Nachfolger A26042 und A26046 haben die Nummer des Vorgängers geerbt (Prüfung «kommt mehrfach vor»). Bei C1024 hat Wegpiraten inzwischen die neue Nummer eingetragen (260918020). | Die Geschäftsnummer steht im Dateinamen der Rechnung und ist beim KJA-FS-Upload der Schlüssel. Doppelt heisst: zwei Rechnungen auf denselben Antrag. | Ohne neue Nummer bleibt die Prüfung rot, Oktober-Rechnungen dieser Aufträge werden zurückgehalten. |
| A3 | **C1000 und C1065: Verlängerung oder Korrektur?** C1000 hat seit 24.09. eine neue Geschäftsnummer (260401001 → 260916002) bei gleichem Ende. C1065 hat ein neues Ende (31.08.2026 → 30.04.2027). Beides ist das Muster einer überschriebenen Verlängerung. | Bei einer Verlängerung braucht es einen Folgeauftrag, sonst geht der alte Auftrag in der Kette verloren und die Oktober-Rechnung läuft auf der falschen Nummer. | Als Folgeauftrag anlegen wie C1024/C1068/C1082: Vorgänger endet mit dem alten Ende, Nachfolger beginnt am Tag danach, Kontingent unverändert. |
| A4 | **Duarte Torres (C1011) und Loosli (C1015): wann endete der alte Auftrag?** Beide haben eine neue Geschäftsnummer bei gleichem Ende. Offen seit 25.09. | Wie A3. Ohne Datum kann kein Folgeauftrag angelegt werden. | Nur Nummernkorrektur annehmen (kein Folgeauftrag), im Auftrag vermerken. Das ist die Annahme, die im Testbuild schon gilt. |
| A5 | **KOB (`ST09`) an Accordix melden?** Kindorientierte Beratung läuft auf echten Aufträgen und hat keine Accordix-Zuordnung (eine der drei Hinweise «Leistungsart ohne Accordix-Zuordnung»). | Betrifft die Accordix-Meldung, nicht die Rechnung. Blockierend nur, wenn eine Meldung vor dem Oktober-Lauf fällig ist. | Nicht melden (auf die Ausschlussliste), bis Wegpiraten eine Accordix-Leistungsart nennt. |
| A6 | **Einführungsgespräch (ST99):** Gelten die 15 Gratisminuten im Monat des Eintritts des Kindes oder im Startmonat jedes Auftrags? (DM-03) | Die Regel liest heute das Startdatum des Klienten. Im neuen Modell hätte jede Verlängerung ein neues Startdatum. | Monat des Eintritts (bleibt bei Verlängerungen gleich), also einmal pro Kind und Betreuung. |
| A7 | **Ankündigung der neuen Rechnungsnummern.** Ab der Oktober-Abrechnung lautet die Nummer `2026-10-A26001` statt `2026-10-C1002`. Muss das KJA-FS oder eine KESB vorher informiert werden, oder prüft jemand die Nummer maschinell? | Ein Upload, der an einer unerwarteten Nummer scheitert, fällt erst beim Versand auf. | Kurze Mitteilung an KJA-FS vor dem Lauf, Stephan entscheidet. |

## B: Datenfehler (DM-60)

| # | Befund | Betrifft | Was Wegpiraten liefert |
| --- | --- | --- | --- |
| B1 | 14 KJA-Aufträge mit «beendet» oder «on hold» statt Geschäftsnummer: A24008, A24009, A24011, A24012, A24015, A24016, A25006, A25009, A25010, A25019, A26004, A26006, A26009 (on hold), A26010 | Nur beendete Aufträge, ausser A26009: der ist zu prüfen | die ursprüngliche Nummer; wo sie nicht mehr auffindbar ist, bleibt der Fehler bewusst stehen |
| B2 | C1091 (neu seit 24.09.) ohne Geschäftsnummer | Rechnung ab Oktober | die Nummer |
| B3 | Stauffer: C1079 hat kein Geburtsdatum, obwohl eine Familie eingetragen ist (Fehler, Indexkind nicht bestimmbar); C1079 und C1083 tragen dieselbe AHV-Nummer | Rechnung C1079, Accordix | Geburtsdatum und richtige AHV-Nummer |
| B4 | Familie bei C1035 (Perren) und C1050 (Burri) mit nur einem Kind | keine Wirkung, aber irreführend | nichts; Feld wird geleert (zwei Aufträge eines Kindes brauchen keine Familie) |
| B5 | 13 Austritte ohne Austrittsgrund, 7 betreute Kinder ohne Accordix-Pflichtfeld, 16 Codewerte in abweichender Schreibweise | Accordix | die Angaben; die Schreibweise korrigiert der Build, wo sie eindeutig ist (DM-04) |
| B6 | 9 Aufträge mit abgelaufener Bewilligung und offener Betreuung, 23 Zuordnungen auf ausgelaufene Aufträge | Bogenerzeugung November | Austritt eintragen oder Verlängerung melden; Zuordnungen entfernen |
| B7 | Rollen P/S: im neuen Workbook gesetzt (85 P, 16 S), aber seit 24.09. haben sich Zuordnungen geändert (DM-04, Abschnitt «Zuordnung MA») | Berichtspflicht | Rolle für die neuen Zuordnungen bestätigen |

## C: kann warten

- Bericht und Zwischenbericht: worin unterscheiden sie sich (Datenmodell, Frage 11)?
- Abschlussbericht für jeden Auftrag einer Kette oder nur den letzten (Frage 13)?
- Berichtsrhythmen beim Leistungsbesteller statt am Auftrag (Frage 12)?
- Erledigt-Stand der 64 vergangenen Berichte (Frage 14). Vorschlag: auf «entfällt» setzen, wer
  einen Bericht als erledigt kennt, trägt ihn nach.
- Die 48 Abweichungen zwischen Mitarbeiterblättern und Klientenübersicht
  (`klaerung_berichte_2026-09-25.md`): betreffen die Berichtsliste, nicht die Stammdaten. Wo dort ein
  anderes Ende oder ein anderer Besteller steht, ist eher die Übersicht veraltet; die Stammdaten
  gelten.
- Notation der Geschäftsnummern anderer Kostenträger, KESB `yyyy-nnnn` (Frage 10).
- Filtern der Vorgänger-Auswahl nach Kind und Leistungsart (Datenmodell, «Excel-specific decisions»).

## Was mit den Antworten passiert

Antworten aus A fliessen in die Build-Spezifikation ([dm04_build_spezifikation.md](dm04_build_spezifikation.md),
Abschnitt «Entscheide aus DM-02»), dann baut DM-05. Antworten aus B trägt Wegpiraten im übergebenen
Workbook selbst ein; was bis dahin schon bekannt ist, setzt der Build. C wird nach der Umstellung
aufgenommen.
