# Umsetzungslog: Umstellung auf Kinder, Aufträge und Betreuungen

Begleitet das [Backlog](backlog_umstellung_datenmodell.md). Muster wie
[umsetzungslog.md](../../umsetzungslog.md): neueste Einträge zuerst, ein Abschnitt je Tag.

## Übergabe

Diesen Abschnitt liest jedes Modell zuerst und überschreibt ihn am Ende jeder Sitzung. Er ist der
einzige Ort, der den aktuellen Stand trägt; die Einträge darunter sind die Begründung dafür.

The handover continues in English from 2026-10-10; historical entries below keep their language.

- **Branch:** `feature/datamodel-v2`; fallback branch/tag `backup/pre-datamodel-v2` / `pre-datamodel-v2` at `e960512`. No push or merge in this session.
- **Deadline:** workbook handover by late October; October invoices with the new schema in early November.
- **Completed:** common schema and consumer switch DM-10–15, DM-20–23, DM-30–33, DM-40/42/43. `v_mandate`, SA sentinel, per-row legacy mapping, new timesheets, invoices and reports implemented. Specification: `dm12_dm15_dm22_implementierung.md`.
- **September evidence:** DM-34 financial comparison completed, 167 identical service rows, 53 invoices, all 53 archived amounts match, CHF 60,385.93 rounded total. Evidence remains ignored under `output/test_datamodel_2026-09_20261010`. Details: `dm34_september_2026.md`. Nine invoices flagged. Two salutation differences and one budget difference documented.
- **In progress:** none; stable common switch ready for review. The live database was not replaced; the CLI now requires a database rebuilt with the new workbook.
- **Next independent work:** remaining invariant/warning coverage DM-16/61, Accordix August comparison DM-41, runbook review DM-50. Do not remove sandbox until DM-06 and DM-41 are complete.
- **Waiting for Stephan:** DM-06 real Windows Excel, acceptance DM-34, operator rehearsal DM-51, customer handover DM-60/52 and merge DM-53. Q1–Q4 answered. October test sheets use a test password and must not be distributed.
- **Model attribution:** Codex / GPT-6, exact variant not exposed. No independent Opus/Astra review is claimed. Stephan explicitly authorized implementation.
- **Validation:** 38 tests passed in `.nox/test`; `nox` lint/typecheck including reports passed (0 errors/warnings). Nox test dependency installation previously failed on network access; direct tests passed. All 94 workbook-derived mandate headers match the view; all 53 SCOR checks valid; PDF layout sampled. Windows-specific validation remains open.
- **Operating scope:** temporary aid until WEGROSE. Customer-maintained XLSX is authoritative; SQLite disposable. Correct findings in XLSX and rebuild. Skip unusable invoices with logged reasons; keep reviewable invoices marked `PRÜFEN`. Current Indexkind also for historical runs. Accordix per Betreuung. Manual `Ohne Berechnung` positions visible at CHF 0.

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

## 2026-10-10

Journal entries continue in English from this date; earlier German entries remain unchanged.

- **Common schema/consumer switch and September reproduction**
  `[Codex / GPT-6, exact variant not exposed]` (Status: implementation completed, acceptance open):
  Completed DM-10–15, DM-20–23, DM-30–33, DM-40/42/43. Added import preflight, typed
  mappings, source row order, structured findings, review flags and `v_mandate` (94-row workbook
  parity). SA has no fictitious care. Frozen identifier-only legacy mapping lives in `resources/`;
  per-date resolution rejects ambiguous files atomically. Current master budgets use minutes.
  Switched timesheets, invoices and reports together; Accordix groups continuous Betreuung
  through renewals; retired `extend-master`. Fixed missing AHV values becoming `nan` and
  actual header defaults F5/F8. Reports now included in nox. Tests cover renewal boundaries,
  overlaps, twins, missing contacts, SA, free positions, tariff rejection, real DOCX rendering
  and generated-sheet roundtrip. September used isolated copies of both versions: 66 sheets,
  167 identical service rows, 53 DOCX/60 PDFs each, all 53 archived invoice amounts reproduced,
  CHF 60,385.93 rounded sum. Contact/budget findings documented; nine invoices marked.
  SCOR validity checked; PDF invoice/payment layout sampled. Added reusable context comparer.
  Evidence: `dm34_september_2026.md`; contracts: `dm12_dm15_dm22_implementierung.md`.
  Updated runbooks, config examples and handover. No customer data or generated documents
  committed; original database and archives unchanged. Validation: 38/38 tests, nox passed.
  Open: DM-16/61 coverage, DM-06 Windows Excel, DM-41 Accordix August, DM-50/51 review and
  rehearsal, acceptance and merge. No push, merge or customer distribution.


- **DM-14 fixture, DM-21 label and DM-10.1 preparation** `[Codex / GPT-6, exact variant not exposed]`
  (Status: completed stable subtasks): Added `tests/fixtures/create_masterdata.py` and its
  README: eleven synthetic import tables, no customer data or sandbox dependency, family,
  parallel/follow-up mandates, substitution, exit and TS=false cases. Calculated foreign
  keys are supplied as fixture values; SA remains importer-generated, its integration test
  awaits DM-15. Added six config entities without removing old client models or switching
  runtime consumers. Verified all new fields against fixture tables and actual map_row:
  0.5 hours becomes 30 minutes once. DM-10.2 and DM-10 overall remain open until the common
  consumer switch. Changed E8 in the timesheet template to «Auftrag-Nr.:» by modifying the
  single XML label; all other ZIP parts remained byte-identical. G8 and layout unchanged.
  Validation: `nox` lint/typecheck passed, 31/31 tests passed in the existing test environment;
  additional ruff checks for new fixture/tests passed. No live database or customer source
  file changed. Next: spec review and common import/consumer migration, Windows Excel DM-06.


- **DM-05 final workbook and DM-63 check** `[Codex / GPT-6, exact variant not exposed]`
  (Status: completed): Updated sandbox migration/build scripts according to approved DM-04:
  frozen original source, separate final destination, no demo families/roles, 153 reports
  and six mandate rows marked `ZU PRÜFEN:`. Corrected predecessor application number for
  C1024; retained current successor number. No historical contact rulings applied to original
  data. Added row and catalogue checks for imported details and closing reports on predecessors
  (two findings), plus invariants 49/50. Preserved 91 issued numbers; C1089=A26047,
  C1091=A26048, C1090=A26049. Final counts: 87 persons, 94 mandates/cares, 101 links,
  49 contacts, 153 reports, zero families. Four known person merges unchanged.
  Verification: field-level source comparison, all report fields, MA pairs and roles passed;
  zero unexplained differences, zero formula errors after LibreOffice recalculation;
  strict Excel validation passed before/after recalculation. Original/testbuild unchanged by
  hash comparison. Added reusable `sandbox/verify_final.py` and three synthetic regression
  tests; full existing suite 27/27 passed. `nox` lint/typecheck passed; `nox -s test` could
  not install build dependencies due to sandbox network restrictions, direct existing test
  environment passed. Output and customer findings remain local, not in Git.
  Next: Windows Excel acceptance DM-06, then customer handover; code migration not yet started.


- **Stephan's answers and workaround scope** `[Codex / GPT-6, exact variant not exposed]`
  (Status: completed documentation update): Recorded Q1–Q4 in the review, DM-02, backlog,
  data model and handover; added the operating scope to AGENTS.md. XLSX remains the shared
  source, customer corrections trigger a complete disposable SQLite rebuild. Skip unusable
  invoices with a warning and continue; use today's index child; report each Betreuung,
  without duplicates solely from follow-up mandates. Introduction is split manually in the
  timesheet. Stephan corrected his initial exclusion instruction: «Ohne Berechnung» remains
  a visible invoice position with amount 0 CHF. Existing invoice code already supports this;
  no automatic ST99/entry-month rule or persistence added. Removed extra hash-register and
  audit-package requirements from the review. Technical Accordix grouping remains a draft,
  not a completed DM-40 implementation. No runtime code or workbook changed.
  Verification: `nox` lint passed, pyright 0 errors/0 warnings; `git diff --check` passed.

- **Plan review and Opus task specification drafts** `[Codex / GPT-6, exact variant not exposed]`
  (Status: draft, Opus review pending): Added `docs/dev/plan_review_2026-10-10.md` and linked it
  from the backlog. Reviewed the handover, DM-02/04, model/concept/runbook and affected source
  modules. Draft contracts cover DM-12, DM-15, DM-22, DM-34/41, DM-40, DM-07/43 and DM-70;
  no existing task closed. Findings: editable-only import omits two calculated foreign keys;
  SQL lacks Excel row order; legacy mapping would disappear with the sandbox; per-row mandate
  resolution requires moving header-level tariff/budget lookups; invoice comparison must allow
  a changed QR reference; ST99 denotes PRIVAT in the model, so the introduction rule needs an
  identification contract. Four questions sent to Stephan, awaiting answers. No workbook,
  customer data or runtime code changed. Verification: `nox` lint passed, pyright 0 errors,
  0 warnings; `git diff --check` passed before commit. Final build, actual invoice/Accordix
  comparison and Windows Excel acceptance remain outstanding.

## 2026-10-09

- **Korrektur: Berichte und Folgeaufträge doch übernehmen** `[Opus 5.5]` (Status: erledigt):
  Stephan: Berichte und Auftragsverkettung übernehmen, aber als «zu prüfen» markieren. DM-04:
  `FOLLOW_UPS` bleibt (mit der Korrektur der Vorgängernummer bei C1024), Berichte über
  `carry_over_handwork` (ohne Familie und Rolle). Markierung: fester Vorsatz `ZU PRÜFEN:` in der
  Bemerkung, neue Hinweis-Prüfung «Übernommene Angabe zu prüfen» (Invariante 50), verschwindet,
  sobald der Vorsatz gelöscht ist. Erwartet: 94 Aufträge, 153 Berichte, 6 markierte Aufträge.
  `import_reports.py` hat damit weiter keinen Zweck (die Berichte stehen schon im Testbuild).

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
