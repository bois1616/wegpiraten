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
normal operation. **Updated after Stephan’s feedback on 2026-10-10:** DM-60 test
handover is complete. Stephan has also tested the result himself without findings
so far. Customer feedback and final acceptance/delivery DM-52 remain open; the
exact scope of his tests does not confirm formal Windows Excel DM-06 or full
operator rehearsal DM-51.
Historical `sandbox/` references below document former paths, not active dependencies.

DM-70 completed on 2026-10-10 at Stephan's explicit request, superseding the earlier
wait-for-real-use condition. `make terminliste MONTH=2026-10` creates one XLSX per
employee from the imported report list. Assign through role P; log and skip entries
without an unambiguous existing primary employee. See the implementation log for
selection rules and validation.

## Plan 2026-10-11: customer workbook review and requested additions

### Implementation checkpoint 2026-10-12

Excel opening at 14:34 failed after consolidation. Inspection found an orphan
shared formula in Fehlerliste M10 caused by overwriting its M2 anchor. Restored
from the preserved source; future partial edits expand shared formulas first.
General review now rejects missing shared anchors; two regression tests added.
The 14:44 repeat still failed; Excel's repair log identified invalid styles.xml.
Corrected the new instruction style's XML child order. The 14:52 Windows check
then opened all 21 sheets without repair and found no formula errors after full
rebuild, 34 runtime names and the five sampled dropdown formulas. Diagnostics:
five open error checks and 72 records with findings. Full DM-80/06 acceptance
still requires the manual editing checks below.

**Revised assignment source, Stephan 2026-10-12:** remove the duplicate empty
Zuständigkeitsverlauf source. Zuordnung MA is the sole relation table, with optional
valid_from/valid_to in D:E after the input-column grouping on 2026-10-12.
Blank bounds are unbounded; old rows continue unchanged.
A change ends the old row and adds a new row; historical roles and support rows
must remain. Report assignment uses due_date, monthly timesheets use interval
overlap and one header per mandate/employee. Distinct periods of a returning
employee survive import. Customer-edited sheet order and tab colours are retained.
The maintenance rule is embedded in Anleitung and the runbook. The 14:52 Windows
automatic pass applies to this consolidated workbook.

Windows automatic check passed on 2026-10-12 at 10:36: no Excel repair or formula
errors after full rebuild, 22 sheets opened, names present and sampled dropdowns
valid. Remaining Windows acceptance concerns manual insertion/deletion/sorting,
new-row autofill and the new input/comment/link interactions. DM-06 stays open
until those checks are confirmed; customer data correction is a separate task.

DM-80/82 are implemented locally: repaired native formulas, zero errors after
LibreOffice recalculation, stable Prüfkatalog with all six customer comments and
linked findings. Windows Excel acceptance (including table insertion/deletion/sort)
remains open. DM-83 and the authorised two-table refinement of DM-85 are implemented
in Config, importer, diagnostics and a separate customer-workbook copy. Empty new
tables remain optional; no adult/family data were inferred. Original source and live
SQLite were not changed. Customer corrections DM-81 remain open.

General review of the prepared copy: no technical defects and 13 customer-data
findings. Additional domain warnings are retained in the import finding list.
Isolated real-data import succeeded: 637 imported records, 144 of 146 report rows
(two duplicate report IDs skipped with warnings), eleven employee lists and the
employee overview generated. No interval-generated report rows exist.

Delivery: ignored output/uebergabe_stammdaten_2026-10-11/wegpiraten_datenbank.xlsx,
with UEBERGABE.md and review/evidence manifests. A new general review is required
after customer edits and before the next import. The task descriptions below retain
the original proposal; the two-table contact refinement supersedes the earlier
per-child duplication proposal.

Status: proposal requested by Stephan, not implementation approval. New entries follow
the English journal seam above. This section processes every customer note in
`Prüfungen!G:G`; the source workbook and its notes have not been overwritten.
Resolve the workbook defects first, then add contact data, dated responsibility and
the annual report overview. Keep the scope appropriate to the temporary v1 system.

**Update after Stephan's decisions, 2026-10-11:** the original proposal below is
retained as its planning baseline. Stephan requested implementation of the employee
overview and decided that report responsibility uses **due_date**. Responsibility is
derived in both outputs from source-maintained assignment periods; no report writer
updates the XLSX and no durable state is expected in SQLite. DM-84's date choice is
settled. Parents/guardians/placements need only currently supplied data; missing
history is accepted and changing guardian responsibilities is deferred. That
narrows DM-85's proposal for mandatory placement/history semantics.

DM-86 is implemented as `make klientenuebersicht MONTH=2026-10`, rather than the
earlier YEAR proposal: one workbook with employee sheets, a preceding Legende,
Berichtsdetails and Nicht zugeordnet. No Übersicht sheet. The repeated name pairs
formerly O/P and AC/AD are removed; the month blocks now start at O and AA. Row 1
has no legend. G:N show fresh imported data for the explicitly identified mandate;
parallel and follow-up mandates retain separate rows. J:M are clearly defined as
current monthly authorised hours, not inherited meanings of the old abbreviations.
All explicit report entries are retained in details, including completed/cancelled
and out-of-grid entries. Employee grids include assigned report dates in the stand
year/following year. These exports are regenerated output, not another data source.

DM-84 implementation is complete for optional `assignment_history` import and a
shared due-date resolver used by DM-70 and DM-86. Periods remain in the customer
XLSX; the customer workbook has not been expanded or imported in this session.
The runbook defines the new table. Missing history uses current P with an explicit
historical-unknown label; gaps/overlaps in supplied history never use that fallback.
Contact phone/email import support is added for the report, but adding those columns
to the customer workbook and the remaining payer-email part of DM-83 remain open.
DM-80/82 and customer corrections DM-81 remain open; no repair is implied by these
report changes. Synthetic end-to-end import/report tests require no customer fake data.

Operating clarification from Stephan, 2026-10-11: customer data corrections happen
later and do not block technical implementation. A current `make import-master`
failure due to unresolved data is accepted. Do not run another customer-workbook
import before the agent has performed a general review of the then-current source:
tables/columns, formula integrity and coverage, calculated references, duplicate and
missing keys, FK completeness, dates, diagnostic coverage and preservation of
customer input. Record remaining findings explicitly. Synthetic implementation
tests may run independently; a successful real-data import is not a prerequisite
for implementing DM-80/82/83. The review must not silently correct customer data.

### Proposed handover sequence and contact relationships, 2026-10-11

Stephan will return an expanded workbook **based on the current customer revision
in import/wegpiraten_datenbank.xlsx** after the technical conversion, so the customer
can continue entering/correcting data. It is not a generated employee overview or
a rebuild from migration seeds. Preserve all customer input; back up and retain the
source hash, compare input fields before/after each technical patch, and deliver
the working master workbook separately from generated reports. Formula repair,
new source tables and their dropdowns/checks are still outstanding.

Recommended order: DM-80 formula integrity, DM-82 diagnostics and fixed comments,
then source-workbook history/contact additions plus the remaining importer fields,
then synthetic editing/pipeline checks and a full general review of the prepared
customer workbook. Provide the outstanding customer-data findings alongside the
handover copy. Customer corrections may follow; failures due to those data remain
accepted. After correction, review the then-current file again before its next
import and verify real report output in an isolated DB. Windows Excel opening,
new-row formulas and dropdown acceptance remain necessary for the source workbook.

**Refinement proposed for DM-85, not yet implemented:** use two small source tables:
`Bezugspersonen` (`related_person`) with stable `related_person_id`, name, current
address, phone, optional email and notes; and `Kind–Bezugsperson`
(`person_related_person`) with stable relationship ID, `person_id`,
`related_person_id`, relationship role and explicit guardianship status
Ja/Nein/Unbekannt. Several children can reference the same adult without copying
phone/address data. A child can have several adults. Parent/guardian roles belong
to the child/adult relationship, not to an assumed family-wide contact. No
historical relationships or addresses are required. Internal employee responsibility
remains the mandate assignment/history and is not merged with these domain contacts.

The existing sibling label in `Kinder.family_id` continues to serve index-child
selection. Shared adults, surnames or addresses do not create family membership.
Adding a family table is unnecessary for these contact requirements alone; propose
it only when there are independent family-level properties to maintain. If that
later happens, map existing labels explicitly onto stable family IDs and preserve
the child groups/index-child results during the conversion. A family table would
still not replace child-specific adult relationships. This refinement supersedes
the earlier DM-85 suggestion of duplicating an adult contact row per child if
Stephan approves it; do not start a family-key migration on the current proposal.

Stephan clarified that the assumed Nipote grouping was his demonstration, not a
confirmed customer relationship. No grouping, parent links or contact records are
to be populated from that example. Current/past placement data can be entered
where known; absent history and changes in guardian responsibility remain outside
the required scope.

### Evidence from the initial customer revision

Reviewed `import/wegpiraten_datenbank.xlsx` against the handover workbook in
`output/uebergabe_datenmodell_2026-10-10/`. Customer revision SHA-256:
`b671fd25324368b9e020f7f2ceb26b94ae64ae3fc43c8b3f07fcd810db95aa09`.
Read formulas, stored results, table definitions and raw input fields separately.
No import into the live DB, recalculation in Windows Excel or financial acceptance
was performed. Stored results are evidence of the last save, not a fresh Excel run.

All eleven required import tables and their configured columns exist. Actual input
records, excluding empty rows containing only helper formulas:

| Entity | Handover | Customer revision | Observation |
| --- | ---: | ---: | --- |
| Kinder | 87 | 86 | C1063 removed; several personal-data fields corrected |
| Aufträge | 94 | 94 | A26019 removed, A26050 added; numbers, dates and budgets edited |
| Betreuungen | 94 | 94 | A26019/C1063 replaced by A26050/C1061; exit data edited |
| Zuordnung MA | 101 | 102 | A26050/M011 added; 24 existing roles changed |
| Ansprechpersonen | 49 | 49 | One salutation and one note changed |
| Berichte | 153 | 146 | 144 distinct IDs, two duplicate IDs; forms/dates/status edited |

Mitarbeiter (11), Kostenträger (14), Leistungsbesteller (26), Büros (2) and
Leistungstypen (15) retain their imported input fields. No unknown non-empty FK,
contact/requester mismatch or reversed care/mandate date interval was found in the
reviewed records. Empty required references are listed below rather than counted
as valid FKs. Customer edits are not automatically approved or reverted.

Concrete findings:

1. **Broken Fehlerliste is a formula defect.** Fifteen formulas contain literal
   `#REF!`: `Aufträge!AP56`, `Betreuungen!AD67,AD94`, and
   `Berichte!T4,T8,T10,T13,T39,T50,T52,T53,T62,T94,T115,T142`.
   These `issue_run` formulas reference a missing predecessor cell. Their errors
   propagate into `Fehlerliste!L1:L7`, the offsets and the displayed rows. Stored
   error cells total 5,623: Aufträge 1,944, Betreuungen 1,932, Berichte 137,
   Fehlerliste 1,610. Row deletion/movement is a plausible trigger, not proven
   editing history. Hiding errors with `IFERROR(...,0)` would lose findings.
2. **Missing formulas on added report rows.** `Berichte!C44` (R154), `C45`
   (R155), and `C147` (R126) are blank although column B contains A24014,
   A24014 and A26046 respectively. Several diagnostic formulas are also missing
   in these rows, and most display helpers are absent in row 147. The importer
   reads column C, not the visible selection B. These reports lose their mandate
   link; the current diagnostics do not catch an empty report FK.
3. **Duplicate report IDs.** R076 occurs in rows 141/146 for A26042/A26046;
   R126 occurs in rows 142/147 for A26042/the visible choice A26046. They are
   different appointments. The importer keeps the first row and omits the second,
   so customer-confirmed unique IDs are required. Do not delete the appointments
   or renumber them silently. The fixed 43-check catalogue omits report-ID
   duplicates, missing report references and status findings, despite some of
   these checks existing in row helpers.
4. **A26050, Aufträge row 60:** Leistungsbesteller, Kostenträger and
   Geschäftsnummer are empty; Ansprechperson is also absent. It has care,
   employee and report records. Filling only the Geschäftsnummer is insufficient
   for invoicing. A26009 (row 14) and A26048 (row 76) have P1000 number placeholders,
   not valid nine-digit business numbers. Keep these as unresolved customer data.
5. **Follow-up closing reports:** R066/A24014 (`Berichte!43`) and
   R068/A26037 (`Berichte!137`) are Abschlussberichte on predecessor mandates.
   Check whether they should be reclassified or assigned to the last mandate;
   preserve the customer date until confirmed.
6. **Other findings:** 12 expired mandates still have open care, 30 employee
   assignment rows refer to expired mandates, and 22 reports marked `offen`
   are due before 2026-10-11. There are 38 reports without status, which does not
   establish completion. Five mandates have no employee assignment at all:
   A24015, A26004, A26010, A26040, A26048; none currently has a report row.
   The displayed missing-P count of zero therefore does not cover all mandates.
7. **Planned exits falsely flagged:** all 14 care records flagged for a missing
   Austrittsgrund have `is_leaving_reason_planned = Ja`. The existing local
   [Accordix mapping](../accordix_mapping.md) requires `leaving_reason` only for
   an unplanned exit. This is a check defect, not fourteen missing customer values.

### Disposition of the comments in Prüfungen column G

The references below describe the saved revision. A7:E49 is a dynamically compacted
list, while G contains fixed text. After a finding disappears, a note can stand next
to another check. Preserve these comments with a stable check ID before any repair
and recalculation. Resolve them in a fixed catalogue/comment table; the open view
looks up the comment by ID. Findings should carry check ID, record ID, sheet, current
row and an internal hyperlink. Row numbers are navigation aids, not identities.

| Source | Customer comment (verbatim) | Proposed treatment |
| --- | --- | --- |
| G7 | Finde die passenden Einträge nicht | List R066/A24014 and R068/A26037 explicitly and link to their rows. Repair Fehlerliste first; retain the closing-report rule pending customer classification. |
| G8 | Nummern werden nach gereicht | Retain the missing-number finding for A26050. Also show its missing payer/requester. Close only after workbook correction and recheck. |
| G9 | Nummern werden nach gereicht | Retain invalid-number findings for A26009/A26048. No invented number and no disabling validation while awaiting delivery. |
| G11 | Nur wenn Austrittsgrund "Nein" ist, dann kommt ein Austrittsgrund | Interpret as **Austritt geplant = Nein** (column E), not a value of Austrittsgrund (column F). For an exit, require Ja/Nein; require reason for Nein, custom reason for Anderer. Ja needs no reason. Match workbook and Python warnings. |
| G12 | wäre coool wenn man direkt sieht welche das betrifft, so muss ich zwischen den tabellen hin und her switchen | Show affected IDs/names and clickable findings, filtered by check. Current IDs: A26014, A26029, A23005, A26037, A26040, A26030, A24005, A26024, A26017, A26031, A26032, A24014. No automatic exit or authorisation extension. |
| G14 | korrekt | Treat as acknowledgement, not permission to invent an Accordix mapping. The three flagged types are ST00/UNBEKANNT, ST02_alt/BBT and ST09/KOB. Separate known inactive/unused placeholders from actual P1000 reporting gaps; retain explicit warnings for unmapped reportable care. |

### Proposed implementation tasks

- [ ] [P1] [Report] **DM-87** Produce a complete client data report grouped by
  the employee assigned with role P in Zuordnung MA. Requested by Stephan on
  2026-10-12. Include all clients, including those without report appointments;
  the existing DM-86 appointment overview does not cover this requirement.
  Show child and sibling/index-child information, residence, related people
  with child-specific relationship and guardianship, known placements, mandates,
  care periods, quotas, requester/contact details, payer and relevant report
  appointments. Resolve P against an explicit report reference date; expose
  missing or ambiguous assignments in a separate unassigned section instead of
  selecting an arbitrary employee or omitting clients. Keep separate child,
  relationship, placement and mandate records visible without multiplying quota
  totals through joins. Name the date and output scope in the report. Do not
  infer family membership from shared adults, surnames or addresses. Acceptance:
  clients without appointments, several related people, several placements,
  siblings and missing/overlapping P assignments remain complete and traceable.

- [ ] [P0] [Workbook] **DM-80** Repair diagnostics on a backed-up copy of the
  customer revision. `[Sonnet]`. Replace predecessor-dependent `issue_run`
  formulas with a cumulative count of non-empty `issue_kind` cells from the first
  data row to the current row. This removes the reference to a deletable preceding
  row; row 4 must not count its header. Refill missing calculated cells across
  actual table rows, preserve all input fields and comments, and check the
  diagnostic ranges beyond the last input row. Use structured table references
  where Excel supports them and explicitly test insert/delete/sort and new rows.
  Do not rebuild from archived migration JSON or overwrite customer work with
  the old handover file. Check that conditional formatting, dropdowns, named
  ranges, table metadata and print settings survive the chosen patch method.
  Acceptance: no formula errors after Windows Excel full recalculation; insert,
  delete, sort and add a report row without missing FKs or losing findings.

- [ ] [P0] [Data] **DM-81** Resolve the customer data findings above. `[Stephan]`
  with Wegpiraten. Assign distinct IDs to the two added appointments, confirm
  the three missing report links, complete A26050's payer/requester/number and
  the two P1000 number placeholders. Review closing reports, overdue statuses
  and expired-but-open care. Confirm intentional deletion of C1063/A26019 and
  budget/date/role changes; retain the revision as the source, not automatic
  rollback. Do not remove historical employee rows merely because a mandate ended.
  Existing skip-and-warning behavior remains for unusable invoices. Acceptance:
  corrected XLSX and a reviewed finding list, followed by a clean disposable-DB
  import; no fixes exclusively in SQLite.

- [ ] [P1] [Workbook/Import] **DM-82** Make checks actionable and preserve customer
  comments. `[Sonnet]`. Add stable catalogue IDs and fixed comment/disposition
  fields; include the report-key, missing-reference, overdue and completion-date
  checks, plus mandates with no employee rows. Link each open check to its record
  findings. Correct the planned-exit condition and scope Accordix-only requirements
  to configured reportable payers. An unknown planned flag is a separate warning,
  not silently treated as Ja. Implement equivalent Python warnings under DM-61,
  including missing required payer/requester and an empty derived report FK.
  Acceptance: every G comment remains attached to its original check after
  resolving another finding, and Excel/Python agree on synthetic planned and
  unplanned exits, duplicate IDs, empty references and absent assignments.

- [ ] [P1] [Contacts] **DM-83** Add optional contact details. `[Sonnet]` after field
  agreement. Add `phone` and `email` to Ansprechpersonen, and `billing_email` to
  Kostenträger, available to all payers including private customers. Store phone
  numbers as text to retain `+` and leading zeroes. Empty contact data must not
  block import or invoices. Warn on obvious malformed email data without rejecting
  the row. No automatic sending or new address printed on invoices. Update Config,
  import models, synthetic fixtures and the customer workbook together. Currently
  even a field marked optional must have an Excel column in the importer; support
  absent **new** optional columns as NULL so the existing format still imports.
  Acceptance: both old and extended workbook formats import; existing invoice
  recipients, amounts and QR data remain unchanged.

- [x] [P1] [Responsibility] **DM-84** Specify dated employee responsibility.
  Completed 2026-10-11 using Stephan's due-date decision and the shared tested
  resolver. Source-workbook rollout remains open. The original proposal below is
  superseded where it offers another reference date; see the update above.
  `[Opus]`, with customer confirmation by `[Stephan]`; implementation `[Sonnet]`.
  Add a separate `Zuständigkeitsverlauf` table with `assignment_id`, `mandate_id`,
  `employee_id`, `role` (P/S), `valid_from`, `valid_to` and `notes`. A separate PK
  allows the same employee to return to the same mandate without changing the
  existing `relation_mandate_emp` key. One row records one uninterrupted role
  period. Dates are inclusive; a switch on 15 October closes the former period
  on 14 October and starts the new period on 15 October. Blank end means ongoing.
  Show changes with mandate, employee IDs/names, role and dates; preserve closed
  periods in the source XLSX across monthly rebuilds.

  The history is authoritative for **dated report responsibility**; the existing
  Zuordnung MA remains the operational assignment for timesheets in this first
  step. Warn if its current P differs from the current historical P. This limited
  duplication requires a documented update procedure; it avoids silently changing
  timesheet generation while extending reporting. Replacing operational assignment
  with history is a separate follow-up requiring all consumers to use month-overlap
  selection, including two employees during a switch month.

  Proposed report lookup: optional `responsibility_date`, otherwise `due_date`.
  It returns exactly one P whose interval contains that day. Gaps, overlapping P
  periods or missing dates produce an explicit unassigned finding. If a mandate
  has no history yet, retain today's P for operational compatibility but label it
  as **current assignment; historical responsibility unknown** in historical views.
  Never fall back to current P for a gap in an existing history. `completed_date`
  is the completion date and must not silently change responsibility. If actual
  authorship is needed, model `author_employee_id` separately; responsibility
  alone does not prove who wrote the report. Use the same resolver in Berichte,
  DM-70 Terminlisten and DM-86; show unassigned entries in a finding output.

  Acceptance: switch-day boundaries, return of a previous employee, simultaneous S
  support, P overlap/gap, future assignment, predecessor/successor mandates and
  old-workbook fallback verified with synthetic records. Customer must provide
  known historical periods; do not backdate today's assignment to mandate start.
  Risk: extra data maintenance and apparently precise but unsupported history.
  This explicitly extends the 2026-10-10 limit on historical reconstruction only
  by recording supplied periods; there is no event log or reconstruction from
  old invoices. The report-date definition remains a customer decision.

- [ ] [P1] [Domain] **DM-85** Specify parents, guardians and child residences.
  `[Opus]`, answers `[Stephan]`; implementation `[Sonnet]`. For v1, propose a
  `Bezugspersonen` table with `contact_id`, `person_id` (child), relationship,
  explicit guardianship status (Ja/Nein/Unbekannt), name, street, postal code,
  locality, phone, optional email and notes. Allow several contacts per child;
  a parent is not automatically a legal guardian and a guardian need not be a
  parent. One row per child/contact is simpler than a general person/relationship
  subsystem; shared sibling contacts may be duplicated and need consistent updates.

  Add optional current residence fields to Kinder and an optional `Platzierungen`
  table with `placement_id`, child, start/end, placement type/place, address,
  contact phone and notes, so both current and past placements can be shown.
  Warn on reversed periods and unexplained overlaps; keep an unknown start unknown.
  Keep the child's residence, guardian residence and placement separate. Existing
  `residence_legal_guardian` is already imported and exported to Accordix as a
  locality field; preserve it. With several guardians, do not automatically select
  one address or infer `canton_of_residence` from a placement. Decide explicitly
  which address is maintained for Accordix, and warn on conflicting entries.
  No parent/placement details flow into invoices or employee report exports by
  default. Acceptance: separated parents, non-parent guardian, sibling contacts,
  changed placement and missing optional data work without changing index-child
  selection, billing or existing Accordix address behavior. Risk: contact/address
  duplication and more sensitive information in workbook, backups and exports.

- [x] [P1] [Report] **DM-86** Generate a Klientenübersicht from the report table.
  Implemented 2026-10-11 with synthetic verification. Windows/customer acceptance
  remains open. The original proposal below is superseded for YEAR, Übersicht
  and repeated name columns by Stephan's decision recorded above.
  `[Opus]` specifies mapping, `[Sonnet]` implements. Reference:
  `resources/2026 Klientenübersicht.xlsx`, eight sheets (overview and seven
  employee sheets), with 2026/2027 Jan–Dec grids and legend: red Bericht,
  orange Zwischenbericht, blue Abschluss + Bericht. Employee layouts differ
  between 39 and 42 columns. Use the structure and legend as the reference;
  customer sheets with old personal data must not become the output template.

  Proposed separate CLI/Make command `make klientenuebersicht YEAR=2026`, using
  imported SQLite and configured output paths. Produce an overview plus sheets
  per employee, with the requested year and following year, one row per mandate
  with index child/family display and explicit A-ID. Keeping separate mandates
  avoids merging parallel services or follow-up orders under one family name.
  Show requester, contact/phone, authorisation dates, service type and employees;
  fill Jan–Dec cells from actual due dates and forms. Use DM-84 responsibility at
  each report's reference date so a switched mandate can appear on both employee
  sheets, each with only that employee's appointments. Supporting S roles may be
  displayed but do not duplicate P responsibility. Add a visible unassigned
  section and a detail list with every report ID, mandate, date, form, status,
  completion date and assignment basis. Include all statuses in the annual view;
  use text to distinguish completed/cancelled entries, keeping colours for forms.

  Several reports in one month must remain visible as multiple dated lines; a
  mixed-form cell needs text labels and a neutral fill, not one misleading colour.
  No-date and out-of-grid appointments belong in the detail list with a reason.
  Do not copy old day values: initial migration assumed the 15th for red month
  markers and sometimes used mandate end for blue closing reports. A reverse
  export can restore the **view**, not those lost original facts or obsolete
  per-employee copies. Current revision contains Zwischenbericht/Abschlussbericht
  entries only; do not reintroduce deleted Bericht entries from the reference.
  Do not equate legacy F/D/I/Gst/Std columns with current budgets before defining
  their meanings and units. Unknown columns remain unfilled and documented.
  No recurrence generation, source-workbook editing or report re-import.
  Acceptance: synthetic year boundary, employee switch, all statuses, multiple
  appointments/forms per month, missing assignment and no-date report; reconcile
  the detail list to every imported report, distinguishing deliberate employee-sheet
  duplication from duplicates. Verify Excel opening, filters and printed layout.

### Delivery order, risks and decisions needed

1. Implement DM-80 and DM-82 first, independently of the later customer corrections
   in DM-81. Windows acceptance DM-06 remains separate. Before the next import of
   the customer workbook, the agent performs the general review described above.
   Unresolved data may still make that import fail; Stephan accepts this. Structural
   repair is urgent; optional extensions must not delay the October billing path.
2. DM-83 is small and can ship independently. DM-85 needs field/maintenance agreement
   before implementation; contact details alone do not require a general CRM.
3. DM-84 before the historical employee version of DM-86. A first overview can
   precede history if it clearly labels current assignment and does not claim past
   responsibility. DM-70 then needs the shared date-aware resolver.
4. Back up and patch the customer workbook in place, retaining manual changes;
   import into an isolated disposable DB and compare invoice/Accordix output
   before handover. New optional tables must be optional when reading an older
   workbook. Do not destructively change the existing assignment schema.

Main risks are already visible: table operations break hidden formulas, blank
calculated FKs drop reports, duplicate IDs omit appointments, static notes drift
beside dynamic checks, and current employee assignment rewrites the apparent past.
Row-level findings and synthetic editing/interval tests address these directly.
History and placement dates supplied without evidence must remain incomplete.
The annual grid compresses information, so its detail list is required for review.
Parent and placement contacts expand the personal-data footprint; employee exports
must include only the agreed operational fields. The reference XLSX is currently
untracked and contains customer data; do not add it to Git. Commit plans and
synthetic fixtures only.

Before implementing DM-84–86, obtain the customer's decisions on: the date that
defines responsibility (due date versus report date), actual author versus responsible
employee, available historical switches, guardian/contact structure and placement
history scope, and any legacy overview columns required beyond the report grid.
These questions do not block formula repair or the agreed optional contact columns.
No independent Opus/Astra review is claimed for this draft.

The existing `[Opus]` tags on DM-84–86 follow this backlog's model-assignment rule
for specifications with domain risk. They are not a prerequisite for DM-80/82/83.
Use that review for date-based responsibility, changes to operational assignment,
address semantics or lossy report mappings; routine formula repair and optional
phone/email fields do not need it. Actual missing dates, numbers and contact data
remain customer maintenance, not specification decisions. Automatic generation
from `report_interval_months` is not implemented and is not part of DM-86; current
import/reporting consume only explicit report rows.

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

- [x] [P0] [Daten] **DM-60** Befundliste mit dem Workbook an Wegpiraten übergeben. `[Stephan]`, Liste `[Sonnet]` (DM-05, Schritt 8). Hinweis: [dm02_fachfragen.md](dm02_fachfragen.md), Gruppe B, im Stand nach dem finalen Build. Die Bereinigung ist Sache von Wegpiraten und keine Voraussetzung für einen weiteren Schritt.

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
