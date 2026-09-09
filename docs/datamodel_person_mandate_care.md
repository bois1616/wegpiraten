# Data model: person, mandate, care

Specification of the entity model that replaces the single `clients` table, as
realised in `sandbox/wegpiraten_datenbank.xlsx`. Written to be lifted into
`wegpiraten_v2` without the Excel specifics.

Rationale, worked examples and the customer-facing explanation live in
[konzept_person_auftrag_leistung.md](konzept_person_auftrag_leistung.md). This
document carries the part a second implementation needs: fields, keys,
invariants and the migration rules that produced the current data.

Revised 2026-09-04 after two rounds of review: the ID prefixes, the short code
moving to the child, contact persons becoming their own entity, the separation of
*Betreuungskind* from *Abrechnungskind*, and `family` as the entity that carries
the billing child. The last two reverse changes made earlier the same day; the
reasoning is under [mandate_person](#mandate_person) and [family](#family).

This model is a workaround for a workbook, not a general case-management schema.
It is cut to what the Accordix report and the invoice need. Where it stops short
on purpose, it says so.

## Glossary

The domain language is German and stays German. Technical identifiers are
English. The mapping is fixed:

| Domain term | Entity | Excel table | Excel sheet |
| --- | --- | --- | --- |
| Familie | family | `masterdata_family` | Familien |
| Kind | person | `person` | Kinder |
| Auftrag | mandate | `mandate` | Aufträge |
| Betreuung | care | `mandate_person` | Betreuungen |
| Ansprechperson | contact person | `masterdata_contact_person` | Ansprechpersonen |
| Zuordnung Mitarbeitende | mandate–employee link | `relation_mandate_emp` | Zuordnung MA |
| Betreuungskind | cared-for child | `mandate_person` row | Betreuungen |
| Abrechnungskind | billing child | `family.billing_person_id` | — |
| Kurzzeichen | short code | `person.short_code` | — |
| Bewilligung von / bis | authorisation period | `mandate.start_date` / `end_date` | — |
| Eintritt / Austritt | care period | `mandate_person.start_date` / `end_date` | — |
| Kontingent | quota | `mandate.allowed_*` | — |
| Vorgängerauftrag | predecessor mandate | `mandate.predecessor_mandate_id` | — |

`mandate_person` keeps the name the concept document uses. `care` is the
shorthand in prose; do not introduce it as an identifier.

## Identifiers

`C…` is a child, `A…` a mandate, `AP…` a contact person.

The digits carry over from the old `client_id`: `C1002` became `A1002`. The
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

Today's `01.2025-C1002` looks like it names the billing child, and in the old
model there was no way to tell: one `clients` row was the child *and* the
mandate, so both readings produce the same string. The code takes it from
`service_data.client_id`, which the importer read out of cell G8 — that is the
mandate.

The distinction becomes load-bearing the moment a child is the billing child of
two mandates at once, and four already are:

| Billing child | Mandates | Service types | Payers | Overlap | Staffed |
| --- | --- | --- | --- | --- | --- |
| C1019 Zwinggi Challco | A1019, A1070 | ST01, ST04 | P1000 both | 12.01.–31.05.2026 | both |
| C1035 Perren | A1035, A1059 | ST04, ST01 | P1000 both | 16.06.2025–31.10.2026 | both |
| C1050 Burri | A1050, A1077 | ST01, ST07 | P1000 / P1005 | 01.06.–31.08.2026 | both |
| C1053 Levic | A1053, A1054 | ST01, ST04 | P1000 both | 01.02.–31.05.2026 | neither |

Keying the number on the child alone gives Perren the same invoice number twice
a month for seventeen months. Three options, and the choice belongs to
Wegpiraten because it is visible to the authority:

1. **Number from the mandate** — `01.2027-A1002`. Unique by construction. The
   letter changes once on running mandates, which recipients see.
2. **Number from the billing child** — `01.2027-C1002`. Nothing changes for the
   78 children with a single mandate, and it breaks for the four above.
3. **Number from the billing child plus service type** — `01.2027-C1050-ST07`.
   Keeps the C number, and invariant 20 is exactly what makes it unique: two
   mandates of the same service type for the same child must not overlap. Costs
   one lookup in `create_invoice_id`, and the extra hyphen is safe — `file_stem`
   in [invoice_processor.py:527](../src/invoices/modules/invoice_processor.py#L527)
   separates fields with underscores, not hyphens.

Whichever is chosen, the grouping key in
[invoice_processor.py:302](../src/invoices/modules/invoice_processor.py#L302)
stays the mandate. Grouping by the child would merge two mandates with the same
payer onto one invoice — C1019, C1035 and C1053 all have that constellation —
and mix two service types at two hourly rates into one position list.

## Entities

### person

One row per child, ever. Holds what is true of the child regardless of which
mandate is running.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `person_id` | text | no | PK; `C` + digits |
| `short_code` | text | yes | Kurzzeichen; appears in timesheet cell C8 and in the file name |
| `family_id` | text | **yes** | → `family`; set only where siblings exist |
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
| `application_number` | text | yes | authority's case number |
| `start_date`, `end_date` | date | `end_date` yes | **authorisation**, not entry/exit |
| `allowed_travel_time` | number | yes | hours per month |
| `allowed_direct_effort` | number | yes | hours per month |
| `allowed_indirect_effort` | number | yes | hours per month |
| `allocation` | code | yes | assumption: per mandate, see open questions |
| `predecessor_mandate_id` | text | yes | → `mandate`; singly linked |
| `notes` | text | yes | internal |

Derived, not stored: `family_id` (the family of the children cared for in this
mandate), `billing_person_id` (that family's), `short_code` (the billing child's)
and `sr_ap_gender` / `sr_ap_first_name` / `sr_ap_last_name` (the contact
person's). The workbook computes all six; a v2 schema can compute them in a view. Keeping the three
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
an Accordix line, and it is the reason the billing marker cannot live here.

An intermediate version on 2026-09-04 stored `is_billing_case` on this entity and
derived the mandate's child from it, on the argument that the children are
entered here anyway. The argument holds; the model does not. Children and
mandates are many-to-many in both directions at once, and the billing child is a
third thing again:

- **One mandate, several children** — siblings in one authorisation.
- **One child, several mandates** — two services running in parallel.
- **Both mixed** — the older child has two mandates, the younger one. Or: the
  younger child's mandate has expired while the older child's runs on.

In the last case the billing child has no care row in the running mandate at all,
because it is not receiving the service — and adding one to carry the flag would
report a child to Accordix who is not in care.

The rule Wegpiraten applies is *the youngest child of the family*, and it does not
move when a mandate expires. That makes the billing child a property of the
family, which is why it lives on `family` and not here. A mandate inherits it
through the children it cares for.

`start_date` is the entry into the care, not into the current authorisation. It
can predate every recorded mandate, because mandates before the record began
were never entered. In all 86 migrated rows it equals `mandate.start_date` —
that is an artefact of the old model having one date, not a rule. On a renewal
the entry date carries over from the predecessor's care row; invariant 21
watches for that.

### family

The entity that carries relationship knowledge. Added 2026-09-04, after two
attempts to put the billing child somewhere else both failed.

| Field | Type | Null | Note |
| --- | --- | --- | --- |
| `family_id` | text | no | PK; `F` + digits |
| `label` | text | yes | `Nachname, Wohnort`, so a human recognises the row |
| `billing_person_id` | text | no | → `person`; must belong to this family |
| `notes` | text | yes | internal |

**It cannot be derived, and that is the whole point.** Nothing in the data
identifies a household:

- `residence_legal_guardian` is a municipality, not an address — Interlaken holds
  13 children, Unterseen 9.
- `application_number` is the KJA-FS Antrags-Nr., and it only exists where the
  invoice goes through KJA-FS. In 29 of 86 rows it holds `beendet`, `brief`,
  `Sonderfall`, `on hold` instead — see *Invoice delivery channels* below. A field
  that is empty by construction for part of the corpus cannot key anything.
- Surname plus municipality produces false positives. C1002 Luan and C1068 Yarrah
  Orion Nipote, both Meiringen, both SPF at SR006, birth dates nine years apart —
  the pattern the concept document had flagged as the prime sibling candidate.
  Wegpiraten says they are two families.

Patchwork settles it: which children belong together is relationship knowledge
that only a person has. It gets entered or it does not exist.

`person.family_id` is a single reference with no history. A child moving between
households is a deliberate edit, not the silent overwrite that lost the
`predecessor_mandate_id` chain, and no requirement for household history has come
up. If one does, a `family_person` link table with validity dates is a lossless
migration from here.

**The reference is optional, and the table starts empty.** Where a child has no
family, the mandate takes the child it serves as the billing child. That is the
same answer the family would give for a family of one, so 82 placeholder rows
would have carried nothing. A family gets created when siblings actually appear —
which is the moment someone has the knowledge to fill it.

The gate moved with it: a mandate serving **more than one child** without a family
is an error, because then nothing determines which child is billed. One child, no
family, is normal.

**Merging two families** is two cells: give both children the same `family_id`,
then set that family's `billing_person_id` to the younger child. Every mandate of
both children follows, including the short code on the timesheets. The emptied
family reports itself as *Familie ohne Kinder* and can be deleted. Verified by
simulating the merge of C1002 and C1068 against the workbook: 0 errors, 1 warning.

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
`is_billing_case` flag from the concept's stage 1 unnecessary as a guard against
double invoicing.

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
| 6 | a `person.family_id`, **where set**, exists in `family` | error |
| 7 | *(withdrawn — the billing child need not have a care row, and since it is derived it cannot be typed wrong)* | — |
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
| 24 | `family.billing_person_id` belongs to that family | error |
| 25 | `family.billing_person_id` is the youngest member of the family | warning — patchwork can justify otherwise |
| 26 | all children cared for in one mandate belong to one family | warning |
| 28 | a mandate serving more than one child has a family | error |
| 27 | every family has at least one member | warning — an emptied family after a merge |

Invariant 18 deserves the emphasis. `validate_coded_value` in
`shared_modules/accordix.py` compares exactly, so `Keine weitere Leistung` is
rejected where `keine weitere Leistung` passes. Excel's `COUNTIF` is
case-insensitive and silently accepts both, which is why the workbook uses
`SUMPRODUCT(--EXACT(list, cell))` instead. A validator in v2 must compare
case-sensitively or it will pass data that Accordix rejects. Sixteen legacy
values fail it today.

Invariant 20 fires on nothing in the current data — all 86 mandates are checked
and none overlap. It is a guard for what happens next: a renewal entered as a
second parallel mandate instead of a successor is the mistake the model now
makes visible. When two of the same service genuinely run at once, the warning
is correct and stays.

Invariant 21 also fires on nothing today, for a duller reason: no chain exists
yet.

Invariants 24 to 26 are what the family entity buys. 24 and 25 sit on the family,
where the decision is made once. 26 catches the mandate that covers children from
two families, which means either the families are wrong or it should be two
mandates.

The class of error that disappeared entirely: two mandates of one family naming
different billing children. It is unrepresentable now — they read the same family
row.

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
contact persons and families added 2026-09-04. Result: 82 persons, 82 families,
86 mandates, 86 cares, 45 contact persons, 91 employee links.

**Person identity.** Group rows by AHV number, but only where the number starts
with `756.` *and* first and last name agree. The `Privat` placeholder in the AHV
column is not an identity — three rows carry it and stay separate. Four groups
merged: A1019+A1070, A1035+A1059, A1050+A1077, A1053+A1054. `person_id` is `C`
plus the digits of the lowest number in the group.

The name condition is not decoration. A1079 and A1083 share `756.2404.7951.71`
but are Caroline and Marlon Til Stauffer — merging on AHV alone would have made
them one child. They stay separate and invariant 14 keeps reporting them until
the number is corrected.

**Families.** One per child, `F` plus the child's digits, labelled
`Nachname, Wohnort`, billing over that one child. Not a guess dressed up as data:
it is what the records support, and it makes the model behave exactly as the old
one did until someone merges two rows.

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

## Invoice delivery channels

Recorded here because it explains a field that looks broken and must not be
repaired, and because nothing else in this repository writes it down. From
Wegpiraten, 2026-09-04.

How an invoice reaches the authority depends on the Leistungsbesteller, and the
three paths do not share a format:

| Path | Upload | Number range | File name |
| --- | --- | --- | --- |
| KJA-FS | bulk, up to 50 PDFs | KJA-FS Antrags-Nr. | fixed scheme, fields separated by `_` |
| KESB, billed directly | none | different, unrelated | free |
| Exceptions | none | — | letter or e-mail with the PDF attached |

Only the first has an Antrags-Nr. at all, which is why `application_number` is
empty of meaning for the other two — and why operators put the channel there
instead. `beendet`, `brief`, `Sonderfall`, `on hold` are that marker, on 29 of 86
mandates.

**Do not encode this.** The author's reason: *«Das kann man nicht kodieren ohne
Millionen von exotischsten Sonderfälle zu beachten.»* A channel enum would need a
branch per authority and per exception, and the exceptions are where the domain
keeps moving. One overloaded optional field, read by a human at the moment of
sending, is the cheaper failure mode.

The one thing worth knowing when reading the data: a missing Antrags-Nr. on a
KJA-FS mandate looks exactly like a channel marker. It is caught downstream —
KJA-FS rejects the upload — not here.

## Excel-specific decisions

Relevant only while the master data lives in a workbook; v2 can ignore this
section.

**Column order carries a rule.** Every editable column comes first, without
gaps; every computed column follows, marked `▸`, filled grey and locked. The
boundary is where the white cells stop. Two things depend on it: sheet
protection is legible without reading a legend, and the entry masks can hand
over one contiguous row to paste.

**Sheet protection** is on for all generated sheets, without a password.
Editable columns are unlocked through the column default style, so rows added
below the data are writable without touching 2000 cells per column. Inserting
rows, deleting rows, sorting and filtering stay allowed. This stops a formula
being overwritten by a typed value; it stops nothing else, and it is meant to be
lifted with one click when someone needs to.

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

**Two hidden helper columns** on Betreuungen: `billing_key` (the mandate number,
but only on the row flagged as the billing case, so the mandate's lookup is a
single `MATCH`) and `predecessor_mandate_id` (the mandate's predecessor, so
invariant 21 does not need a nested lookup inside `SUMIFS`).

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
acceptable entry process is won or lost, not in the number of checks: the 31 checks
sit on their own sheet and cost the person entering data nothing. Only gates —
mandatory fields, restricted dropdowns, an extra sheet on the critical path — do.
So the family stopped being a gate and the masks went.

**The former `Klienten` sheet** is kept, hidden and renamed `Klienten (alt)`.
Its formulas referenced the deleted `masterdata_client` table and were frozen to
their last computed values.

**Recalculation** of the whole workbook takes about 6 seconds in headless
LibreOffice, with `MAX = 2000` rows of formula reserve (7.2 s measured, minus a
1.0 s start measured on a trivial file). The quadratic formulas — invariant 20
over every pair of care rows, invariant 25 over every family against every child
— account for most of the growth from 4.7 s. Cheap enough at this size; worth
remembering if `MAX` ever grows.

## Open questions

Carried forward from section 7 of the concept; the workbook implements the first
reading of each and marks it on the `Anleitung` sheet.

1. Quota per mandate or per child? Implemented on the mandate. If it is granted
   per child, the three `allowed_*` fields move to `mandate_person`.
2. Can `allocation` differ between siblings? Implemented on the mandate.
3. Does a newborn sibling create a new mandate, or does the existing one change
   its billing child? Both are representable; which one happens is unknown. The
   second is one cell per mandate of the family — and invariant 24 points at the
   mandates that still need it.
4. Accordix entry date: first mandate of the chain, or the running one? The
   model no longer needs the chain to answer it — `mandate_person.start_date` is
   the entry into the care and is maintained by hand, which is the only way to
   record an entry that predates the data. What Accordix expects in column Q is
   still open with Wegpiraten; both readings are servable, the second as
   `mandate.start_date`.
5. Which of the current mandates cover more than one child? Not derivable from
   the data, but two candidate sibling groups fall out of matching last name and
   guardian residence:

   | Children | Mandates | Note |
   | --- | --- | --- |
   | C1002 Luan (10.03.2017), C1068 Yarrah Orion (08.05.2026) Nipote, Meiringen | A1002 ST01 to 31.03.2027, A1068 ST01 to 31.08.2026 | same service, same requester SR006. If one family, the billing child should be Yarrah on both — and A1068 expired on 31.08.2026, which is exactly the mixed case above |
   | C1015 Flurin (19.12.2023), C1078 Laura (no date of birth) Loosli, Unterseen | A1015 ST01 to 31.08.2027, A1078 ST08 to 10.07.2026 | same requester SR011, different services. Not previously spotted |

   C1079 Caroline and C1083 Marlon Til Stauffer share a last name and the
   disputed AHV number; C1079's mandate is ST99 `PRIVAT` via SR999, so it is a
   privately paid service rather than an authority mandate.

6. **Which children are actually siblings?** All 82 start as their own family,
   because nothing in the data says otherwise and a wrong merge is worse than no
   merge. Every merge Wegpiraten makes is two cells. Until then the model behaves
   exactly as it did before the family existed.
7. Are AP022 and AP025 the same person with the names swapped? Data, not schema.
8. *(Withdrawn 2026-09-04 — asked whether `application_number` should be cleaned.
   It should not; the practice is deliberate. See* Invoice delivery channels*.)*
