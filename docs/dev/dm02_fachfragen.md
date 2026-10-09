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
| A3 | ~~Ankündigung der neuen Rechnungsnummern~~ **Entschieden 2026-10-09 (Stephan): Kein Kostenträger, auch das KJA nicht, muss über den geänderten Nummernkreis informiert werden.** | — | — |

## B: Datenbefunde

Alle Befunde sind Datenpflege und Sache von Wegpiraten (Stephan, 2026-10-09). Der finale Build übernimmt nur die Daten der originalen Datenbank; alles, was der Testbuild darüber hinaus enthielt, war Demo. Nachzuführen nach dem
finalen Build (DM-05, Schritt 8). «Markiert» heisst: Das Workbook zeigt den Befund im Blatt
«Prüfungen»; wo nicht, steht es in der Spalte.

| # | Befund | Markiert | Wirkung, solange er offen ist |
| --- | --- | --- | --- |
| B1 | **Familien:** keine erfasst. Die Einträge im Testbuild (u.a. Nipote) waren Demo; Familien definiert der Kunde in der initialen und laufenden Datenpflege. | nein (leer ist gültig) | jedes Kind ist sein eigenes Indexkind, wie im alten Modell |
| B2 | **Folgeaufträge C1024, C1068, C1082:** übernommen, Vorgängerwerte aus dem Stand 02.09.; Nachfolger von C1068 und C1082 tragen die Geschäftsnummer des Vorgängers | ja, «zu prüfen» und «kommt mehrfach vor» | zwei Rechnungen mit derselben Geschäftsnummer im Dateinamen |
| B3 | C1000 (neue Geschäftsnummer) und C1065 (neues Ende) seit 24.09. geändert wie eine überschriebene Verlängerung; C1011, C1015 ebenso (seit 25.09. offen) | nein; steht in dieser Liste | Kette und altes Kontingent fehlen; Rechnung läuft auf dem bestehenden Auftrag |
| B4 | 14 KJA-Aufträge mit «beendet» oder «on hold» statt Geschäftsnummer: A24008, A24009, A24011, A24012, A24015, A24016, A25006, A25009, A25010, A25019, A26004, A26006, A26009 (on hold), A26010 | ja | Rechnungen sind nicht Teil der Stammdaten; ob auf diesen Aufträgen noch Stunden anfallen, zeigen erst die Bögen. Fällt eine Rechnung an, steht der Text statt einer Nummer im Dateinamen (korrigiert 2026-10-09: «ohne Rechnung» war eine Annahme, keine Prüfung) |
| B5 | C1091 (neu seit 24.09.) ohne Geschäftsnummer | ja | Rechnung mit «PRÜFEN» im Dateinamen, wie heute schon |
| B6 | Stauffer: C1079 und C1083 mit derselben AHV-Nummer; C1079 ohne Geburtsdatum | ja | Accordix-Pflichtfeld fehlt bei C1079 |
| B7 | *(entfällt: die Familien bei Perren und Burri waren Demo)* | — | — |
| B8 | 13 Austritte ohne Grund, 7 betreute Kinder ohne Accordix-Pflichtfeld, 16 Codewerte in abweichender Schreibweise | ja | Accordix kann die Zeilen ablehnen |
| B9 | 9 Aufträge mit abgelaufener Bewilligung und offener Betreuung, 23 Zuordnungen auf ausgelaufene Aufträge | ja | auf ausgelaufene Aufträge entsteht kein Bogen (DM-20); das wird gemeldet |
| B10 | Rollen P/S: im Testbuild nur ein best guess (Stephan, 2026-10-09). Der finale Build setzt P nur bei Aufträgen mit genau einer Person; bei allen anderen fehlt die Rolle | ja, «ohne primäre Betreuungsperson» | Berichte dieser Aufträge ohne zuständige Person |

## C: entschieden oder zurückgestellt (Stephan, 2026-10-09)

- **Bericht und Zwischenbericht:** nur Text ohne Semantik, eine Erinnerung für den Monat.
- **Abschlussbericht:** nur für den letzten Auftrag einer Kette. Ein Abschlussbericht auf einem
  Auftrag mit Nachfolger ist damit ein Datenbefund; das Workbook soll ihn markieren (DM-63).
- **Berichtsrhythmen:** zurückgestellt. Termine werden zunächst von Hand eingetragen; wenn ein
  Rhythmus kommt, eher am Auftrag.
- **Status vergangener Berichte:** bleibt leer, so in Ordnung.
- **Notation der Geschäftsnummern anderer Kostenträger:** vorläufig nicht prüfen.
- **Filtern der Vorgänger-Auswahl:** später zu klären.
- **Berichtsliste:** die 153 Berichte aus der Klientenübersicht werden übernommen und als «zu prüfen»
  markiert (Korrektur Stephan, 2026-10-09). Die 48 Abweichungen in `klaerung_berichte_2026-09-25.md`
  gehören zu dieser Prüfung und gehen mit der Befundliste an Wegpiraten.

## Was mit den Antworten passiert

Antworten aus A gehen in die Programme (DM-03, DM-40, DM-31) und werden in
[dm04_build_spezifikation.md](dm04_build_spezifikation.md), Abschnitt «Entscheide aus DM-02»,
festgehalten. Die Liste B geht mit dem Workbook an Wegpiraten, die die Daten selbst pflegen. C wird
nach der Umstellung aufgenommen.
