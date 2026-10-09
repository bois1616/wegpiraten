# DM-02: Offene Fachfragen, sortiert

Stand 2026-10-09, `[Opus 5.5]`. Ergebnis der Aufgabe DM-02 im
[Backlog](backlog_umstellung_datenmodell.md). Quellen: Konzept («Was offen ist»), Datenmodell
(«Open questions»), die Klärungsdateien vom 24./25.09., der Vergleich der eingefrorenen alten Datei
(09.10.) mit der Quelle des Testbuilds (24.09.) und das Blatt «Prüfungen» in
`wegpiraten_datenbank_neu.xlsx` (Stand 30.09.).

Kinder und Aufträge stehen mit Nummer. Die Klientennummer `C…` ist die alte Nummer, die Auftragsnummer
`A…` die des Testbuilds (eingefroren in `mandate_numbers.json`).

Grundsatz (Stephan, 2026-10-09): **Datenpflege ist nicht Aufgabe der Umstellung.** Inkonsistenzen in
den Daten werden benannt und markiert, aber nicht korrigiert, und sie blockieren nichts. Blockieren
kann nur eine Regel, die die Programme brauchen und die nur Wegpiraten festlegen kann.

Drei Gruppen:

- **A: Regeln für die Programme.** Ohne Antwort gilt der Vorschlag; die Frage blockiert nur, wenn
  der Vorschlag falsch wäre und das erst nach dem Versand auffällt.
- **B: Datenbefunde.** Benannt und im Workbook markiert, gehen als Liste mit dem Workbook an
  Wegpiraten. Blockieren nichts. Wo ein Befund eine Rechnung betrifft, markieren die Programme sie
  (DM-16), statt sie anzuhalten.
- **C: kann warten.** Betrifft Berichte oder spätere Auswertungen.

## A: Regeln für die Programme

| # | Frage | Warum wichtig | Vorschlag, gilt bis zur Antwort |
| --- | --- | --- | --- |
| A1 | ~~KOB an Accordix melden?~~ **Entschieden 2026-10-09 (Stephan): Meldepflichtig ist ein Auftrag über den Kostenträger, nicht über die Leistungsart. P1000 (KJA-FS) ist meldepflichtig, alle anderen bisher nicht.** | KOB läuft heute nur auf einem Auftrag eines anderen Kostenträgers und fällt damit von selbst heraus. Neu ist: auch SPF und UWB anderer Kostenträger (19 Aufträge in der alten Datei) werden nicht gemeldet. | — |
| A2 | ~~Einführungsgespräch (ST99)~~ **Entschieden 2026-10-09 (Stephan): Die 15 Minuten gibt es einmalig, nicht pro Monat und nicht pro Auftrag.** | Umsetzung: einmal je Kind, im Monat des Eintritts seiner ersten ST99-Betreuung; Verlängerungen lösen es nicht erneut aus (DM-03). | — |
| A3 | **Ankündigung der neuen Rechnungsnummern.** Ab Oktober `2026-10-A26001` statt `2026-10-C1002`. Muss das KJA-FS oder eine KESB vorher informiert werden, oder prüft jemand die Nummer maschinell? | Ein Upload, der an der Nummer scheitert, fällt erst beim Versand auf. | Kurze Mitteilung an KJA-FS vor dem Lauf, Stephan entscheidet. |

## B: Datenbefunde

Nachzuführen nach dem finalen Build (DM-05, Schritt 8). «Markiert» heisst: Das Workbook zeigt den
Befund im Blatt «Prüfungen»; wo nicht, steht es in der Spalte.

| # | Befund | Markiert | Wirkung, solange er offen ist |
| --- | --- | --- | --- |
| B1 | **Nipote:** im Testbuild eine Familie (C1002, C1068), laut Klärung vom 24.09. nach Wegpiraten zwei | nein, die Daten sind formal gültig; steht in dieser Liste | C1068 ist Indexkind auch des Auftrags von C1002: dessen Rechnung trägt Name und AHV-Nummer von C1068 |
| B2 | Folgeaufträge von C1068 und C1082 tragen die Geschäftsnummer des Vorgängers | ja, «kommt mehrfach vor» | zwei Rechnungen mit derselben Nummer im Dateinamen; die Programme markieren sie |
| B3 | C1000 (neue Geschäftsnummer) und C1065 (neues Ende) seit 24.09. geändert wie eine überschriebene Verlängerung; C1011, C1015 ebenso (seit 25.09. offen) | nein; steht in dieser Liste | Kette und altes Kontingent fehlen; Rechnung läuft auf dem bestehenden Auftrag |
| B4 | 14 KJA-Aufträge mit «beendet» oder «on hold» statt Geschäftsnummer: A24008, A24009, A24011, A24012, A24015, A24016, A25006, A25009, A25010, A25019, A26004, A26006, A26009 (on hold), A26010 | ja | beendete Aufträge ohne Rechnung, ausser A26009 |
| B5 | C1091 (neu seit 24.09.) ohne Geschäftsnummer | ja | Rechnung mit «PRÜFEN» im Dateinamen, wie heute schon |
| B6 | Stauffer: C1079 ohne Geburtsdatum trotz Familie; C1079 und C1083 mit derselben AHV-Nummer | ja | Indexkind nicht bestimmbar (die Programme markieren den Auftrag) |
| B7 | Familie bei C1035 (Perren) und C1050 (Burri) mit nur einem Kind | ja, Hinweis | keine |
| B8 | 13 Austritte ohne Grund, 7 betreute Kinder ohne Accordix-Pflichtfeld, 16 Codewerte in abweichender Schreibweise | ja | Accordix kann die Zeilen ablehnen |
| B9 | 9 Aufträge mit abgelaufener Bewilligung und offener Betreuung, 23 Zuordnungen auf ausgelaufene Aufträge | ja | auf ausgelaufene Aufträge entsteht kein Bogen (DM-20); das wird gemeldet |
| B10 | Zuordnungen, die seit 24.09. neu sind und mehr als eine Person am Auftrag haben, ohne Rolle P/S | ja, «ohne primäre Betreuungsperson» | Berichte ohne zuständige Person |

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

Antworten aus A gehen in die Programme (DM-03, DM-40, DM-31) und werden in
[dm04_build_spezifikation.md](dm04_build_spezifikation.md), Abschnitt «Entscheide aus DM-02»,
festgehalten. Die Liste B geht mit dem Workbook an Wegpiraten, die die Daten selbst pflegen. C wird
nach der Umstellung aufgenommen.
