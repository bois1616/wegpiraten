# Data model: person, mandate, care

Specification of the entity model that replaces the single `clients` table, as realised in `sandbox/wegpiraten_datenbank_sandbox.xlsx`. Written to be lifted into
`wegpiraten_v2` without the Excel specifics.

Rationale, worked examples and the customer-facing explanation live in
[konzept_person_auftrag_leistung.md](konzept_person_auftrag_leistung.md). This
document carries the part a second implementation needs: fields, keys,
invariants and the migration rules that produced the current data.

Aligned with the workbook 2026-09-21; where the two differed, the workbook is authoritative.
The *Indexkind* is the domain term for the child through which a mandate is
billed; earlier revisions and the concept document call it *Abrechnungskind*.

Extended 2026-09-22 with clarifications from Wegpiraten: quota per mandate can
change on a follow-up mandate; a newborn sibling always closes the running
mandate and opens a new one (settled, open question 3); the allocation basis
cannot differ within a mandate for the same reason (settled, open question 2);
`relation_mandate_emp.role` (P/S) marks the primary care person; reporting scope
is the family; the invoice number is decided (mandate number); the
predecessor-mandate dropdown is labelled; invariant 36 checks the service type
against the real Accordix mapping. Mandate numbering (open question 9) is
settled 2026-09-22 as a structure: `A` + year + yearly counter; applying it to
existing data is deferred to the eventual migration. Same day, later: the
`report` entity is built as a PoC — see [report](#report) — expected to change
once Wegpiraten has looked at it.

Revised 2026-09-25: the `family` entity is dropped. The family is a free-text field
`person.family_id`; the index child is derived as the youngest child of the family from
the date of birth, a child of a family without one is an error (see [Family](#family-no-table)).
The history below describes the earlier table.

Revised 2026-09-04 after two rounds of review: the ID prefixes, the short code
moving to the child, contact persons becoming their own entity, the separation of
*Betreuungskind* from *Indexkind*, and `family` as the entity that carries
the index child. The last two reverse changes made earlier the same day; the
reasoning is under [mandate_person](#mandate_person).

This model is a workaround for a workbook, not a general case-management schema.
It is cut to what the Accordix report and the invoice need. Where it stops short
on purpose, it says so.

## Glossary

The domain language is German and stays German. Technical identifiers are
English. The mapping is fixed:

| Domain term | Entity | Excel table | Excel sheet |
| --- | --- | --- | --- |
| Familie | family | `person.family_id` (free text) | Kinder |
| Kind | person | `person` | Kinder |
| Auftrag | mandate | `mandate` | Aufträge |
| Betreuung | care | `mandate_person` | Betreuungen |
| Ansprechperson | contact person | `masterdata_contact_person` | Ansprechpersonen |
| Zuordnung Mitarbeitende | mandate–employee link | `relation_mandate_emp` | Zuordnung MA |
| Betreuungskind | cared-for child | `mandate_person` row | Betreuungen |
| Indexkind | index child | derived: youngest child of the family, else the child itself | — |
| Kurzzeichen | short code | `person.short_code` | — |
| Bewilligung von / bis | authorisation period | `mandate.start_date` / `end_date` | — |
| Eintritt / Austritt | care period | `mandate_person.start_date` / `end_date` — Eintritt is entered by hand | — |
| Kontingent | quota | `mandate.allowed_*` — per mandate, may differ on a follow-up mandate | — |
| Vorgängerauftrag | predecessor mandate | `mandate.predecessor_mandate_id` | — |
| Bericht | report | `report` | Berichte |
| primäre Betreuungsperson | primary care person | `relation_mandate_emp.role` = `P` | — |

`mandate_person` keeps the name the concept document uses. `care` is the
shorthand in prose; do not introduce it as an identifier.

## Identifiers

`C…` is a child, `A…` a mandate, `AP…` a contact person.

**Superseded 2026-09-22** for the mandate's digits — see *Open questions*, point
9: `mandate_id` is now `A` + two-digit start year + three-digit yearly counter
(`A26001`), not the digits below. Kept here as the record of how today's sandbox
IDs (`A1000`–`A1083`) came to be; the eventual migration replaces them.

The digits carried over from the old `client_id`: `C1002` became `A1002`. The
letter `C` was freed and now means the child. Person numbers are a subset of
mandate numbers — a merged child keeps the lowest of its former numbers, so
`A1070` exists while `C1070` does not.

This is not free. Three places outside the workbook carry the old numbers:

- `service_data.client_id` in the database. A prefix swap fixes it:
  `UPDATE service_data SET client_id = 'A' || substr(client_id, 2)`.
- Archived timesheets carry the number in cell **G8**
  ([header_cells.py:20](../src/pydantic_models/data/header_cells.py#L20)); the
  short code sits in C8 and is informational. Sheets already imported are fine.
  Re-importing an archived sheet after the rename needs the importer to accept
  `C…` and map it, or the sheet to be edited.
- Invoice numbers are `f"{invoice_month}-{client_id}"`
  ([invoice_factory.py:78](../src/invoices/modules/invoice_factory.py#L78)),
  fed from `service_data.client_id` and therefore from cell G8 — the mandate.
  See below.

The earlier version of this document kept `mandate_id` on the old `client_id`
precisely to avoid this, and named cell F8 while doing so — the cell is G8. The
rename is worth the migration because the alternative is a `C` prefix meaning
mandate in one table and child in another.

### What the invoice number names

Today's `01.2025-C1002` looks like it names the index child, and in the old
model there was no way to tell: one `clients` row was the child *and* the
mandate, so both readings produce the same string. The code takes it from
`service_data.client_id`, which the importer read out of cell G8 — that is the
mandate.

The distinction becomes load-bearing the moment a child is the index child of
two mandates at once, and four already are:

| Index child | Mandates | Service types | Payers | Overlap | Staffed |
| --- | --- | --- | --- | --- | --- |
| C1019 Zwinggi Challco | A1019, A1070 | ST01, ST04 | P1000 both | 12.01.–31.05.2026 | both |
| C1035 Perren | A1035, A1059 | ST04, ST01 | P1000 both | 16.06.2025–31.10.2026 | both |
| C1050 Burri | A1050, A1077 | ST01, ST07 | P1000 / P1005 | 01.06.–31.08.2026 | both |
| C1053 Levic | A1053, A1054 | ST01, ST04 | P1000 both | 01.02.–31.05.2026 | neither |

Keying the number on the child alone gives Perren the same invoice number twice
a month for seventeen months. Three options were considered:

1. **Number from the mandate** — `01.2027-A1002`. Unique by construction. The
   letter changes once on running mandates, which recipients see.
2. **Number from the index child** — `01.2027-C1002`. Nothing changes for the
   78 children with a single mandate, and it breaks for the four above.
3. **Number from the index child plus service type** — `01.2027-C1050-ST07`.
   Keeps the C number, and invariant 20 is exactly what makes it unique: two
   mandates of the same service type for the same child must not overlap. Costs
   one lookup in `create_invoice_id`, and the extra hyphen is safe — `file_stem`
   in [invoice_processor.py:527](../src/invoices/modules/invoice_processor.py#L527)
   separates fields with underscores, not hyphens.

**Decided 2026-09-21: option 1, the invoice number is built from the mandate number**
(`01.2027-A1002`). The mandate number is the only one that stays put when the
index child changes mid-mandate (a newborn takes over); options 2 and 3 would
change the number of a running mandate. The letter change from `C` to `A` on
running mandates is visible to recipients. Not yet implemented: `create_invoice_id`
already takes the number from `service_data.client_id`, which after the prefix swap
described above carries the mandate number, so the code change is the migration
itself.

The grouping key in
[invoice_processor.py:302](../src/invoices/modules/invoice_processor.py#L302)
stays the mandate. Grouping by the child would merge two mandates with the same
payer onto one invoice — C1019, C1035 and C1053 all have that constellation —
and mix two service types at two hourly rates into one position list.

### Mandate numbers never change

Decided 2026-09-25: once a mandate number is issued it does not change, even when a mandate
with an earlier start date is entered later. The counter of a year only ever moves forward;
a new mandate gets the next free counter of its start year, ties on the same date are broken
by the former client number. In the sandbox the assignment lives in
`sandbox/mandate_numbers.json` (former client number → mandate number), written on the first
run of `prepare.py` from the numbers the 2026-09-24/25 test build had already shown. The
numbers of that build are the frozen ones; a build that recomputes the sort order would
shuffle them and is wrong. Numbers of mandates that vanish from the data are not reused.

## Entities

### person

One row per child, ever. Holds what is true of the child regardless of which
mandate is running.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `person_id` | text | no | PK; `C` + digits |
| `short_code` | text | yes | Kurzzeichen; appears in timesheet cell C8 and in the file name |
| `family_id` | text | **yes** | free text, identical for all siblings; set only where siblings exist |
| `social_security_number` | text | yes | AHV; format `756.NNNN.NNNN.NN`, 16 chars |
| `last_name`, `first_name` | text | no | |
| `date_of_birth` | date | yes | required by Accordix |
| `gender` | code | yes | required by Accordix |
| `uma_umf` | code | yes | required by Accordix |
| `spoken_language` | code | yes | |
| `canton_of_residence` | code | yes | required by Accordix |
| `residence_legal_guardian` | text | yes | |
| `notes` | text | yes | internal |

`short_code` moved here from `mandate`. It is built from the name — two letters
of the first name, two of the last, `Maurin Stoller` → `MaSt` — so it describes
the child, not the authorisation. A child with two mandates therefore carries
one code on both. Timesheet file names stay distinct because the mandate number
is in them as well:
`{employee_id}_{mandate_id} ({short_code})_{YYYY-MM}.xlsx`
([time_sheet_factory.py:242](../src/time_sheets/modules/time_sheet_factory.py#L242)).

Collisions between *different* children are real and are resolved by appending a
digit. The existing data already does this: `MaSt` Stoller, `MaSt2` Stähli. The
migration continued the series with `MaSt3` for Stauffer.

### mandate

One row per authorisation. Holds what the authority granted.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `mandate_id` | text | no | PK; `A` + the digits of the former `client_id` |
| `service_type_id` | text | no | → `service_types` |
| `service_requester_id` | text | no | → `masterdata_service_requester` |
| `contact_person_id` | text | yes | → `masterdata_contact_person` |
| `payer_id` | text | no | → `masterdata_payer` |
| `tenant_id` | text | no | → `masterdata_tenant` |
| `application_number` | text | **no** | Geschäftsnummer; for payer `P1000` (KJA) binding `yymmddnnn`, otherwise free text — see [Application numbers](#application-numbers-geschäftsnummer) |
| `start_date`, `end_date` | date | `end_date` yes | **authorisation**, not entry/exit |
| `allowed_travel_time` | number | yes | hours per month; granted per mandate, not per child, and may change with a follow-up mandate |
| `allowed_direct_effort` | number | yes | hours per month |
| `allowed_indirect_effort` | number | yes | hours per month |
| `allocation` | code | yes | assumption: per mandate, see open questions |
| `predecessor_mandate_id` | text | yes | → `mandate`; singly linked |
| `report_cadence` | code | yes | `einmalig` / `periodisch` / `ereignisbezogen`; moved here from `report` 2026-09-25 |
| `report_interval_months` | number | yes | only with `periodisch` |
| `notes` | text | yes | internal |

Derived, not stored: `family_id` (the family of the children cared for in this
mandate), `index_person_id` and `index_person_name` (that family's, or the single child
served), `short_code` (the index child's) and `sr_ap_gender` / `sr_ap_first_name` /
`sr_ap_last_name` (the contact person's). The workbook computes these plus display
and check columns (`successor_mandate_id`, `care_person_id`,
`person_count_current` / `person_count_total`, `quota_total`, `service_type_name`,
the `*_check` columns). A v2 schema can compute the first group in a view; the
check columns belong to the validator. Keeping the three
`sr_ap_*` names on the mandate means
[invoice_processor.py:156](../src/invoices/modules/invoice_processor.py#L156)
keeps working unchanged.

`successor_mandate_id` is a lookup, never a column: *the mandate whose
predecessor is this one*. Invariant 11 makes it unique. A stored successor field
would be a second copy of the same edge and could contradict the first.

### mandate_person

One row per child per mandate. **Each row is exactly one line of the Accordix
report** — that equivalence is the point of the entity and the fastest way to
explain it.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `mandate_id` | text | no | PK part → `mandate` |
| `person_id` | text | no | PK part → `person` |
| `start_date` | date | no | Eintritt of this child |
| `end_date` | date | yes | Austritt of this child; empty while the care runs |
| `is_leaving_reason_planned` | Ja/Nein | yes | |
| `leaving_reason` | code | yes | |
| `custom_leaving_reason` | text | yes | required when `leaving_reason` = `Anderer` |
| `after_leave_situation` | code | yes | |
| `custom_after_leave_situation` | text | yes | required when `after_leave_situation` = `andere` |
| `is_consultative_adolescent_psychiatric_care` | Ja/Nein | yes | IBF only |
| `number_of_care_days_per_week` | integer 0–7 | yes | SPT only |
| `remarks` | text | yes | for the Accordix report |

**A row here means the child receives the service.** That is what makes the row
an Accordix line, and it is the reason the index marker cannot live here.

An intermediate version on 2026-09-04 stored `is_index_case` on this entity and
derived the mandate's child from it, on the argument that the children are
entered here anyway. The argument holds; the model does not. Children and
mandates are many-to-many in both directions at once, and the index child is a
third thing again:

- **One mandate, several children** — siblings in one authorisation.
- **One child, several mandates** — two services running in parallel.
- **Both mixed** — the older child has two mandates, the younger one. Or: the
  younger child's mandate has expired while the older child's runs on.

In the last case the index child has no care row in the running mandate at all,
because it is not receiving the service — and adding one to carry the flag would
report a child to Accordix who is not in care.

The rule Wegpiraten applies is *the youngest child of the family*, and it does not
move when a mandate expires. That makes the index child a property of the
family, which is why it is derived from the family's children and not stored here. A
mandate inherits it through the children it cares for.

`start_date` is the Accordix entry (*Eintritt*) and a **manual entry**: it is
neither the current authorisation nor the first mandate on record. It can predate
every recorded mandate, because mandates before the record began were never
entered, so it cannot be derived from them. The consistency rule runs the other
way: the first recorded mandate must not begin *before* the entry, compared by
month (invariant 32). In all 86 migrated rows it equals `mandate.start_date` —
that is an artefact of the old model having one date, not a rule. On a renewal
the entry date carries over from the predecessor's care row; invariant 21
watches for that.

### Family (no table)

Until 2026-09-25 a `family` table carried the family and named its index child. It is
gone, for one reason: the index child is derivable. The rule Wegpiraten applies is *the
youngest child of the family*, which the date of birth already says, and the table had
never been filled (0 rows in the real data). What it cost: a family had to be created
before a child could be assigned to it, the index child had to be picked from a dropdown,
and five checks watched the table against the children.

Now the family is one free-text field on `person`. Siblings carry the same text, for
example `Muster Interlaken`. Derived on the child, not stored:

- `family_size`: how many children carry this text.
- `index_person_id`: the child itself where there is no family, else the youngest child
  of the family. A mandate takes it from the first care row's child.

**It still cannot be derived which children belong together.** Nothing in the data
identifies a household: `residence_legal_guardian` is a municipality, not an address, and
surname plus municipality produces false positives (C1002 Luan and C1068 Yarrah Orion
Nipote, both Meiringen, nine years apart: two families, said Wegpiraten). Which children
belong together is knowledge that only a person has, and it is entered or it does not
exist. The field stays empty until siblings actually appear.

`person.family_id` is a single value with no history. A child moving between households
is a deliberate edit, and no requirement for household history has come up.

**What free text gives up.**
- A typo creates a second family. Invariant 46 (a family with one child) catches it, and
  a mandate with children from two families is flagged by invariant 26.
- No override: the index child is always the youngest. Wegpiraten named no exception; the
  earlier "patchwork" caveat was ours.
- Twins or an identical date of birth: the first child in the list wins; invariant 47 marks it.

The gate is unchanged: a mandate serving **more than one child** without a family is an
error (invariant 28), because then nothing determines which child is billed.

**Merging two families** is one edit: give the children the same text. Every mandate of
those children follows, including the short code on the timesheets.

### masterdata_contact_person

New. One row per contact person at one service requester.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `contact_person_id` | text | no | PK; `AP` + three digits |
| `service_requester_id` | text | no | → `masterdata_service_requester` |
| `gender` | Frau/Herr | yes | salutation, not the person's gender field from Accordix |
| `first_name`, `last_name` | text | yes | |
| `notes` | text | yes | internal |

A person working for two requesters gets two rows. That keeps "does this contact
belong to this requester" a single lookup (invariant 13) and matches how the
data behaves: Tanja Schneider appears under SR006 and SR016, Anja Nigg under
SR015 and SR025, and nothing in the data says whether that is one human or two.

### relation_mandate_emp

`mandate_id` + `employee_id`, both parts of the PK. Employees hang off the
mandate, not off the child — a consequence of the model, and what makes the
`is_index_case` flag from the concept's stage 1 unnecessary as a guard against
double invoicing.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `mandate_id` | text | no | PK part → `mandate` |
| `employee_id` | text | no | PK part → `employees` |
| `role` | code | yes | `P` primary / `S` support, added 2026-09-22 |

**`role`, Wegpiraten 2026-09-22.** There is always one primary care person
(*primäre Betreuungsperson*), the one named to the KESB. Recorded here rather
than as a new entity because it is a property of the mandate–employee link, not
a fact about either side alone. It changes nothing about timesheet generation or
invoicing — both stay keyed on the link as before — it only decides who a report
gets assigned to (see *Reporting* below). Invariants 34–35 keep it to exactly one
`P` per mandate; unset is a warning, not an error, because the field is new. A mandate with exactly one
employee gets `P` automatically in the migration build.

## Invariants

Numbered so a validator can cite them. Severity `error` blocks a correct
Accordix report or a correct invoice; `warning` is a data-quality signal that
can legitimately be true. Numbers 1–19 keep their meaning from the previous
version where the entity did not change.

| # | Invariant | Severity |
| --- | --- | --- |
| 1 | `person_id` unique | error |
| 2 | `mandate_id` unique | error |
| 3 | (`mandate_id`, `person_id`) unique in `mandate_person` | error |
| 4 | every `mandate_person.mandate_id` exists in `mandate` | error |
| 5 | every `mandate_person.person_id` exists in `person` | error |
| 6 | *(withdrawn 2026-09-25 — the family is free text, there is no table to point into)* | — |
| 7 | *(withdrawn — the index child need not have a care row, and since it is derived it cannot be typed wrong)* | — |
| 8 | every mandate has at least one `mandate_person` row | error |
| 9 | `predecessor_mandate_id` exists in `mandate` | error |
| 10 | `predecessor_mandate_id` ≠ own `mandate_id` | error |
| 11 | `predecessor_mandate_id` used by at most one mandate — the chain must not fork | error |
| 12 | `relation_mandate_emp.mandate_id` exists in `mandate`; `employee_id` exists in `employees` | error |
| 13 | `mandate.contact_person_id` exists and belongs to `mandate.service_requester_id` | error |
| 14 | an AHV number appears at most once across `person` | warning |
| 15 | every person has at least one `mandate_person` row | warning |
| 16 | `end_date` set implies `leaving_reason` set | warning |
| 17 | a person with a care row has `date_of_birth`, `gender`, `uma_umf`, `canton_of_residence` | warning |
| 18 | coded values match their value list **byte for byte** | warning |
| 19 | mandate expired while a care row is still open | warning |
| 20 | two mandates of the same `service_type_id` covering the same person do not overlap in their authorisation periods | warning |
| 21 | on a renewal, the child's `start_date` equals the predecessor's `start_date` for that child | warning |
| 22 | `short_code` set and unique across `person` | warning |
| 23 | every mandate has a `contact_person_id` | warning |
| 24 | *(withdrawn 2026-09-25 — the index child is derived)* | — |
| 25 | *(withdrawn 2026-09-25 — the index child is always the youngest)* | — |
| 26 | all children cared for in one mandate belong to one family | warning |
| 28 | a mandate serving more than one child has a family | error |
| 27 | *(withdrawn 2026-09-25 — there is no family table that can be left empty)* | — |
| 29 | `mandate.service_type_id` exists in `service_types` | error |
| 30 | a running mandate whose service type slice (`to_date`) has expired | warning |
| 31 | an employee link on an expired mandate; timesheets are generated from the link | warning |
| 32 | the month of the first recorded mandate start is not before the month of the care `start_date` | warning — month-rounded: entry 17.02.2026 accepts a mandate from 01.02.2026 and warns for 01.01.2026 |
| 33 | *(withdrawn 2026-09-25 — replaced by 45)* | — |
| 45 | every child that carries a family has a `date_of_birth`, otherwise the index child cannot be determined | error |
| 46 | a family has more than one child | warning — typo in the free text |
| 47 | the youngest date of birth of a family belongs to one child only | warning — twins or an entry error |
| 34 | at least one `relation_mandate_emp` row of a mandate has `role` = `P` | warning |
| 35 | at most one `relation_mandate_emp` row per mandate has `role` = `P` | warning |
| 36 | `mandate.service_type_id`'s `code` is either in the Accordix mapping or on the deliberate exclusion list | warning |
| 42 | `application_number` is set | error |
| 43 | payer `P1000`: `application_number` is nine digits `yymmddnnn` with `nnn` > 0 | error |
| 44 | payer `P1000`: digits 1–6 of `application_number` form a real calendar date (`260631002` is not) | error |

Invariants 42–44 were added 2026-09-25 and are numbered after 41 in the reporting
section's sequence; they are listed here because they belong to `mandate`.

Invariant 18 deserves the emphasis. `validate_coded_value` in
`shared_modules/accordix.py` compares exactly, so `Keine weitere Leistung` is
rejected where `keine weitere Leistung` passes. Excel's `COUNTIF` is
case-insensitive and silently accepts both, which is why the workbook uses
`SUMPRODUCT(--EXACT(list, cell))` instead. A validator in v2 must compare
case-sensitively or it will pass data that Accordix rejects. Sixteen legacy
values fail it today.

Invariant 36, asked by Wegpiraten 22.09.2026: does `Leistungstypen.description`
have to match the Accordix wording? **No — the two are unrelated today, and that
is worth knowing rather than fixing.** The real Accordix `ServiceTypeName` comes
from `SERVICE_TYPE_MAP` in `shared_modules/accordix.py`, keyed by `code`, not by
`service_type_id` and not by `description`. `description` is a free display text
for the workbook and is not read by the export at all. Checked against the
current sheet: for `ST01`/SPF the two happen to read the same; for `ST02`–`ST04`
(UWB) and `ST06` (DAF) they diverge substantially (`description` reads "DAF
Langzeitunterbringung", Accordix expects "DAF: Begleitung von
Pflegeverhältnissen Langzeitunterbringung"). That divergence is harmless *because*
`description` is cosmetic — but it means nobody can read the sheet and know
whether a service type will actually report. What matters is the `code`, and
invariant 36 mirrors `SERVICE_TYPE_MAP` plus the deliberate exclusion list
(`PRIVAT`, `SONST`, `Jugendcoaching`, `Abklärung`, `med./therap. Bericht`) into
the workbook to catch a `code` that is neither — a typo or a genuinely new
service type would otherwise fail silently, exactly the "Accordix meldet zu
wenig" failure already named in the concept document. It found one on the first
run: **`ST09` / `KOB` (Kindorientierte Beratung) is used on real mandates and has
no Accordix mapping at all.** `ST00` (`UNBEKANNT`, placeholder) and `ST02_alt`
(`BBT`) are also unmapped but unused. Whether KOB should report, and under which
Accordix `ServiceTypeName`, is with Wegpiraten.

Invariant 32 is computed per care row against the mandate of that row. Two
legitimate cases keep it a warning: a sibling joining a running mandate later, and
an authorisation issued before care began. The workbook compared day-exact until
2026-09-21; the month rounding was added then.

Invariants 29 to 33 exist in the workbook and were missing here. The workbook has
41 checks in total as of 2026-09-25 (three of them the application-number checks 42–44); some
numbers above are split or merged there (4/5 and 12 each appear as two checks). The sheet
`Prüfungen` lists only the checks that are open; the sheet `Prüfkatalog` lists all of them,
including the passed ones, as evidence that they run.

Invariant 20 fires on nothing in the current data — all 86 mandates are checked
and none overlap. It is a guard for what happens next: a renewal entered as a
second parallel mandate instead of a successor is the mistake the model now
makes visible. When two of the same service genuinely run at once, the warning
is correct and stays.

Asked 22.09.2026: when an overlapping follow-up mandate is entered, could the
predecessor's `end_date` be closed automatically? **No — by design, not by
limitation.** `mandate.end_date` is the authority's approved Bewilligung, an
external fact; writing it from our own logic would either silently paper over a
data-entry mistake (the predecessor really is still open and the overlap is
real) or discard the authority's actual approved date. Invariant 20 already
catches the case without guessing — it fires on person, service type and date
overlap regardless of whether `predecessor_mandate_id` is set — and leaves the
correction, closing the predecessor by hand, to whoever entered the renewal.

Invariant 21 also fires on nothing today, for a duller reason: no chain exists
yet.

Invariant 26 catches the mandate that covers children from two families, which means
either the families are wrong or it should be two mandates. Invariants 45 to 47 guard
the free-text family: without a date of birth the index child cannot be derived, a lone
family is probably a typo, and identical dates make the choice arbitrary.

The class of error that disappeared entirely: two mandates of one family naming
different index children. Both read the same derivation.

Not an invariant, and not machine-checkable: a sibling who is cared for but was
never entered is invisible. Nothing detects it. Asking whether further children
in the household are being cared for belongs in the mandate intake procedure.

## Coded value lists

`gender`, `uma_umf`, `spoken_language`, `canton_of_residence`, `allocation`,
`leaving_reason`, `after_leave_situation` — canonical values in
`FIELD_VALUE_LISTS` (`src/shared_modules/accordix.py`). `Ja`/`Nein` for the
boolean-ish fields, `Frau`/`Herr` for the salutation. The workbook mirrors these
lists on the sheet `Wertelisten`; they are the same strings, and a change
belongs in both places.

## Migration from `clients`

Executed against the 86 rows of `masterdata_client` as of 2026-09-02, prefixes,
contact persons and families added 2026-09-04. Result: 82 persons, 86 mandates, 86 cares, 45 contact persons, 91 employee links; the family table starts empty.

**Person identity.** Group rows by AHV number, but only where the number starts
with `756.` *and* first and last name agree. The `Privat` placeholder in the AHV
column is not an identity — three rows carry it and stay separate. Four groups
merged: A1019+A1070, A1035+A1059, A1050+A1077, A1053+A1054. `person_id` is `C`
plus the digits of the lowest number in the group.

The name condition is not decoration. A1079 and A1083 share `756.2404.7951.71`
but are Caroline and Marlon Til Stauffer — merging on AHV alone would have made
them one child. They stay separate and invariant 14 keeps reporting them until
the number is corrected.

**Families.** None are entered. A child without a family is its own index child, which is
what the records support and what makes the model behave exactly as the old one did. Real
families are entered when Wegpiraten supplies the knowledge.

**Short codes.** Taken from the mandates of the child, which agreed in all four
merged groups. One collision between different children needed a new value:
Stauffer got `MaSt3` because Stoller holds `MaSt` and Stähli `MaSt2`.

**Contact persons.** Built from the distinct (`service_requester_id`,
`first_name`, `last_name`) triples in the 86 mandate rows. 45 rows, and three of
them carry a contradiction that the repetition had been hiding:

- AP015 David Dimitrijevic at SR011 is addressed as `Frau` on seven mandates and
  `Herr` on three. The majority value was taken and the split recorded in
  `notes`.
- AP022 and AP025 at SR013 are `Wilhelmi, Regula` and `Regula, Wilhelmi`.
  Probably one person with the names swapped on one of them. Both rows survive
  with a note; merging them is a decision about the data, not about the schema.

**Splitting `end_date`.** The old column meant the authorisation end, and the
Accordix report of 2026-08-29 needed a hand-made rule to avoid reporting it as
an exit. The migration applies that rule once: `end_date` becomes
`mandate.end_date` always, and additionally `mandate_person.end_date` only when
at least one of `is_leaving_reason_planned`, `leaving_reason`,
`custom_leaving_reason`, `after_leave_situation`,
`custom_after_leave_situation` is filled. That held for 18 of 86 rows.

**Date normalisation.** `date_of_birth` is parsed from datetime, date and Excel
serial number before persons are compared, otherwise Awa Burri's two spellings
(`29.10.2018` and `43402`) would have counted as conflicting person data. After
normalisation no group had a conflicting value in any person field.

**Not reconstructable.** `predecessor_mandate_id` is empty everywhere. Renewals
overwrote `start_date` in the old model, so the chain is gone for existing data
and can only be built going forward.

**A live instance of exactly this loss, found 2026-09-22.** A printed client
overview Wegpiraten still keeps by hand showed C1006 Shanice Richards running to
31.08.2026 with quota 3/18/9. The sandbox has only `A1006`, running to
28.02.2027 with quota 2/12/6, `predecessor_mandate_id` empty. Wegpiraten
confirmed by hand: the first mandate ended, a renewal followed with a reduced
budget — not two readings of the same fact, an actual predecessor that the
migration could not see because the old model had already overwritten it. Their
own words fit the point this document keeps making: *"Genau das könnten wir
beantworten, wenn wir bereits in der neuen Struktur arbeiten würden"* — once
renewals are entered as successor mandates instead of overwritten rows, this
question answers itself from `predecessor_mandate_id` instead of needing a
side-channel document.

## Application numbers (Geschäftsnummer)

Decided 2026-09-25 (Stephan), replacing the earlier reading of this field as a free
channel marker (2026-09-04, kept below as history).

**Payer `P1000` (Kantonales Jugendamt Bern, KJA, sometimes KJA-FS): the notation is
binding.** `yymmddnnn` — two-digit year, month, day of the **order date** (*Auftragsdatum*),
then a three-digit running number of that day: `260819008` is order no. 8 of 19.08.2026.
The order date is **not** the start of the authorisation. The start (`start_date`) is entered
by hand from the order itself and has no further meaning for the number; the date inside the
number is only used to check length and plausibility (`260631002` names a date that does not
exist). Deviations are marked as errors (invariants 43, 44).

**A missing entry is an error for every payer** (invariant 42).

**Payer other than `P1000`: free text without semantics, until further notice.** That can
change. KESB mostly — not without exceptions — use `yyyy-nnnn`, for example `2024-1987`.
It has no effect today but could matter for case-level reporting later. Open question 10.

**`Auftrag beendet` (formerly `beendet`) is not a good entry, and the 2026-09-24 renaming is
withdrawn.** The old text overwrote the authority's own number, and in a chain of mandates
it is easier to follow when the older, external numbers are still visible. That the
authorisation has ended is read off the field *Bewilligung bis* (filter on it), not from a
marker in this field. Historically the data still carries `beendet` on 14 mandates of payer
`P1000`; correcting them means recovering the original number by hand and is not done by the
build. They now show up as errors on purpose (Stephan's stance: findings in old data are the
purpose of the exercise). Likewise `brief`, `Sonderfall`, `on hold` — where a P1000 mandate
carries such a text it is a deviation from the binding notation.

### History: invoice delivery channels (2026-09-04)

Recorded because it explains why the field used to hold texts, and because nothing else in
this repository writes the channels down. From Wegpiraten.

How an invoice reaches the authority depends on the Leistungsbesteller, and the
three paths do not share a format:

| Path | Upload | Number range | File name |
| --- | --- | --- | --- |
| KJA-FS | bulk, up to 50 PDFs | KJA-FS Antrags-Nr. | fixed scheme, fields separated by `_` |
| KESB, billed directly | none | different, unrelated | free |
| Exceptions | none | — | letter or e-mail with the PDF attached |

Only the first has a number in the KJA notation, which is why operators put the channel into
the field for the other two. The author's reason for not encoding channels: *«Das kann man
nicht kodieren ohne Millionen von exotischsten Sonderfälle zu beachten.»* That still holds for
the channel; what changed is that the field is no longer the place for it. A missing number on
a KJA-FS mandate used to look exactly like a channel marker and was caught downstream — KJA-FS
rejects the upload; invariants 42–44 now catch it earlier.

## Excel-specific decisions

Relevant only while the master data lives in a workbook; v2 can ignore this
section.

**Column order carries a rule.** Every editable column comes first, without
gaps; every computed column follows, marked `▸`, filled grey and locked. The
boundary is where the white cells stop. Two things depend on it: sheet
protection is legible without reading a legend, and the entry masks can hand
over one contiguous row to paste.

**Sheet protection was removed 2026-09-24.** It had been on for all generated sheets
(no password, editable columns unlocked). Sorting a sheet that contains locked formula
cells fails in Excel and LibreOffice alike (*Protected cells cannot be changed*), and
sorting is needed more than the guard against overwriting a formula. The grey `▸`
columns remain as a visual marker; `PROTECT_SHEETS` in `build.py` switches the old
behaviour back on.

**Dropdown sources** are defined names over `OFFSET(…, COUNTA(…))` rather than
structured table references, because LibreOffice and Excel disagree about
structured references inside data validation. The ranges grow as rows are added,
so a newly entered child is immediately selectable.

**A `definedName` carries no leading `=`.** In OOXML its content is a formula, not
a cell entry. Excel drops a name that starts with `=` while opening the file and
reports it as *removed records*; LibreOffice accepts both spellings. Every build
from 2026-09-02 to 2026-09-04 wrote the `=`, so in Excel all 18 names were gone and
every dropdown was dead — invisible here, because the whole verification loop ran
through LibreOffice. The source workbook had it right; the bug was introduced by
the rebuild.

The same session removed the external link inherited from the source: it pointed at
`wegpiraten_datenbank (# Name clash 2026-08-29 …).xlsx` in a Proton Drive folder on
another machine, a stale sync artefact. `load_workbook(..., keep_links=False)`.

`verify_excel_strict` in `build.py` now fails the build on both, plus empty or
duplicate table headers and `=`-prefixed validation and formatting formulas. It
exists because a LibreOffice-only test loop cannot see any of them.

**INDEX/MATCH, not XLOOKUP.** The previous version of this document blamed
spilling array functions. That is wrong for XLOOKUP with a single return column,
and it was worth testing rather than repeating: openpyxl writes the string it is
given, and LibreOffice 25.2 computes `_xlfn.XLOOKUP(...)` correctly while a bare
`XLOOKUP(...)` yields `#NAME?`. The real objection is the version floor. The
workbook's cached values *are* the import interface —
[import_masterdata.py:90](../src/data_imports/import_masterdata.py#L90) reads
with `data_only=True` — so a machine with LibreOffice below 24.8 or Excel 2019
would not fail loudly. It would save `#NAME?` into the cache and the import
would read empty lookups. INDEX/MATCH computes everywhere and costs one extra
`MATCH` per formula.

**Helper columns.** `is_index_case` on Betreuungen (Ja when the row's child is the
mandate's index child) is a visible derived column. Family, the index child of the child, date of birth and the
predecessor mandate are carried into Betreuungen as hidden helpers, so that
invariant 21 needs no nested lookup inside `SUMIFS`. The `issue_*` columns feed
the sheet `Fehlerliste`, which collects the findings of every sheet in one place.

**No `TEXT()`, same reasoning as INDEX/MATCH above.** `mandate_display` (below)
needed a date rendered into a string. `TEXT(date,"DD.MM.YYYY")` looked right and
built without error, but LibreOffice's recalculation returned literal
`DD.09.YYYY` — the day and year tokens were not substituted, only the month.
Found by testing the round trip, not by inspection. Rebuilt without `TEXT()`:
`RIGHT("0"&DAY(d),2)&"."&RIGHT("0"&MONTH(d),2)&"."&YEAR(d)`. Whether real Excel
would have rendered the original correctly was not tested — only LibreOffice is
available here, which is exactly the blind spot `verify_excel_strict` exists for
on the structural bugs; this one a formula, so it had to be caught by running the
formula, not by parsing the file.

**Predecessor mandate, labelled.** Wegpiraten, 22.09.2026: a bare mandate number
in the predecessor dropdown is unreadable and error-prone. `predecessor_mandate_id`
on Aufträge is now an auto/hidden column, extracted from a new editable
`predecessor_choice` (a choice plus an extraction formula, the idiom also used by `report.mandate_choice`).
The dropdown source is `mandate_display` (`A1002 — Nipote, Yarrah Orion (SPF, bis
31.03.2027)`) through the named range `liste_auftrag_namen`. **Not done:** filtering the list to the same child/family and
service type. It would need either a per-(family, service type) named range
rebuilt on every `build.py` run — workable, since the workbook is already rebuilt
for structural changes, but every such range would have to be regenerated from
`data["mandates"]`, and a brand-new family created directly in the sheet (not
through a rebuild) would not yet have a range to filter into, so the newest
follow-up mandate is exactly the case the filter would miss until the next
rebuild — or a `FILTER()`/dynamic-array formula, ruled out by the same version
floor as XLOOKUP above. The unfiltered, labelled list was shipped now because it
is a real improvement with none of that risk; filtering is a separate decision.

**Rebuilds no longer lose `role` or `Berichte`.** Both are entirely hand-entered
— migration_v2.json has no source for either, the same situation `family` was
in. `carry_over_handwork` (renamed from its original, family-only scope,
2026-09-22) now also reads the existing file's `Zuordnung MA.role` and the whole
`Berichte` sheet before the rebuild overwrites them, the same way it already
protected `Familien`. Skipping this step on the day `role`/`Berichte` were added
cost nothing, because both were still empty; it will cost real entries the next
time someone changes `build.py` after Wegpiraten has used either.

**`Berichte.assigned_employee_id` needed a hidden helper on `Zuordnung MA`.**
Picking the row whose `mandate_id` matches *and* whose `role` is `P` is a
two-criteria lookup, and `INDEX`/`MATCH` against two criteria at once needs an
array formula (Ctrl+Shift+Enter) to work without a helper — exactly the kind of
formula this workbook has avoided elsewhere for compatibility. Solved the same
way `is_index_case` avoids it: `relation_mandate_emp.primary_mandate_id`, a
hidden column that is the mandate's own id where `role` = `P` and blank
otherwise, turns it back into a plain single-criterion `MATCH`.

**No entry masks.** Two were built on 2026-09-04 and removed the same day. They
could not write into the tables — that needs a macro, and a macro in an `.xlsx`
means VBA, which LibreOffice runs only partially — so they ended in a copy-and-
paste step that cost more than the guidance bought. LibreOffice's own Data → Form
writes straight into the table, carries the same dropdowns, and needs no build
step.

**Entry cost is the reason for both simplifications.** Measured against the
column model: a new mandate for a known child is 29 entered cells across 3 sheets,
where the old single table was 38 cells across 2. Normalisation barely changed the
typing — it multiplied the *navigation*, and it introduced a dependency order
(child → contact → mandate → care → staff) that has to be known. That is where an
acceptable entry process is won or lost, not in the number of checks: the 38 checks sit on their own sheet and cost the person entering data nothing. Only gates —
mandatory fields, restricted dropdowns, an extra sheet on the critical path — do.
So the family stopped being a gate and the masks went.

**The former `Klienten` sheet** is kept, hidden and renamed `Klienten (alt)`.
Its formulas referenced the deleted `masterdata_client` table and were frozen to
their last computed values.

**Recalculation** of the whole workbook takes about 6 seconds in headless
LibreOffice, with `MAX = 2000` rows of formula reserve (7.2 s measured, minus a
1.0 s start measured on a trivial file). The quadratic formulas — invariant 20
over every pair of care rows and the youngest-child lookup per family — account for
most of the growth from 4.7 s. Cheap enough at this size; worth
remembering if `MAX` ever grows.

## Open questions

Carried forward from section 7 of the concept; the workbook implements the first
reading of each and marks it on the `Anleitung` sheet.

1. ~~Quota per mandate or per child?~~ **Settled 2026-09-21: per mandate.** It can
   change from one mandate to the next, for instance on a follow-up mandate.
2. ~~Can `allocation` differ between siblings in one mandate?~~ **Settled
   2026-09-22, with Wegpiraten: no.** A mandate always covers the whole family,
   whether or not each child has an explicit care row — that is also why billing
   runs through the index child even when the index child itself is not in care
   (see [mandate_person](#mandate_person)). When the basis of assignment changes —
   the example given: siblings start *Einvernehmlich über Sozialdienst*, the KESB
   later orders a measure for one of them because the parents refuse — that is not
   an edit of the running mandate but a **new mandate**, which then applies to
   every child in the family. `allocation` stays on `mandate` and invariant 26
   already forbids a mandate that mixes families; a mismatch cannot arise.
3. ~~Does a newborn sibling create a new mandate, or does the existing one change
   its index child?~~ **Settled 2026-09-22, with Wegpiraten: always a new
   mandate.** A birth into the family ends the running KGS/mandate and opens a new
   one, whether or not the new child ends up in care — the same "mandate is about
   the family" rule as point 2. The Nipote pair in point 5 below is the
   illustration: Yarrah's birth on 08.05.2026 should have closed A1002 (running
   since 2023) and opened A1068 as its successor, not left both running in
   parallel. The migration could not reconstruct `predecessor_mandate_id` for
   existing data (see *Migration from `clients`* below), so this chain has to be
   set by hand once the family is confirmed.
4. ~~Accordix entry date~~ **Settled 2026-09-21: manual entry**, separate from the
   first mandate date, because not all past mandates are on record. The
   consistency rule is invariant 32.
5. Which of the current mandates cover more than one child? Not derivable from
   the data, but two candidate sibling groups fall out of matching last name and
   guardian residence:

   | Children | Mandates | Note |
   | --- | --- | --- |
   | C1002 Luan (10.03.2017), C1068 Yarrah Orion (08.05.2026) Nipote, Meiringen | A1002 ST01 to 31.03.2027, A1068 ST01 to 31.08.2026 | same service, same requester SR006. If one family, the index child should be Yarrah on both — and A1068 expired on 31.08.2026, which is exactly the mixed case above |
   | C1015 Flurin (19.12.2023), C1078 Laura (no date of birth) Loosli, Unterseen | A1015 ST01 to 31.08.2027, A1078 ST08 to 10.07.2026 | same requester SR011, different services. Not previously spotted |

   C1079 Caroline and C1083 Marlon Til Stauffer share a last name and the
   disputed AHV number; C1079's mandate is ST99 `PRIVAT` via SR999, so it is a
   privately paid service rather than an authority mandate.

6. **Which children are actually siblings?** All start without a family, because nothing
   in the data says otherwise and a wrong merge is worse than no merge. Entering a family
   is one text in the child's row. Until then the model behaves exactly as it did before
   the family existed.
7. ~~AP022 / AP025~~ Settled: one person, merged into AP025 on 2026-09-05, AP022
   removed. The Stauffer AHV collision (C1079 / C1083) is with Wegpiraten for
   clarification.
8. *(Withdrawn 2026-09-04 — asked whether `application_number` should be cleaned.
   It should not; the practice is deliberate. See* Invoice delivery channels*.)*
9. ~~Mandate numbering~~ **Settled 2026-09-22, with Wegpiraten:**
   `mandate_id` = `A` + two-digit start year + three-digit counter, the counter
   reset to 0 at the start of each year — e.g. start 25.11.2025 → `A25089`
   (assumed: the 89th mandate of 2025 by `start_date` order; the message that
   set this rule wrote "25089 (98. Auftrag aus 2025)", which does not match its
   own digits — read as a typo for 89th), start 07.01.2026 → `A26001`. Applies
   uniformly, including the 86 already-migrated mandates — **as a structural
   decision, not applied to the sandbox's current demonstration IDs (A1000–
   A1083) in this pass.** Wegpiraten's own framing: this document fixes the
   data *structure*; the actual renumbering is content, produced by the
   eventual migration of the real data, not by editing the sandbox now. Two
   details the rule as given does not cover and that migration will need:
   - **Tie-break for the counter's order.** By `start_date` ascending is the
     working assumption; two mandates opened on the same date need a second
     sort key (entry order in the source data, most likely).
   - **Applied in the test build 2026-09-24** (`sandbox/prepare.py`, `build_mandate_numbers`):
     counter by `start_date` ascending, tie-break on the former client number, which
     is kept in `mandate.notes` (`Bisherige Klientennummer C1002.`). Person numbers keep
     the digits of the lowest former client number, so persons and mandates no longer
     share digits. Visual test only, not the production migration.
   - **Downstream renumbering cost**, unchanged from the earlier note: the new
     digits replace the ones `service_data.client_id`, archived timesheet cell
     G8 and existing invoice numbers carry today. Same class of migration as
     the `client_id` → `A`+digits move already made once (see *Identifiers*),
     done again.

10. **Free-text application numbers of other payers.** KESB mostly use `yyyy-nnnn`
    (`2024-1987`), not without exceptions. No effect today. It could matter for
    case-level reporting; then a notation per payer would have to be decided, as for
    `P1000`. Open with Wegpiraten.
11. **`Bericht` vs. `Zwischenbericht`.** Treated as two forms of report. Where they
    differ — content, recipient, deadline — is unclear.
12. **Are there cadences tied to the Leistungsbesteller?** The cadence stays on the
    mandate for now, as an optional field. If the reports of one requester follow one
    rhythm, it would move there.
13. **Abschlussbericht per mandate.** Imported from the blue cells. Does every mandate
    in a chain get one, or only the last?
14. **State of past reports.** Where does the done-state of reports before today come
    from? Their `status` is empty.

## Reporting

**Scope: the family, not the mandate-person and not the child alone.** Wegpiraten,
22.09.2026: Accordix mandates are family facts, not child facts — the same
reasoning settled in point 2/3 of *Open questions* (a mandate covers the whole
family whether or not every child has an explicit care row, and a birth or a
changed assignment basis is always a new mandate for the family, not an edit
within one). Reporting follows the same scope: **it is reported on the family.**
Consequence for the entity below: it keys on `mandate_id`, not on `family_id`
directly or on `mandate_person`. That is not a contradiction — a mandate already
*is* the family-level unit (see `family` above: most children have no `family`
row at all, the mandate stands in for it), so keying on the mandate is the
family scope, without requiring a `family` row to exist first.

### report

**Status: PoC, built 2026-09-22, expected to change after review** — Wegpiraten's
own framing for this pass: build it into the workbook now, with the ordinary
probability of revision once looked at, rather than wait for the reporting model
to be fully settled first. Berichtsart and Fälligkeitsregel are not finally
decided; this is the first concrete shape, not the last.

One row is one concrete report, due or done, for one mandate.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `report_id` | text | no | PK; `R` + digits |
| `mandate_id` | text | no | → `mandate`; entered via a labelled choice, same idiom as `predecessor_mandate_id` |
| `due_date` | date | yes | when the report is due |
| `report_form` | code | yes | `Bericht` / `Zwischenbericht` / `Abschlussbericht` — what distinguishes the first two is not yet clear (open question 11) |
| `status` | code | yes | `offen` / `erledigt` / `entfällt` |
| `completed_date` | date | yes | |
| `notes` | text | yes | free text for anything the fields above don't capture — recipient detail, coordination between two staff on the same family, tandem notes |

Derived, not stored: `index_person_name`, `service_type_name`, `requester_name`
(all read off the mandate, for readability) and `assigned_employee_id` /
`assigned_employee_name` — the mandate's primary care person (`role` = `P` in
`relation_mandate_emp`), so assignment follows from who is already marked
responsible rather than being entered a second time. Where the mandate has no `P`,
the assignment cannot resolve and the row is marked (invariant 41).

**Table and rule are separate (2026-09-25).** `report` is a to-do and lookup list —
status, done-on — not a rule engine. `cadence` and `interval_months` moved to
`mandate` (`report_cadence`, `report_interval_months`) on Stephan's reading that
they belong to the order; they stay there for now and are optional; whether cadences
related to the Leistungsbesteller exist is open question 12. `suggested_next_due` was dropped with them.

**Filled 2026-09-25 from `sandbox/2026 Klientenübersicht.xlsx`** (`sandbox/import_reports.py`,
seed file `reports_import.json`, findings in `klaerung_berichte_2026-09-25.md`). Red cells
are `Bericht`, orange cells `Zwischenbericht`; a red cell carries no date, only its month
(row 4), so the middle of the month (the 15th) is assumed; an orange cell's own date counts
when it matches the column's month. Blue cells (*Abschluss + Bericht*) are imported as
`Abschlussbericht` (decided 2026-09-25); their own date often carries a wrong year, so the
authorisation end of the mandate is used when it falls in that month (open question 13). The employee sheets are the main
source, the overview is checked against them, because the overview is not necessarily
current; deviations are listed, not resolved. Status is `offen` from today on; earlier
rows have none, since the overview knows no done marker (open question 14).

**Not modelled, on purpose, for this pass:** `ereignisbezogen` reports (e.g.
*"Kurzberichte nach Besuchen"*) have no due date to compute at all; `notes` is
where they live for now. A recurring rule that spawns its own rows, and the
*Terminzettel* proposal below, both wait for the cadence question to be settled first.

**Invariants** (continuing the numbering above):

| # | Invariant | Severity |
| --- | --- | --- |
| 37 | `report_id` unique | error |
| 38 | `report.mandate_id` exists in `mandate` | error |
| 39 | `status` = `offen`, `due_date` set and in the past | warning |
| 40 | `status` = `erledigt` and `completed_date` empty | warning |
| 41 | `mandate_id` set but no `relation_mandate_emp` row of that mandate has `role` = `P` (assignment cannot resolve) | warning |

**Monthly task list ("Terminzettel"), proposal, still not built.** Wegpiraten's
own proposal: alongside timesheet generation, list what is due this month per
employee. Wegpiraten's own caution, 22.09.2026: if built, as its **own `make`
target, run separately from timesheet generation** — not folded into that
pipeline, because a shared failure point there is worse than one more manual
step. Still not started, and still not started on purpose: it reads `report`,
and `report`'s own cadence rules are the PoC piece most likely to change: better
to let one round of real use on the table above settle before building a second
feature on top of it. `src/` changes stay frozen until the table model is
accepted regardless — see the top of this document and `AGENTS.md`/`CLAUDE.md`.

### Target architecture: a Python reporting engine on SQLite, not Excel formulas

Proposed by Stephan, 22.09.2026, for later: read this workbook into SQLite —
after the corresponding programs are adjusted — and generate every report from
SQLite, not from Excel formulas at runtime. Checked against the current code
rather than taken on faith:

- **This is already how Accordix reporting works.** `reports/accordix_report.py`
  reads `sqlite3` directly; the Excel workbook is only ever the *input* to
  `import-master`. Extending the reporting engine to `report`/the Terminzettel is
  not a new architecture, it is the existing one applied to one more table.
- **The importer is config-driven, which lowers the cost of the schema change.**
  `data_imports/import_masterdata.py` maps Excel table name → SQLite table via
  `DEFAULT_TABLE_MAPPINGS` (plus `FOREIGN_KEY_MAPPINGS`) and reads each generically
  through a Pydantic entity model — it is not one bespoke function per table. The
  new sheets' Excel table names (`mandate`, `person`, `mandate_person`,
  `relation_mandate_emp`, `report`) were already chosen to be
  these mapping keys; see the *Glossary* table above. Adding them is entries in
  two dicts plus one entity class each, not a rewrite of the importer.
- **"Transaktionsdaten weitgehend unbetroffen" is right about the records, not
  quite right about the code untouched.** `service_data` itself (the actual
  booked hours) does not change. But `invoice_processor.py` and
  `time_sheets/modules/client_data.py` both `JOIN clients c ON … c.client_id`
  today; after migration that join target is `mandate`/`mandate_id`. Same
  business logic, one renamed join on each side — the size of change this
  document already priced in under *Identifiers* and the Stufe 1/2 table in the
  concept document, not a new cost.
- **Genuinely new, not a schema-driven extension:** the report generator itself
  — nothing today reads `report` or produces a Terminzettel, because the table
  did not exist before this session. That is the actual engineering work in this
  proposal; the SQLite plumbing around it is mostly already there.

Not started, same reason as everywhere else in this section: `src/` stays frozen
until the table model is accepted, and `report`'s own fields are a PoC likely to
move.
