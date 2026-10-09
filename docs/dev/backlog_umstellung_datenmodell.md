# Backlog: Umstellung auf Kinder, Aufträge und Betreuungen

Stand 2026-10-09. Plan für die finale Umstellung der Programme und Daten auf das vom Kunden
bestätigte Modell. Fachliche Grundlage: [Konzept](../konzept_person_auftrag_leistung.md),
[Datenmodell](../datamodel_person_mandate_care.md), [Runbook Umstellung](../runbook_umstellung_datenmodell.md).
Der Fortschritt steht im [Umsetzungslog](umsetzungslog_umstellung_datenmodell.md); wer übernimmt,
liest zuerst dessen Abschnitt «Übergabe».

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

Regeln für den Modellwechsel:

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

Empfehlung: **beides, Sicherung und neuer Branch.** Der Grund ist der Monatslauf: Rechnungen und
Erfassungsbögen müssen während der Umstellung weiter aus dem alten Modell entstehen. Das geht nur,
wenn der Produktivstand auf einem eigenen Branch bleibt und die Umstellung daneben läuft.

- Tag `pre-datamodel-v2` auf dem heutigen Produktivstand. Er ist der Rückweg, unabhängig von
  allem, was danach auf einem Branch passiert. Ein zusätzlicher Backup-Branch bringt gegenüber
  dem Tag nichts.
- Umstellung auf `feature/datamodel-v2`. Monatsläufe und Notfixes laufen weiter auf `main`
  und werden bei Bedarf in den Feature-Branch übernommen.
- Merge in `main` erst nach der Generalprobe (DM-51), danach Tag `datamodel-v2`.

Ausgangslage am 2026-10-09: `main` steht auf `50ffaa5`. Der ausgecheckte Branch
`fix/sa-sentinel-client` ist 16 Commits weiter (SA-Sentinel-Fix, Modell-Dokumente,
Sandbox-Skripte), alle gepusht, nicht gemergt. Er ist der eigentliche Produktivstand.

## P0 Must

### Phase 0: Vorbereitung

- [ ] [P0] [Git] **DM-00** Produktivstand sichern und Umstellungsbranch anlegen. `[Stephan]` für die Freigabe, Ausführung `[Haiku]`. Hinweis: zuerst `fix/sa-sentinel-client` nach `main` mergen (Fast-Forward, nur Docs, Sandbox und der SA-Fix), dann Tag `pre-datamodel-v2` auf `main`, dann `feature/datamodel-v2` von `main`. Tag und Branch erst nach Freigabe pushen.
- [ ] [P0] [Governance] **DM-01** Ausnahme von AGENTS.md «Betriebsstabilität» festhalten. `[Stephan]`. Hinweis: Die Umstellung ist absichtlich destruktiv (Tabelle `clients` und `relation_client_emp` entfallen) und bricht das bisherige Importformat. Beides verbietet AGENTS.md heute. Stephan genehmigt die Ausnahme für diesen Branch; der Satz kommt als Abschnitt in AGENTS.md (Text vorbereiten: `[Haiku]`).
- [ ] [P0] [Fach] **DM-02** Offene Fachfragen nach «blockiert die Umstellung» und «kann warten» sortieren. `[Opus]`, Antworten `[Stephan]` mit Wegpiraten. Hinweis: Blockierend nach heutiger Lesart: KOB (`ST09`) ohne Accordix-Zuordnung (melden oder ausschliessen), die Folgeaufträge Duarte Torres und Loosli (Ende alt, Beginn neu), Rechnungsnummer-Wechsel C→A gegenüber KJA-FS und KESB ankündigen. Kann warten: Fragen 10–14 im Datenmodell (KESB-Nummern, Berichtsformen, Rhythmen, Abschlussbericht, Erledigt-Stand). Ergebnis als Liste im Log.
- [ ] [P0] [Fach] **DM-03** Einführungsgespräch (ST99) im neuen Modell festlegen. `[Opus]`, Bestätigung `[Stephan]`. Hinweis: Die Regel liest heute `clients.start_date`. Im neuen Modell gibt es drei Kandidaten: Beginn des Auftrags, Eintritt der Betreuung, Beginn des ersten Auftrags der Kette. Vorschlag: Eintritt des Indexkindes (der bleibt bei Verlängerungen gleich), sonst gäbe jede Verlängerung erneut 15 Gratisminuten.
- [ ] [P0] [Daten] **DM-04** Datenstand für den finalen Build zusammenführen. `[Opus]`. Hinweis: Die Stammdaten werden weiter in `sandbox/wegpiraten_datenbank.xlsx` gepflegt (Stand 09.10.), die Handarbeit (Familien, Rollen P/S, Berichte, Korrekturen) liegt in `sandbox/wegpiraten_datenbank_neu.xlsx` (Stand 30.09.). Ein Neubau aus der alten Datei allein verliert die Handarbeit. `migrate.py` und `build.py` lesen noch `wegpiraten_datenbank(1).xlsx`, die es nicht mehr gibt. Spezifikation ins Log: Quelle je Blatt, was `carry_over_handwork` heute übernimmt und was fehlt, wie Klienten behandelt werden, die nach dem 24.09. dazugekommen sind oder sich geändert haben. `mandate_numbers.json` bleibt eingefroren, neue Aufträge bekommen den nächsten freien Zähler.
- [ ] [P0] [Daten] **DM-05** Finalen Build ausführen und Differenz belegen. `[Sonnet]`, Spezifikation: DM-04. Hinweis: Skriptpfade umstellen, Build laufen lassen, Zählung (Kinder, Aufträge, Betreuungen, Zuordnungen, Berichte) und jede geänderte oder neue Zeile gegenüber `_neu.xlsx` ins Log. Danach Blatt «Prüfungen» auswerten: Fehler und Hinweise zählen.
- [ ] [P0] [Daten] **DM-06** Workbook in echtem Excel prüfen. `[Stephan]`. Hinweis: LibreOffice sieht die Excel-Defekte nicht (siehe Datenmodell, «Excel-specific decisions»). `sandbox/excel_pruefung.ps1` unter Windows, Dropdowns und Prüfungen stichprobenweise.

### Phase 1: Schema und Stammdaten-Import

- [ ] [P0] [Config] **DM-10** Entitätsmodelle in `.config/wegpiraten_config.yaml` anlegen: `person`, `mandate`, `mandate_person`, `contact_person`, `mandate_employee_relation`, `report`. `[Haiku]`. Hinweis: Feldnamen, Typen und Pflicht genau aus den Tabellen im Datenmodell, Abschnitt «Entities». Nur Spalten, die im Workbook editierbar sind; die grauen `▸`-Spalten werden nicht importiert. `client` und `client_employee_relation` bleiben bis DM-53 stehen.
- [ ] [P0] [Import] **DM-11** `import_masterdata.py` auf die neuen Blätter umstellen. `[Sonnet]`. Hinweis: `DEFAULT_TABLE_MAPPINGS` und `FOREIGN_KEY_MAPPINGS` (Reihenfolge: Stammdaten → `masterdata_contact_person` → `person` → `mandate` → `mandate_person` → `relation_mandate_emp` → `report`). Leere Reservezeilen (das Workbook hat 2000 Formelzeilen) überspringen. FK-Diagnostik bleibt.
- [ ] [P0] [Schema] **DM-12** Abgeleitete Felder als SQL-View `v_mandate` spezifizieren. `[Opus]`. Hinweis: `index_person_id` (jüngstes Kind der Familie der Betreuungskinder, sonst das Kind selbst; bei gleichem Geburtsdatum dieselbe Regel wie im Workbook), `short_code` und `last_name/first_name/social_security_number` des Indexkindes, `sr_ap_gender/first_name/last_name` der Ansprechperson, Budget in Minuten. Die View muss für jeden Auftrag dasselbe Indexkind liefern wie das Workbook; Abgleich gehört zur Spezifikation.
- [ ] [P0] [Schema] **DM-13** View `v_mandate` umsetzen und gegen das Workbook prüfen. `[Sonnet]`, Spezifikation: DM-12. Hinweis: Test vergleicht View-Spalten mit den berechneten Spalten des Workbooks für alle Aufträge.
- [ ] [P0] [Import] **DM-14** Synthetisches Test-Workbook ohne Personendaten. `[Sonnet]`. Hinweis: kleiner Ausschnitt mit den Fällen aus dem Konzept: Geschwister mit Indexkind, Kind mit zwei Aufträgen, Folgeauftrag, Vertretung (zwei MA, eine mit P), Austritt, SA-Sentinel. Erzeugt mit `build.py` aus einer erfundenen `migration_v2`-Datei, liegt unter `tests/fixtures/`. Grundlage für alle Tests ab hier.
- [ ] [P0] [Import] **DM-15** SA-Sentinel im neuen Modell. `[Opus]` entscheidet, `[Sonnet]` setzt um. Hinweis: `internal_client.py` legt heute einen Klienten `SA` an. Vorschlag: ein Auftrag `SA` ohne Kind und ohne Betreuung, von Invariante 8 ausgenommen, nie fakturiert, nie gemeldet. Betrifft Import, Bogenerzeugung und Rechnungsfilter.
- [ ] [P0] [Import] **DM-16** Fehler-Invarianten beim Import prüfen. `[Sonnet]`. Hinweis: Import bricht ab bei den Invarianten mit Schwere `error`, die Rechnung oder Bogen falsch machen (1–5, 8–13, 28, 29, 45, 48). Hinweise nur ins Log. Gleiche Nummern wie im Datenmodell, damit die Meldung auf die Regel zeigt.

### Phase 2: Zeiterfassung

- [ ] [P0] [Zeiterfassung] **DM-20** Bogenerzeugung auf Aufträge umstellen. `[Sonnet]`. Hinweis: `time_sheets/modules/client_data.py` liest `relation_mandate_emp` + `v_mandate` statt `relation_client_emp` + `clients`. Ein Bogen je Zeile der Zuordnung, wie bisher. Zelle G8 trägt die Auftragsnummer, C8 das Kurzzeichen des Indexkindes, Budget aus dem Auftrag. Dateiname `{employee_id}_{mandate_id} ({short_code})_{YYYY-MM}.xlsx`. Aufträge mit abgelaufener Bewilligung erzeugen keinen Bogen mehr (Invariante 31 als Warnung ins Log).
- [ ] [P0] [Zeiterfassung] **DM-21** Beschriftung im Bogen-Template prüfen. `[Haiku]`. Hinweis: Steht im Kopf «Klient-Nr» neben G8, wird es «Auftrag-Nr». Nur Text, keine Zellverschiebung (`header_cells.py` bleibt gültig).
- [ ] [P0] [Import] **DM-22** Zuordnung alter Nummern beim Bogen-Import spezifizieren. `[Opus]`. Hinweis: Archivierte und noch ausstehende Bögen tragen `C…` in G8. Die Zuordnung C→A ist nicht immer eindeutig: bei nachgetragenen Folgeaufträgen (Yahia, Nipote, Gorlov, Richards) entscheidet das Leistungsdatum, welcher Auftrag gilt. Quelle ist `mandate_numbers.json` plus die Bewilligungszeiträume. Unauflösbar = fataler Fehler mit Datei und Zeile, kein stilles Raten.
- [ ] [P0] [Import] **DM-23** `batch_import_timesheets.py` auf `mandate_id` umstellen. `[Sonnet]`, Spezifikation: DM-22. Hinweis: `service_data.client_id` wird `service_data.mandate_id` (FK auf `mandate`), Budgetspalten bleiben. Bögen mit `C…` laufen über die Zuordnung aus DM-22. Tests mit je einem Bogen alter und neuer Form.

### Phase 3: Rechnung

- [ ] [P0] [Rechnung] **DM-30** `invoice_processor.py` auf Aufträge umstellen. `[Sonnet]`. Hinweis: `JOIN clients` → `JOIN v_mandate`. Gruppierung bleibt je Auftrag (siehe Datenmodell, «What the invoice number names»), Kostenträger, Besteller, Ansprechperson und Standort vom Auftrag, Name und AHV-Nummer vom Indexkind. Kontextfelder (`client_name`, `client.social_security_number`, `sr_ap_*`) behalten ihre Namen, damit `rechnungsvorlage.docx` unverändert bleibt. Einführungsgespräch nach DM-03.
- [ ] [P0] [Rechnung] **DM-31** Rechnungsnummer aus der Auftragsnummer. `[Sonnet]`. Hinweis: entsteht von selbst aus `service_data.mandate_id` (`2026-11-A26001`). `generate_scor` mit den neuen Nummern testen. Dateiname `{invoice_id}_{von}_{bis}_{application_number}` bleibt; die KJA-FS-Upload-Konvention prüfen (`_` als Trenner).
- [ ] [P0] [Rechnung] **DM-32** Rechnungsfilter `CLIENT=` erweitern. `[Sonnet]`. Hinweis: `invoice_filter.py` nimmt A-Nummern (ein Auftrag) und C-Nummern (alle Aufträge, deren Indexkind das Kind ist). Makefile-Hilfe nachziehen.
- [ ] [P0] [Rechnung] **DM-33** Rechnungsübersicht (`document_utils.py`) um Auftragsnummer ergänzen. `[Haiku]`. Hinweis: Spalte «Auftrag» vor «Klient», «Klient» zeigt das Indexkind. Sonst keine Änderung am Layout.
- [ ] [P0] [Rechnung] **DM-34** Paralleler Rechnungslauf alt gegen neu. `[Opus]` legt fest, was gleich sein muss, `[Sonnet]` schreibt den Vergleich, `[Stephan]` nimmt ab. Hinweis: ein abgeschlossener Monat (Vorschlag 2026-09) einmal mit `main` und einmal mit dem Feature-Branch. Beträge, Stunden, Positionen, Empfänger und QR-Daten je Rechnung gleich; erlaubt verschieden sind nur Rechnungsnummer, Referenz und Dateiname. Jede andere Abweichung ist ein Fehler oder eine im Log begründete fachliche Änderung.

### Phase 4: Reporting

- [ ] [P0] [Report] **DM-40** Accordix-Meldung aus den Betreuungen. `[Opus]` spezifiziert, `[Sonnet]` setzt um. Hinweis: `reports/accordix_report.py` liest heute eine Zeile je Klient; neu ist jede Zeile von `mandate_person` eine Meldezeile, Eintritt und Austritt von der Betreuung, Leistungsart und Kostenträger vom Auftrag. Die Sonderregel für Austritt = Bewilligungsende entfällt. KOB nach DM-02.
- [ ] [P0] [Report] **DM-41** Abgleich Accordix August 2026. `[Opus]`. Hinweis: neue Meldung gegen `sandbox/Import-Accordix_ambulant_August_2026.xlsx`. Jede Abweichung erklären: zusätzliche Geschwister und getrennte Austritte sind gewollt, alles andere nicht.
- [ ] [P0] [Report] **DM-42** Arbeitszeitprotokoll auf Aufträge umstellen. `[Haiku]`. Hinweis: `reports/arbeitszeit_report.py`, ein JOIN (`clients` → `v_mandate`); im Detailblatt Auftragsnummer und Indexkind zeigen.
- [ ] [P0] [Report] **DM-43** `utils/extend_masterdata_accordix.py` stilllegen oder anpassen. `[Opus]` entscheidet, `[Haiku]` führt aus. Hinweis: Das Skript ergänzt die alte Klientenliste um Accordix-Spalten. Diese Felder sind jetzt Teil von Kinder und Betreuungen; das Skript ist vermutlich überflüssig.

### Phase 5: Umstellung

- [ ] [P0] [Doku] **DM-50** Betriebs-Runbook auf das neue Modell umschreiben. `[Sonnet]`. Hinweis: `docs/runbook_betriebsablauf.md` und die Kapitel «Für die Umsetzung in den Programmen» im Umstellungs-Runbook; AGENTS.md und CLAUDE.md (Projektübersicht, Datenmodell) nachziehen.
- [ ] [P0] [Betrieb] **DM-51** Generalprobe auf einer Kopie. `[Stephan]` mit `[Sonnet]`. Hinweis: kompletter Monat auf dem Feature-Branch mit dem finalen Workbook: `import-master`, `timesheets`, `import-sheets`, `invoices`, `report`, `accordix`. Eigene Datenbank-Datei, Produktiv-DB unberührt.
- [ ] [P0] [Betrieb] **DM-52** Stichtag festlegen und Stammdatei umschalten. `[Stephan]`. Hinweis: Ab dem Stichtag wird nur noch das neue Workbook gepflegt. Empfehlung: Es übernimmt den Namen `wegpiraten_datenbank.xlsx` im Proton-Drive, die alte Datei wird als `wegpiraten_datenbank_alt.xlsx` archiviert; dann bleibt `masterdata_source` in der Config unverändert. Stichtag nach einem Monatslauf, nicht mitten im Monat.
- [ ] [P0] [Git] **DM-53** Merge nach `main`, Tag `datamodel-v2`. `[Stephan]`. Hinweis: erst nach DM-34, DM-41 und DM-51. Danach `client`/`client_employee_relation` aus der Config und `clients`/`relation_client_emp` aus dem Code entfernen (`[Haiku]`, eigener Commit).

## P1 Should

- [ ] [P1] [Daten] **DM-60** Altdaten bereinigen, die die Prüfungen aufdecken. `[Stephan]` mit Wegpiraten. Hinweis: 14 KJA-Aufträge mit «beendet» statt Geschäftsnummer, Stauffer-AHV, Rollen P ohne Eintrag, Berichtsstatus der Vergangenheit. Das ist der Zweck der Übung, kein Fehler des Builds.
- [ ] [P1] [Import] **DM-61** Workbook-Prüfungen und Python-Prüfung abgleichen. `[Sonnet]`. Hinweis: Hinweis-Invarianten (14–36) zusätzlich im Import als Warnung ausgeben, damit eine im Workbook übersehene Prüfung im Log steht.
- [ ] [P1] [Doku] **DM-62** Sandbox-Skripte nach der Umstellung einordnen. `[Opus]`. Hinweis: `migrate.py` und `prepare.py` sind nach dem Stichtag erledigt; `build.py` bleibt, solange Strukturänderungen am Workbook über einen Neubau laufen. Entscheiden und im Umstellungs-Runbook festhalten.

## P2 Nice

- [ ] [P2] [Report] **DM-70** Monatliche Aufgabenliste je Mitarbeitende («Terminzettel»). `[Opus]` spezifiziert, `[Sonnet]` setzt um. Hinweis: aus `report`, zuständig ist die Person mit Rolle P. Eigenes `make`-Target neben den Erfassungsbögen, nicht in deren Lauf (Wunsch von Wegpiraten). Bewusst erst nach einer Runde echter Nutzung der Berichtsliste und nach den Fragen 11–14.
- [ ] [P2] [Rechnung] **DM-71** Folgeauftragskette auf der Rechnung oder in der Übersicht sichtbar machen. `[Sonnet]`. Hinweis: nur wenn Wegpiraten es wünscht; heute nicht verlangt.

## Abhängigkeiten

```
DM-00 ─┬─ DM-01
       └─ DM-02 ─┬─ DM-03 ──────────────── DM-30
                 └─ DM-04 ─ DM-05 ─ DM-06
DM-10 ─ DM-11 ─┬─ DM-12 ─ DM-13 ─┬─ DM-20 ─ DM-21
DM-14 ─────────┘                 ├─ DM-22 ─ DM-23
DM-15 ───────────────────────────┤
                                 ├─ DM-30 ─┬─ DM-31, DM-32, DM-33
                                 │         └─ DM-34
                                 └─ DM-40 ─ DM-41;  DM-42, DM-43
DM-34, DM-41, DM-06 ─ DM-50 ─ DM-51 ─ DM-52 ─ DM-53
```

Was ohne Antwort von Wegpiraten beginnen kann: DM-10 bis DM-16, DM-20 bis DM-23, DM-30 bis
DM-33 und DM-42. Was auf Antworten wartet: DM-03, DM-04 (Folgeaufträge), DM-40 (KOB).
