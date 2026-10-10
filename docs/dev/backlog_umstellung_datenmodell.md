# Backlog: Umstellung auf Kinder, Aufträge und Betreuungen

Stand 2026-10-09. Plan für die finale Umstellung der Programme und Daten auf das vom Kunden
bestätigte Modell. Fachliche Grundlage: [Konzept](../konzept_person_auftrag_leistung.md),
[Datenmodell](../datamodel_person_mandate_care.md), [Runbook Umstellung](../runbook_umstellung_datenmodell.md).
Der Fortschritt steht im [Umsetzungslog](umsetzungslog_umstellung_datenmodell.md); wer übernimmt,
liest zuerst dessen Abschnitt «Übergabe».

Planprüfung vom 10.10.2026: [Bewertung und Spezifikationsentwürfe](plan_review_2026-10-10.md).
Der Entwurf nennt zusätzliche Lücken bei DM-10/11/16, DM-03, DM-22 und den Abnahmekriterien;
er ist noch keine Freigabe der Opus-Aufgaben und schliesst keinen bestehenden Punkt.

Ergänzung 10.10.2026: Stephan hat Q1–Q4 beantwortet. Der Workaround erleichtert den
manuellen Ablauf bis WEGROSE einsetzbar ist. XLSX ist die gemeinsame Datenquelle;
kundenseitige Korrekturen, danach vollständiger Neuaufbau der SQLite-DB. Keine historische
Rekonstruktion oder maximale Absicherung als zusätzlicher Umfang. Ausgelassene Rechnungen
als Warnung zur Nacharbeit melden, übrigen Lauf fortsetzen. «Ohne Berechnung» erscheint
auf der Rechnung mit Betrag 0 CHF (Korrektur der zunächst genannten Ausschlussregel).

## Update 2026-10-10: implementation and September verification

New journal updates continue in English from this point; existing German task descriptions
remain in their original language.

Stephan instructed implementation and selected September 2026 as the comparison month.
The new import/schema/timesheet/invoice path is now implemented as one coherent change;
see [implementation contracts](dm12_dm15_dm22_implementierung.md) and
[September evidence](dm34_september_2026.md). No independent Opus/Astra review is claimed.
DM-34's financial comparison is complete; Stephan's operational acceptance remains open.
DM-16 has the P0 diagnostics and markings, with remaining warning coverage under DM-61.
DM-50's runbook is updated; DM-51 still requires the operator's runbook-based rehearsal.

Sandbox cleanup completed at Stephan's explicit request on 2026-10-10, overriding the
original wait-for-DM-06/41 condition through lossless archiving. All 43 files are retained
under ignored `archiv/umstellung_datenmodell_2026-10-10/sandbox/`, with a hash manifest.
The three one-off migration tests are archived alongside their scripts; active synthetic
pipeline tests remain. Customer handover files: `output/uebergabe_datenmodell_2026-10-10/`.
The workbook is byte-identical to the final build, named `wegpiraten_datenbank.xlsx` for
normal operation. Windows Excel DM-06 and actual delivery DM-60/52 remain open.
Historical `sandbox/` references below document former paths, not active dependencies.

DM-70 completed on 2026-10-10 at Stephan's explicit request, superseding the earlier
wait-for-real-use condition. `make terminliste MONTH=2026-10` creates one XLSX per
employee from the imported report list. Assign through role P; log and skip entries
without an unambiguous existing primary employee. See the implementation log for
selection rules and validation.

## Termin und Rahmen

Seit 2026-10-09 ist die alte Stammdatei eingefroren: Stephan hat `wegpiraten_datenbank.xlsx` aus der
Kundenablage verschoben, Wegpiraten kann sie nicht mehr bearbeiten. Massgeblich ist die Kopie
`sandbox/wegpiraten_datenbank.xlsx` (Stand 09.10.), sie ist gesichert.

Zwei Fristen:

1. **Ende Oktober 2026: neues Workbook beim Kunden.** Dann kommt die nächste Stammdatenänderung von
   Wegpiraten. Bis dahin müssen die Unklarheiten benannt und die Datenbefunde im Workbook markiert
   sein; beheben muss sie Wegpiraten, nicht die Umstellung. Kritischer Pfad: DM-05, DM-06, DM-60.
2. **Anfang November 2026: Oktober-Abrechnung mit dem neuen Schema** (entschieden 2026-10-09). Bis
   dahin müssen Phase 1 bis 3 und DM-50 fertig sein, die Bogenerzeugung für November ebenfalls.
   Die Oktober-Bögen sind noch aus dem alten Modell erzeugt und tragen `C…` in F8; deshalb ist
   DM-22/DM-23 für diesen Lauf Pflicht, nicht nur für Archivbögen.

Was das Vorgehen einfacher macht (Stephan, 2026-10-09):

- **Keine Migration der SQLite-Datenbank.** Wegpiraten pflegt das Workbook lokal, Stephan holt es
  vor jedem Lauf aus der Cloud und setzt die Datenbank komplett neu auf (SQLite-Datei löschen,
  `make import-master`). Das Schema entsteht bei jedem Import neu; es gibt keine Bestandsdaten, die
  umgebaut werden müssten, und keine Rückwärtskompatibilität mit `clients` im Feature-Branch.
- **Erfassungsbögen und Rechnungsvorlage bleiben, wie sie sind.** Sichtbar ändern sich nur der
  Inhalt von F8 (Auftrags- statt Klientennummer) und die Rechnungsnummer.
- **Die Sandbox wird aufgelöst** (DM-07). Nach der Umstellung bleibt dort nichts, was später für
  Verwirrung sorgen kann.

Format wie [backlog.md](../../backlog.md): `- [ ] [Priorität] [Bereich] Text. Hinweis: …`,
ergänzt um eine ID (`DM-nn`) und die Modellzuordnung.

## Modellzuordnung

Jede Aufgabe trägt genau eine Marke. Sie nennt die **kleinste Stufe, die die Aufgabe tragen darf**.
Jede höhere Stufe darf sie ebenfalls übernehmen, eine kleinere nicht.

| Marke | Wer | Wofür | Muss / kann |
| --- | --- | --- | --- |
| `[Stephan]` | nur der Mensch | Kundenkontakt, Freigaben, Excel unter Windows, Proton Drive, Push, Merge | muss |
| `[Opus]` | Opus (oder gleichwertig) | Entscheidungen mit Fach- oder Datenverlustrisiko, Spezifikationen für andere Aufgaben, Abnahme-Reviews, Abgleich alt gegen neu | muss |
| `[Sonnet]` | Sonnet aufwärts | Umsetzung nach einer Vorgabe, die in dieser Datei oder in der Spezifikation einer `[Opus]`-Aufgabe steht; Tests schreiben | kann |
| `[Haiku]` | Haiku aufwärts | mechanische Arbeit mit eindeutiger Vorgabe: Feldlisten übertragen, Umbenennungen, Prüfläufe ausführen und Ergebnis ins Log schreiben | kann |

### Andere Anbieter

Stand 2026-10-09. Gleiche Stufe heisst: darf dieselben Marken übernehmen.

| Stufe | Claude | OpenAI | Moonshot |
| --- | --- | --- | --- |
| `[Opus]` | Opus 5.5 (Fable 5.1 darüber) | GPT-6 Astra | Kimi K3 nur vorläufig, siehe unten |
| `[Sonnet]` | Sonnet 5.5 | GPT-6.1 Sol | Kimi K3 |
| `[Haiku]` | Haiku 4.5 | GPT-6 Luna | — |

- **OpenAI:** Die Einordnung folgt OpenAIs eigener Staffelung: Astra ist das Spitzenmodell für
  Arbeit, die beim ersten Mal stimmen muss, Sol (6.1) liegt nach Anbieterangabe nahe an Astra zu
  einem Fünftel des Preises, Luna ist für einfache Massenaufgaben. Eine Version «GPT-6.1 Luna» habe
  ich nicht gefunden, nur GPT-6 Luna.
- **Kimi K3:** offenes Modell mit starken Coding-Werten in Benchmarks, teils auf Höhe der
  Spitzenmodelle. Für `[Sonnet]`-Aufgaben unbedenklich. Die `[Opus]`-Aufgaben hier sind aber
  Fachentscheidungen auf Deutsch mit Datenverlustrisiko, und das messen die Benchmarks nicht.
  Deshalb gilt ein K3-Ergebnis auf einer `[Opus]`-Aufgabe als «Entwurf, Opus-Review offen», bis
  eine solche Aufgabe von einem Opus-Modell geprüft wurde und gehalten hat. Danach zählt K3 als
  `[Opus]`, und der Eintrag im Log hält das fest.
- **Werkzeuge anderer Anbieter lesen `CLAUDE.md` und die Claude-Skills nicht**, sondern `AGENTS.md`.
  Deshalb verweist AGENTS.md auf dieses Backlog und das Log; mehr Kontext braucht ein fremdes Modell
  nicht.
- Im Log steht der genaue Modellname (z.B. `[GPT-6 Astra]`), nicht nur die Stufe.

Grundsatz für Daten (Stephan, 2026-10-09): **Datenpflege ist nicht Aufgabe der Umstellung, nur im
Ausnahmefall.** Inkonsistenzen werden benannt und markiert, nicht korrigiert, und sie blockieren
keinen Schritt: weder den Build noch den Import noch einen Monatslauf. Die Ausnahme ist ein Fehler,
den unser eigener Code erzeugt; der wird im Code behoben.

Regeln für den Modellwechsel:

- **Nur beginnen, was im laufenden Kontingent fertig wird** (Stephan, 2026-10-09). Jede Sitzung
  hinterlässt ein stabiles Zwischenergebnis: committet, `nox` grün oder der Grund im Log, und so
  beschrieben, dass ein anderes Modell ohne Rückfrage weitermacht. Ist eine Aufgabe dafür zu gross,
  wird sie vor dem Beginn im Log in Teilschritte geschnitten (`DM-nn.1`, `DM-nn.2`), von denen jeder
  für sich stabil ist. Ein halb umgebauter Code-Pfad wird nicht committet; lieber den kleineren
  Schritt fertig als den grösseren angefangen.
- **Eine `[Opus]`-Aufgabe wird nicht abwärts vergeben.** Ist Opus nicht verfügbar, darf Sonnet einen
  Entwurf schreiben. Er wird im Log als «Entwurf, Opus-Review offen» markiert, und keine abhängige
  Aufgabe beginnt, bevor das Review im Log steht.
- **Eine Aufgabe mit `Spezifikation:` ist erst bereit, wenn die genannte Spezifikation im Log
  steht.** Das ist der Übergabepunkt zwischen den Stufen.
- **Jede Sitzung endet mit einem Logeintrag**, auch eine abgebrochene. Ohne Eintrag gilt die
  Aufgabe als nicht begonnen.
- Personendaten (Namen, AHV-Nummern) kommen weder in Commits noch in Testdaten. Tests laufen auf
  einem synthetischen Workbook (DM-14).

## Branch und Sicherung

Sicherung und neuer Branch, beides (Stephan, 2026-10-09).

- Rückweg: Tag `pre-datamodel-v2` und Branch `backup/pre-datamodel-v2` auf dem heutigen
  Produktivstand (`e960512`). Der Branch ist der Fallback, auf dem notfalls ein Lauf mit dem alten
  Modell und der gesicherten alten Datei möglich bleibt; der Tag markiert den Punkt unverrückbar.
- Umstellung auf `feature/datamodel-v2`. Notfixes bis zur Umstellung auf `main`, bei Bedarf in den
  Feature-Branch übernehmen.
- Merge in `main` nach der Generalprobe (DM-51), danach Tag `datamodel-v2`.

Ausgangslage am 2026-10-09: `main` steht auf `50ffaa5`. Der ausgecheckte Branch
`fix/sa-sentinel-client` ist 16 Commits weiter (SA-Sentinel-Fix, Modell-Dokumente,
Sandbox-Skripte), alle gepusht, nicht gemergt. Er ist der eigentliche Produktivstand.

## P0 Must

### Phase 0: Vorbereitung

- [x] [P0] [Git] **DM-00** Produktivstand sichern und Umstellungsbranch anlegen. `[Stephan]` für die Freigabe, Ausführung `[Haiku]`. Hinweis: erledigt 2026-10-09: `main` per Fast-Forward auf `e960512`, Tag `pre-datamodel-v2`, Branches `backup/pre-datamodel-v2` und `feature/datamodel-v2`, alles gepusht.
- [x] [P0] [Governance] **DM-01** Ausnahme von AGENTS.md «Betriebsstabilität» festhalten. `[Stephan]`. Hinweis: von Stephan am 2026-10-09 bestätigt, in AGENTS.md eingetragen (Abschnitt «Ausnahme: Umstellung des Datenmodells»), dort auch der Verweis auf Backlog und Log für Modelle, die CLAUDE.md nicht lesen.
- [x] [P0] [Fach] **DM-02** Offene Fachfragen nach «blockiert die Umstellung» und «kann warten» sortieren. `[Opus]`, Antworten `[Stephan]` mit Wegpiraten. Hinweis: erledigt 2026-10-09, Ergebnis in [dm02_fachfragen.md](dm02_fachfragen.md): 3 Regeln für die Programme (A, mit Vorschlag bis zur Antwort), 10 Datenbefunde (B, markiert, nicht blockierend), Rest kann warten (C). Antworten von Wegpiraten offen. Ursprünglicher Auftrag: Blockierend nach heutiger Lesart: KOB (`ST09`) ohne Accordix-Zuordnung (melden oder ausschliessen), die Folgeaufträge Duarte Torres und Loosli (Ende alt, Beginn neu), Rechnungsnummer-Wechsel C→A gegenüber KJA-FS und KESB ankündigen. Kann warten: Fragen 10–14 im Datenmodell (KESB-Nummern, Berichtsformen, Rhythmen, Abschlussbericht, Erledigt-Stand). Ergebnis als Liste im Log.
- [x] [P0] [Fach] **DM-03** Einführungsgespräch im neuen Modell festlegen. `[Opus]`, Bestätigung `[Stephan]`. Hinweis: entschieden 2026-10-09, konkretisiert/korrigiert 2026-10-10 (Stephan): Kunde splittet manuell 15 Minuten mit Notiz `Ohne Berechnung` und den Rest. Die markierte Position erscheint auf der Rechnung mit Betrag 0 CHF, wie im bestehenden Code. Die bisherige Ableitung aus ST99/Eintrittsmonat ist zurückgenommen (ST99 = PRIVAT). Keine automatisch erzeugte Position oder maschinelle Einmaligkeitskontrolle; Risiko eines falsch gesetzten Texts akzeptiert.
- [x] [P0] [Daten] **DM-04** Datenstand für den finalen Build zusammenführen. `[Opus]`. Hinweis: erledigt 2026-10-09, Spezifikation in [dm04_build_spezifikation.md](dm04_build_spezifikation.md); Der Build übernimmt nur die Daten der originalen Datenbank, unverändert; aus dem Testbuild nur Berichte und die drei Folgeaufträge, beide markiert «zu prüfen» (Stephan, 2026-10-09). Keine Familien, Rollen nur wo eindeutig. Ursprünglicher Auftrag: Die alte Struktur ist seit 09.10. eingefroren (`sandbox/wegpiraten_datenbank.xlsx`), die Handarbeit (Familien, Rollen P/S, Berichte, Korrekturen) liegt in `sandbox/wegpiraten_datenbank_neu.xlsx` (Stand 30.09.). Ein Neubau aus der alten Datei allein verliert die Handarbeit. `migrate.py` und `build.py` lesen noch `wegpiraten_datenbank(1).xlsx`, die es nicht mehr gibt. Spezifikation ins Log: Quelle je Blatt, was `carry_over_handwork` heute übernimmt und was fehlt, wie Klienten behandelt werden, die zwischen dem 24.09. und dem 09.10. dazugekommen sind oder sich geändert haben. `mandate_numbers.json` bleibt eingefroren, neue Aufträge bekommen den nächsten freien Zähler. Ergebnis ist die Datei, die Wegpiraten Ende Oktober bekommt; danach ist das Workbook beim Kunden die einzige Quelle, ein Neubau aus JSON-Dateien findet nicht mehr statt.
- [x] [P0] [Daten] **DM-05** Finalen Build ausführen und Differenz belegen. `[Sonnet]`, Spezifikation: DM-04. Hinweis: genau nach den acht Schritten in [dm04_build_spezifikation.md](dm04_build_spezifikation.md). Erledigt 2026-10-10: [Build-Ergebnis](dm05_build_ergebnis.md), finale XLSX und Befundliste lokal in sandbox; 0 unerklärte Feldabweichungen, 0 Formelfehler. Windows-Excel-Prüfung DM-06 bleibt offen.
- [ ] [P0] [Daten] **DM-06** Workbook in echtem Excel prüfen. `[Stephan]`. Hinweis: LibreOffice sieht die Excel-Defekte nicht (siehe Datenmodell, «Excel-specific decisions»). `tools/excel_pruefung.ps1` unter Windows, Dropdowns und Prüfungen stichprobenweise. Danach Übergabe an Wegpiraten.
- [x] [P0] [Aufräumen] **DM-07** Sandbox auflösen. `[Opus]` legt fest, `[Haiku]` führt aus, `[Stephan]` verschiebt die Dateien mit Personendaten. Hinweis: Erst nach DM-06 und DM-41 (die Accordix-Meldung August liegt dort). Inventar jeder Datei in `sandbox/` mit Entscheid: löschen, ins Repo übernehmen (z.B. `verify_excel_strict` und `excel_pruefung.ps1`, falls sie für spätere Strukturänderungen am Kunden-Workbook gebraucht werden) oder ausserhalb des Repos archivieren (alles mit Personendaten). `migrate.py`, `prepare.py`, `import_reports.py`, die `migration*.json`, `reports_import.json` und `mandate_numbers.json` haben nach dem finalen Build keinen Zweck mehr. Danach: `sandbox/`-Regeln aus `.gitignore`, alle Verweise auf `sandbox/` in `docs/` prüfen (das Datenmodell nennt sie als Herkunft, dort als Geschichte kennzeichnen, im Runbook entfernen), die Klärungsdateien sind beantwortet oder ins Log übertragen. Abnahme: `git grep sandbox` zeigt nur noch begründete Erwähnungen.

- [ ] [P0] [Daten] **DM-60** Befundliste mit dem Workbook an Wegpiraten übergeben. `[Stephan]`, Liste `[Sonnet]` (DM-05, Schritt 8). Hinweis: [dm02_fachfragen.md](dm02_fachfragen.md), Gruppe B, im Stand nach dem finalen Build. Die Bereinigung ist Sache von Wegpiraten und keine Voraussetzung für einen weiteren Schritt.

### Phase 1: Schema und Stammdaten-Import

- [x] [P0] [Config] **DM-10** Entitätsmodelle in `.config/wegpiraten_config.yaml` anlegen: `person`, `mandate`, `mandate_person`, `contact_person`, `mandate_employee_relation`, `report`. `[Haiku]`. Hinweis: Feldnamen, Typen und Pflicht genau aus den Tabellen im Datenmodell, Abschnitt «Entities». Editierbare Fachfelder plus die beiden berechneten FK-Schlüssel `predecessor_mandate_id` und `report.mandate_id`; Anzeige-/Prüfspalten werden nicht importiert (Korrektur 10.10.). `client` und `client_employee_relation` werden im selben Zug entfernt: Die Datenbank wird bei jedem Lauf neu aufgesetzt, der Feature-Branch muss das alte Schema nicht mehr lesen.
- [x] [P0] [Import] **DM-11** `import_masterdata.py` auf die neuen Blätter umstellen. `[Sonnet]`. Hinweis: `DEFAULT_TABLE_MAPPINGS` und `FOREIGN_KEY_MAPPINGS` (Reihenfolge: Stammdaten → `masterdata_contact_person` → `person` → `mandate` → `mandate_person` → `relation_mandate_emp` → `report`). Leere Reservezeilen (das Workbook hat 2000 Formelzeilen) überspringen. FK-Diagnostik bleibt.
- [x] [P0] [Schema] **DM-12** Abgeleitete Felder als SQL-View `v_mandate` spezifizieren. `[Opus]`. Hinweis: `index_person_id` (jüngstes Kind der Familie der Betreuungskinder, sonst das Kind selbst; bei gleichem Geburtsdatum dieselbe Regel wie im Workbook), `short_code` und `last_name/first_name/social_security_number` des Indexkindes, `sr_ap_gender/first_name/last_name` der Ansprechperson, Budget in Minuten. Die View muss für jeden Auftrag dasselbe Indexkind liefern wie das Workbook; Abgleich gehört zur Spezifikation. Stephan, 2026-10-10: immer heutiges Indexkind, auch bei alten Leistungsdaten; keine Historie rekonstruieren.
- [x] [P0] [Schema] **DM-13** View `v_mandate` umsetzen und gegen das Workbook prüfen. `[Sonnet]`, Spezifikation: DM-12. Hinweis: Test vergleicht View-Spalten mit den berechneten Spalten des Workbooks für alle Aufträge.
- [x] [P0] [Import] **DM-14** Synthetisches Test-Workbook ohne Personendaten. `[Sonnet]`. Hinweis: kleiner Ausschnitt mit den Fällen aus dem Konzept: Geschwister mit Indexkind, Kind mit zwei Aufträgen, Folgeauftrag, Vertretung (zwei MA, eine mit P), Austritt, SA-Sentinel. Das Test-Workbook enthält nur die Excel-Tabellen, die der Import liest (gleiche Tabellennamen und Spalten wie das finale Workbook), erzeugt von einem kleinen Skript unter `tests/fixtures/`; keine Abhängigkeit von `build.py`, das mit der Sandbox verschwindet. Grundlage für alle Tests ab hier. Erledigt 2026-10-10: `tests/fixtures/create_masterdata.py`, elf Tabellen ohne Sandbox-Abhängigkeit, Testfälle und Tabellen-/Mappingprüfungen. SA wird vom Import erzeugt; neuer Schema-Import folgt in DM-11/15.
- [x] [P0] [Import] **DM-15** SA-Sentinel im neuen Modell. `[Opus]` entscheidet, `[Sonnet]` setzt um. Hinweis: `internal_client.py` legt heute einen Klienten `SA` an. Vorschlag: ein Auftrag `SA` ohne Kind und ohne Betreuung, von Invariante 8 ausgenommen, nie fakturiert, nie gemeldet. Betrifft Import, Bogenerzeugung und Rechnungsfilter.
- [ ] [P0] [Import] **DM-16** Invarianten beim Import prüfen, markieren statt anhalten. `[Sonnet]`. Hinweis: Der Import schreibt eine Befundliste (Invariante nach Nummer des Datenmodells, Blatt, Schlüssel, Text) ins Log und als Datei neben die Ausgabe, und er läuft weiter. Anhalten darf er nur, wenn das Workbook technisch nicht lesbar ist (Blatt oder Spalte fehlt). Doppelte Schlüssel: erste Zeile importieren, weitere als Befund nennen. Die nachgelagerten Programme markieren betroffene Ergebnisse nach dem bestehenden Muster `PRÜFEN` (fehlende Geschäftsnummer im Rechnungsdateinamen), etwa Rechnungen eines Auftrags ohne bestimmbares Indexkind oder mit doppelter KJA-Nummer, und listen sie in der Rechnungsübersicht.

Ergänzung zu DM-16 (Stephan, 2026-10-10): Fehlen verwendbare Rechnungsgrundlagen, wird
die betroffene Rechnung ausgelassen und als Warnung mit Auftrag und Grund im Log genannt.
Der übrige Lauf geht weiter. Markierung `PRÜFEN` bleibt für erstellbare Rechnungen mit
Datenbefunden bestehen; sie ersetzt keine fehlende Grundlage. Der Kunde korrigiert das
Workbook fachlich, Stephan baut die SQLite-DB danach vollständig neu auf.

DM-10 ist in stabile Schritte geteilt: **DM-10.1 erledigt 10.10.2026**, sechs neue Modelle
additiv vorbereitet, inklusive der beiden berechneten FKs und Budgetumrechnung. Alte
Modelle blieben im Vorbereitungsschritt vorübergehend erhalten. **DM-10.2
erledigt 10.10.:** Entfernung der alten Modelle gemeinsam mit der Umstellung aller Verbraucher;
DM-10 abgeschlossen. Fixture-Mapping und Config-Validierung geprüft.

### Phase 2: Zeiterfassung

- [x] [P0] [Zeiterfassung] **DM-20** Bogenerzeugung auf Aufträge umstellen. `[Sonnet]`. Hinweis: `time_sheets/modules/client_data.py` liest `relation_mandate_emp` + `v_mandate` statt `relation_client_emp` + `clients`. Ein Bogen je Zeile der Zuordnung, wie bisher. Zelle F8 trägt (Korrektur 10.10., Config und September-Bögen geprüft) die Auftragsnummer, C8 das Kurzzeichen des Indexkindes, Budget aus dem Auftrag. Dateiname `{employee_id}_{mandate_id} ({short_code})_{YYYY-MM}.xlsx`. Aufträge mit abgelaufener Bewilligung erzeugen keinen Bogen mehr (Invariante 31 als Warnung ins Log).
- [x] [P0] [Zeiterfassung] **DM-21** Beschriftung im Bogen-Template prüfen. `[Haiku]`. Hinweis: Steht im Kopf «Klient-Nr» neben F8, wird es «Auftrag-Nr». Nur Text, keine Zellverschiebung (`header_cells.py` bleibt gültig). Erledigt 2026-10-10: E8 von «Klient-Nr.:» auf «Auftrag-Nr.:» geändert, alle übrigen XLSX-ZIP-Bestandteile unverändert.
- [x] [P0] [Import] **DM-22** Zuordnung alter Nummern beim Bogen-Import spezifizieren. `[Opus]`. Hinweis: Archivierte und noch ausstehende Bögen tragen `C…` in F8. Die Zuordnung C→A ist nicht immer eindeutig: bei nachgetragenen Folgeaufträgen (Yahia, Nipote, Gorlov, Richards) entscheidet das Leistungsdatum, welcher Auftrag gilt. Laufende Quelle ist `resources/legacy_mandate_mapping.json` plus die aktuellen Bewilligungszeiträume; keine Sandbox-Abhängigkeit (10.10.). Unauflösbar = fataler Fehler mit Datei und Zeile, kein stilles Raten.
- [x] [P0] [Import] **DM-23** `batch_import_timesheets.py` auf `mandate_id` umstellen. `[Sonnet]`, Spezifikation: DM-22. Hinweis: `service_data.client_id` wird `service_data.mandate_id` (FK auf `mandate`), Budgetspalten bleiben. Bögen mit `C…` laufen über die Zuordnung aus DM-22. Tests mit je einem Bogen alter und neuer Form.

### Phase 3: Rechnung

- [x] [P0] [Rechnung] **DM-30** `invoice_processor.py` auf Aufträge umstellen. `[Sonnet]`. Hinweis: `JOIN clients` → `JOIN v_mandate`. Gruppierung bleibt je Auftrag (siehe Datenmodell, «What the invoice number names»), Kostenträger, Besteller, Ansprechperson und Standort vom Auftrag, Name und AHV-Nummer vom Indexkind. Kontextfelder (`client_name`, `client.social_security_number`, `sr_ap_*`) behalten ihre Namen, damit `rechnungsvorlage.docx` unverändert bleibt. Einführungsgespräch nach DM-03.
- [x] [P0] [Rechnung] **DM-31** Rechnungsnummer aus der Auftragsnummer. `[Sonnet]`. Hinweis: entsteht von selbst aus `service_data.mandate_id` (`2026-11-A26001`). `generate_scor` mit den neuen Nummern testen. Dateiname `{invoice_id}_{von}_{bis}_{application_number}` bleibt; die KJA-FS-Upload-Konvention prüfen (`_` als Trenner).
- [x] [P0] [Rechnung] **DM-32** Rechnungsfilter `CLIENT=` erweitern. `[Sonnet]`. Hinweis: `invoice_filter.py` nimmt A-Nummern (ein Auftrag) und C-Nummern (alle Aufträge, deren Indexkind das Kind ist). Makefile-Hilfe nachgezogen (10.10.).
- [x] [P0] [Rechnung] **DM-33** Rechnungsübersicht (`document_utils.py`) um Auftragsnummer ergänzen. `[Haiku]`. Hinweis: Spalte «Auftrag» vor «Klient», «Klient» zeigt das Indexkind. Sonst keine Änderung am Layout.
- [ ] [P0] [Rechnung] **DM-34** Paralleler Rechnungslauf alt gegen neu. `[Opus]` legt fest, was gleich sein muss, `[Sonnet]` schreibt den Vergleich, `[Stephan]` nimmt ab. Hinweis: ein abgeschlossener Monat (Vorschlag 2026-09) einmal mit `backup/pre-datamodel-v2` und der alten Datei, einmal mit dem Feature-Branch und dem finalen Workbook. Beträge, Stunden, Positionen, Empfänger und QR-Daten ausser der Referenz je Rechnung gleich; erlaubt verschieden sind nur Rechnungsnummer, Referenz und Dateiname. Jede andere Abweichung ist ein Fehler, eine im Log begründete fachliche Änderung oder die Wirkung eines Datenbefunds aus DM-02 B.

DM-34: financial comparison completed on 2026-10-10: 53 archived invoice amounts match,
167 identical imported rows, CHF 60,385.93 sum of rounded individual invoices. Contact
salutations and C1068 quota differences are explained in the evidence document; operator
acceptance remains open, so the checkbox is deliberately not closed.

### Phase 4: Reporting

- [x] [P0] [Report] **DM-40** Accordix-Meldung aus den Betreuungen. `[Opus]` spezifiziert, `[Sonnet]` setzt um. Hinweis: Stephan, 2026-10-10: Meldung je Betreuung, nicht je Auftrag. Die bisherige Gleichsetzung jeder `mandate_person`-Zeile mit einer Meldezeile ist korrigiert: fortlaufende Betreuung über Folgeaufträge zusammenfassen, verschiedene Betreuungskinder getrennt melden. Eintritt und Austritt von der Betreuung, Leistungsart und Kostenträger vom Auftrag. Kettenregel implementiert und mit Wechsel/Austritt getestet; unabhängiges Review nicht behauptet. Die Sonderregel für Austritt = Bewilligungsende entfällt. **Gemeldet werden nur Betreuungen über den Kostenträger P1000 (KJA-FS)** (Stephan, 2026-10-09); Kostenträgerfilter vor `SERVICE_TYPE_MAP`. Die Liste meldepflichtiger Kostenträger gehört in die Config. Invariante 36 gilt nur für meldepflichtige Kostenträger.
- [ ] [P0] [Report] **DM-41** Abgleich Accordix August 2026. `[Opus]`. Hinweis: neue Meldung gegen `archiv/umstellung_datenmodell_2026-10-10/sandbox/Import-Accordix_ambulant_August_2026.xlsx`. Jede Abweichung erklären: zusätzliche Geschwister, getrennte Austritte und wegfallende Zeilen anderer Kostenträger als P1000 sind gewollt, alles andere nicht.
- [x] [P0] [Report] **DM-42** Arbeitszeitprotokoll auf Aufträge umstellen. `[Haiku]`. Hinweis: `reports/arbeitszeit_report.py`, ein JOIN (`clients` → `v_mandate`); im Detailblatt Auftragsnummer und Indexkind zeigen.
- [x] [P0] [Report] **DM-43** `utils/extend_masterdata_accordix.py` stilllegen oder anpassen. `[Opus]` entscheidet, `[Haiku]` führt aus. Hinweis: Das Skript ergänzt die alte Klientenliste um Accordix-Spalten. Diese Felder sind jetzt Teil von Kinder und Betreuungen; das Skript ist vermutlich überflüssig.

### Phase 5: Umstellung

- [ ] [P0] [Doku] **DM-50** Betriebs-Runbook mit Schritt-für-Schritt-Anleitung umschreiben. `[Sonnet]`, Review `[Opus]`. Hinweis: `docs/runbook_betriebsablauf.md` bekommt den Monatslauf als nummerierte Schritte, jeder mit Befehl, erwartetem Ergebnis und was bei Abweichung zu tun ist: Workbook aus der Cloud holen (`make fetch-master`), SQLite-Datei löschen, `make import-master` und dessen Prüfmeldungen lesen, Bögen erzeugen (`make timesheets`), Bögen einsammeln und importieren, Rechnungen, Arbeitszeitprotokoll, Accordix. Dazu der einmalige Abschnitt «Erster Lauf nach der Umstellung» (Oktober 2026: Bögen mit `C…` in F8). Das Umstellungs-Runbook verliert die Sandbox-Teile und das Kapitel «Für die Umsetzung in den Programmen», die «Typischen Vorgänge» für Wegpiraten bleiben. AGENTS.md und CLAUDE.md (Projektübersicht, Datenmodell) nachziehen. Wird vor DM-51 geschrieben, damit die Generalprobe genau nach dem Runbook läuft.
- [ ] [P0] [Betrieb] **DM-51** Generalprobe auf einer Kopie. `[Stephan]` mit `[Sonnet]`. Hinweis: kompletter Monat auf dem Feature-Branch mit dem finalen Workbook, Schritt für Schritt nach dem Runbook aus DM-50; jede Stelle, an der das Runbook nicht reicht, wird dort korrigiert. Vorschlag: September 2026 mit den archivierten Bögen, dann ist der Vergleich aus DM-34 gleich mit erledigt.
- [ ] [P0] [Betrieb] **DM-52** Neues Workbook an Wegpiraten übergeben und Quelle umschalten. `[Stephan]`. Hinweis: Ende Oktober 2026. Wegpiraten bearbeitet die Datei lokal, Stephan holt sie aus der Cloud. Empfehlung: Sie heisst wieder `wegpiraten_datenbank.xlsx`, dann bleibt `masterdata_source` in der Config unverändert; heisst sie anders, `file_pattern` und `preferred_filename` anpassen (`[Haiku]`).
- [ ] [P0] [Git] **DM-53** Merge nach `main`, Tag `datamodel-v2`. `[Stephan]`. Hinweis: nach DM-34 und DM-51, vor dem Oktober-Lauf; DM-41 nur dann vorher, wenn die Accordix-Meldung vor dem Lauf fällig ist.

DM-16.1 implemented: P0 key/FK/mandate/number diagnostics, `PRÜFEN` filename and summary
markers, warning-only omission of unusable invoices. Full warning parity follows in DM-61;
DM-16 remains open for final review of coverage. DM-50 runbook rewritten; its review and the
operator rehearsal remain open. No claim of a production or cloud rehearsal.

## P1 Should

- [ ] [P1] [Import] **DM-61** Workbook-Prüfungen und Python-Prüfung abgleichen. `[Sonnet]`. Hinweis: Hinweis-Invarianten (14–36) zusätzlich im Import als Warnung ausgeben, damit eine im Workbook übersehene Prüfung im Log steht.

- [x] [P1] [Workbook] **DM-63** Prüfung «Abschlussbericht auf einem Auftrag mit Nachfolger» (Hinweis). `[Sonnet]`. Hinweis: Abschlussberichte gibt es nur für den letzten Auftrag einer Kette (Stephan, 2026-10-09). Neue Prüfung im Workbook nach dem Muster der bestehenden (`build.py`, Blatt «Prüfungen»), neue Invariantennummer 49 im Datenmodell. Erledigt 2026-10-10 mit DM-05: zwei Fälle als Hinweis in Prüfungen und Fehlerliste. Nur markieren. Ursprüngliche Planung: Wenn sie vor der Übergabe fertig wird, mit DM-05 bauen; sonst ist sie die erste Strukturänderung am Kunden-Workbook nach DM-07.

## P2 Nice

- [x] [P2] [Report] **DM-70** Monatliche Aufgabenliste je Mitarbeitende («Terminzettel»). `[Opus]` spezifiziert, `[Sonnet]` setzt um. Hinweis: aus `report`, zuständig ist die Person mit Rolle P. Eigenes `make`-Target neben den Erfassungsbögen, nicht in deren Lauf (Wunsch von Wegpiraten). Liest nur `due_date` und `report_form` als Text (Bericht/Zwischenbericht ohne Semantik, Stephan 2026-10-09); Rhythmen sind zurückgestellt, Termine werden von Hand eingetragen. Bewusst erst nach einer Runde echter Nutzung der Berichtsliste.
- [ ] [P2] [Rechnung] **DM-71** Folgeauftragskette auf der Rechnung oder in der Übersicht sichtbar machen. `[Sonnet]`. Hinweis: nur wenn Wegpiraten es wünscht; heute nicht verlangt.

## Abhängigkeiten

```
DM-00, DM-01 (erledigt)
DM-02 ─┬─ DM-03 ──────────────── DM-30
       └─ DM-04 ─ DM-05 ─ DM-06 ─ DM-52 (Ende Oktober)
DM-05 ─ DM-60 (Übergabe mit dem Workbook)
DM-10 ─ DM-11 ─┬─ DM-12 ─ DM-13 ─┬─ DM-20 ─ DM-21
DM-14 ─────────┘                 ├─ DM-22 ─ DM-23
DM-15 ───────────────────────────┤
                                 ├─ DM-30 ─┬─ DM-31, DM-32, DM-33
                                 │         └─ DM-34
                                 └─ DM-40 ─ DM-41;  DM-42, DM-43
DM-34, DM-41, DM-06 ─ DM-50 ─ DM-51 ─ DM-53 ─ Oktober-Lauf (Anfang November)
DM-06, DM-41 ─ DM-07
```

Was ohne Antwort von Wegpiraten beginnen kann: DM-10 bis DM-16, DM-20 bis DM-23, DM-30 bis
DM-33 und DM-42. Was auf Antworten wartet: nichts; alle Regeln aus DM-02 A sind entschieden.
Reihenfolge bei knappem Kontingent: zuerst alles, was Ende Oktober braucht (DM-02, DM-04 bis
DM-06, DM-60), dann der Pfad zum Oktober-Lauf (DM-10 bis DM-34, DM-50, DM-51); Reporting
(Phase 4) darf nach dem ersten Rechnungslauf kommen, wenn die Accordix-Meldung nicht vorher fällig ist.

- [ ] [P1] [Invoice] September comparison found the existing distinction between summing
  unrounded computed totals (CHF 60,385.92) and summing the rounded invoice amounts
  (CHF 60,385.93). Decide whether the summary should sum the latter; do not change individual
  invoice calculations as a side effect of this migration.
