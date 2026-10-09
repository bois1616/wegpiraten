# Umsetzungslog: Umstellung auf Kinder, Aufträge und Betreuungen

Begleitet das [Backlog](backlog_umstellung_datenmodell.md). Muster wie
[umsetzungslog.md](../../umsetzungslog.md): neueste Einträge zuerst, ein Abschnitt je Tag.

## Übergabe

Diesen Abschnitt liest jedes Modell zuerst und überschreibt ihn am Ende jeder Sitzung. Er ist der
einzige Ort, der den aktuellen Stand trägt; die Einträge darunter sind die Begründung dafür.

- **Branch:** `feature/datamodel-v2` (ab `e960512`, gepusht); Fallback `backup/pre-datamodel-v2` und Tag `pre-datamodel-v2` (beide `e960512`, gepusht); `main` = `e960512`
- **Fristen:** Ende Oktober 2026 neues Workbook bei Wegpiraten, Unklarheiten benannt, Datenbefunde markiert; Anfang November Oktober-Abrechnung mit dem neuen Schema
- **Zuletzt erledigt:** DM-02 A1 bis A3 entschieden (Accordix nach Kostenträger, Einführungsgespräch einmalig), DM-03 erledigt
- **In Arbeit:** nichts
- **Nächster Schritt:** DM-05 `[Sonnet]` nach `docs/dev/dm04_build_spezifikation.md` (hängt an keiner Antwort); parallel DM-10 `[Haiku]`
- **Wartet auf Stephan:** nichts
- **Entwürfe ohne Opus-Review:** keine
- **Prüfstand:** `nox` zuletzt nicht gelaufen (keine Codeänderung)

- **Grundsatz Daten:** Datenpflege ist nicht Aufgabe der Umstellung; Inkonsistenzen benennen und markieren, nicht korrigieren, nicht blockieren (Stephan, 2026-10-09)

## Eintragsvorlage

```markdown
- **DM-nn Kurztitel** `[Modell]` (Status: erledigt | Teil erledigt | Entwurf, Opus-Review offen | abgebrochen):
  Was geändert wurde, mit Dateien. Entscheidungen und warum. Prüfung: Befehl und Ergebnis
  (z.B. `nox`: 0 Fehler, `pytest`: 14/14). Offen: was der Nächste wissen muss.
```

Regeln:

- Das Modell steht in jedem Eintrag, damit sichtbar ist, welche Stufe eine Entscheidung getroffen hat.
- Spezifikationen aus `[Opus]`-Aufgaben stehen vollständig im Eintrag oder als eigene Datei unter
  `docs/dev/`, auf die der Eintrag verweist. Eine Spezifikation, die nur im Chat stand, gibt es nicht.
- Prüfergebnisse werden zusammengefasst (Anzahl bestanden, Namen der Fehlschläge), keine
  Rohausgaben.
- Keine Personendaten im Log. Aufträge und Kinder mit Nummer nennen, Namen nur, wo das Konzept
  sie schon als Beispiel führt.

## 2026-10-09

- **Nur Originaldaten** `[Opus 5.5]` (Status: erledigt): Stephan: relevant sind nur die Daten aus
  der originalen Datenbank, alle Ergänzungen im Testbuild sind Demo. DM-04 neu gefasst: keine
  Übernahme aus dem Testbuild (`WEGPIRATEN_HAND` ins Leere, kein Berichts-Seed), `FOLLOW_UPS`
  leer (die drei bestätigten Folgeaufträge legt Wegpiraten als Datenpflege an, Befund B2), Berichte
  und Familien leer, Rolle P nur wo eindeutig. Neue Abnahme: Vollständigkeit gegen das Original
  (Schritt 7) statt Differenz zum Testbuild. Die Nummern A26042, A26045, A26046 bleiben unbenutzt.
  Damit wird `import_reports.py` gegenstandslos (DM-07).

- **Rollen P/S neu setzen** `[Opus 5.5]` (Status: erledigt): Stephan: Die Rollen im Testbuild
  waren ein best guess, Datenpflege. Der finale Build übernimmt sie nicht, sondern setzt P nur, wo
  genau eine Person am Auftrag arbeitet (DM-04 Schritt 4, Befund B10). Aus dem Testbuild kommen
  damit nur noch die Berichte.

- **DM-02 Gruppe B und C beantwortet** `[Opus 5.5]` (Status: erledigt): Stephan: B1 bis B10 sind
  Datenpflege bei Wegpiraten. Die Familie Nipote im Testbuild war ein Demo-Eintrag; Familien
  definiert der Kunde. Folge: Der finale Build übernimmt keine Familien aus dem Testbuild
  (DM-04 Schritt 4, Schalter in `carry_over_handwork`). B4 korrigiert: «ohne Rechnung» war meine
  Annahme, Rechnungen sind nicht Teil der Stammdaten. Gruppe C: Bericht/Zwischenbericht nur Text,
  Abschlussbericht nur am letzten Auftrag einer Kette (neue Prüfung DM-63, P1), Rhythmen
  zurückgestellt, Status vergangener Berichte bleibt leer, Notation anderer Kostenträger wird nicht
  geprüft, Vorgänger-Filter später. Datenmodell, Fragen 10 bis 14, nachgeführt. Rollen P/S: siehe nächster Eintrag.

- **DM-02 A3 entschieden** `[Opus 5.5]` (Status: erledigt): Stephan: kein Kostenträger, auch das
  KJA nicht, muss über den geänderten Nummernkreis der Rechnungen informiert werden. Damit ist
  DM-02 Gruppe A vollständig entschieden.

- **DM-02 A1 und A2 entschieden, DM-03 erledigt** `[Opus 5.5]` (Status: erledigt): Stephan:
  Accordix-Pflicht hängt am Kostenträger, P1000 ja, andere bisher nein; das Einführungsgespräch
  gibt es einmalig, nicht pro Monat. Geprüft an der alten Datei: KOB läuft nur auf einem Auftrag
  eines anderen Kostenträgers, fällt also heraus; 19 SPF/UWB-Aufträge anderer Kostenträger werden
  künftig ebenfalls nicht gemeldet. Eingetragen in `dm02_fachfragen.md`, `dm04_build_spezifikation.md`
  («Entscheide aus DM-02») und im Backlog bei DM-03, DM-40, DM-41. Prüfung: keine Codeänderung.

- **Grundsatz «markieren statt pflegen» eingearbeitet** `[Opus 5.5]` (Status: erledigt): Stephan:
  Datenpflege ist nicht Aufgabe der Umstellung, Inkonsistenzen werden benannt und markiert und
  blockieren nichts. Folgen: DM-02 neu gruppiert (A nur noch drei Regeln für die Programme, die
  bisherigen Datenfragen Nipote, doppelte Nummern, Verlängerungsmuster sind jetzt Befunde B1 bis B3);
  DM-04 übernimmt die Daten unverändert, keine neuen Folgeaufträge, keine Korrektur von Familien oder
  Schreibweisen, einzige Codekorrektur bleibt die Geschäftsnummer des Vorgängers bei C1024 (ein Fehler
  von `apply_follow_ups`, keine Datenpflege); DM-16 hält beim Import nicht mehr an, sondern schreibt
  eine Befundliste und markiert betroffene Rechnungen nach dem Muster `PRÜFEN`; DM-60 ist jetzt die
  Übergabe der Befundliste, nicht die Bereinigung.

- **DM-02 Fachfragen sortiert, DM-04 Build spezifiziert** `[Opus 5.5]` (Status: erledigt):
  `docs/dev/dm02_fachfragen.md` und `docs/dev/dm04_build_spezifikation.md`. Grundlage: Vergleich
  der eingefrorenen alten Datei (09.10.) mit dem Blatt «Klienten (alt)» des Testbuilds (Stand der
  Quelle 24.09.) und Auswertung des Blatts «Prüfungen» im Testbuild. Befunde, die über die bekannten
  offenen Fragen hinausgehen: (1) Im Testbuild ist Nipote als eine Familie erfasst, laut Klärung
  vom 24.09. sind es zwei (A1). (2) Die Folgeaufträge haben die Geschäftsnummer des Vorgängers
  geerbt; bei C1024 hat Wegpiraten inzwischen die neue Nummer eingetragen, und `apply_follow_ups`
  würde sie jetzt auch dem Vorgänger geben (DM-04 Schritt 2). (3) C1000 und C1065 zeigen seit dem
  24.09. das Muster einer überschriebenen Verlängerung (A3). (4) Perren und Burri tragen eine
  Familie mit nur einem Kind (B4). (5) Drei neue Klienten C1089 bis C1091, nächste freie
  Auftragsnummer `A26047`. Prüfung: keine Codeänderung. Offen: Antworten zu Gruppe A.

- **DM-00 abgeschlossen** `[Opus 5.5]` (Status: erledigt): Mit Stephans Freigabe `main` per
  Fast-Forward auf `e960512` (`fix/sa-sentinel-client`) gezogen, `main`, Tag `pre-datamodel-v2`,
  `backup/pre-datamodel-v2` und `feature/datamodel-v2` gepusht. Neue Regel (Stephan): nur beginnen,
  was im laufenden Kontingent fertig wird, stabile Zwischenergebnisse; im Backlog unter
  «Regeln für den Modellwechsel» und in AGENTS.md.

- **Plan nach Stephans Antworten nachgeführt** `[Opus 5.5]` (Status: erledigt):
  (1) Ausnahme von «Betriebsstabilität» bestätigt, in AGENTS.md eingetragen, dort auch der Einstieg
  für Modelle, die CLAUDE.md nicht lesen (DM-01 erledigt). Fallback-Branch
  `backup/pre-datamodel-v2` lokal angelegt.
  (2) Modellklassen: GPT-6 Astra = Opus, GPT-6.1 Sol = Sonnet, GPT-6 Luna = Haiku bestätigt (nach
  OpenAIs eigener Staffelung). Kimi K3 = Sonnet; auf Opus-Aufgaben nur als Entwurf, bis eine
  davon ein Opus-Review bestanden hat. Tabelle im Backlog, Abschnitt «Andere Anbieter».
  (3) Sandbox wird aufgelöst: neue Aufgabe DM-07, DM-62 darin aufgegangen. Keine Migration der
  SQLite-Datenbank, weil sie vor jedem Lauf neu aufgesetzt wird; deshalb entfällt auch die
  Rückwärtskompatibilität mit `clients` (DM-10, DM-53). Test-Workbook ohne `build.py` (DM-14).
  (4) Oktober-Abrechnung mit dem neuen Schema: Die Oktober-Bögen tragen noch `C…` in G8, DM-22/23
  sind damit für diesen Lauf Pflicht. Frist im Abschnitt «Termin und Rahmen».
  (5) DM-50 verlangt jetzt die Schritt-für-Schritt-Anleitung und wird vor der Generalprobe
  geschrieben, damit DM-51 genau danach läuft.

- **Alte Stammdatei eingefroren** `[Opus]` (Status: erledigt): Stephan hat `wegpiraten_datenbank.xlsx`
  aus der Kundenablage verschoben; Wegpiraten bearbeitet sie nicht mehr. Quelle für den finalen
  Build ist damit `sandbox/wegpiraten_datenbank.xlsx` (Stand 09.10.), sie ändert sich nicht mehr.
  Nächste Stammdatenänderung Ende Oktober, bis dahin müssen Unklarheiten und Datenfehler behoben
  sein. Backlog: Abschnitt «Termin» ergänzt, DM-60 nach P0 mit Frist, DM-04 auf die eingefrorene
  Quelle angepasst. Offen: mit welchen Programmen der Oktober-Lauf fakturiert.

- **Plan für die finale Umstellung** `[Opus]` (Status: erledigt): Backlog
  `docs/dev/backlog_umstellung_datenmodell.md` mit 36 Aufgaben in sechs Phasen plus P1/P2 und
  Modellzuordnung angelegt, dieses Log eingerichtet. Grundlage: Konzept, Datenmodell und
  Umstellungs-Runbook (Stand 25.09.2026), Kunde hat das Modell bestätigt.
  Befunde, die in den Plan eingeflossen sind:
  (1) `main` (`50ffaa5`) liegt 16 Commits hinter `fix/sa-sentinel-client`; der Produktivstand ist
  der Branch, nicht `main`.
  (2) Zwei Workbooks mit getrenntem Inhalt: `sandbox/wegpiraten_datenbank.xlsx` (alte Struktur,
  laufend gepflegt, Stand 09.10.) und `sandbox/wegpiraten_datenbank_neu.xlsx` (neue Struktur mit
  Handarbeit, Stand 30.09.). Die Sandbox-Skripte lesen noch `wegpiraten_datenbank(1).xlsx`, die
  nicht mehr existiert (DM-04).
  (3) `service_data` wird bei jedem Bogen-Import neu befüllt (heute nur Juni 2026, 243 Zeilen);
  die eigentliche Altlast sind die archivierten Bögen mit `C…` in G8 (DM-22), nicht die Datenbank.
  (4) 19 Module unter `src/` lesen `clients` oder `client_id`; die Rechnungsvorlage braucht
  keine Änderung, wenn die Kontextfelder ihre Namen behalten (DM-30).
  (5) Die Umstellung widerspricht AGENTS.md «Betriebsstabilität» (keine destruktiven
  Schemaänderungen, alte Importformate bleiben); Ausnahme braucht Stephans Freigabe (DM-01).
  Lokal angelegt: Tag `pre-datamodel-v2` auf `e960512`, Branch `feature/datamodel-v2` davon, Plan dort committet,
  nicht gepusht. Prüfung: keine Codeänderung, `nox` nicht gelaufen.
  Offen: Freigabe DM-00 und DM-01 durch Stephan.
