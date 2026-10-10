# DM-07: Sandbox archive, 2026-10-10

Stephan explicitly requested cleanup before the outstanding Windows Excel and August
Accordix checks. Cleanup preserves their inputs instead of waiting or deleting them.

| Content | Destination | Status |
| --- | --- | --- |
| All 43 sandbox files, including nested prior workbooks | `archiv/umstellung_datenmodell_2026-10-10/sandbox/` | Local ignored archive; SHA-256 and size verified for every file |
| Full per-file inventory | `archiv/umstellung_datenmodell_2026-10-10/manifest.json` | Local ignored manifest |
| One-off migration regression tests | `archiv/umstellung_datenmodell_2026-10-10/tests/` | Archived with matching scripts; no active pipeline dependency |
| Windows Excel checker | `tools/excel_pruefung.ps1` | Retained in Git; obsolete family-sheet sample corrected |
| Final workbook, findings, checker and handover note | `output/uebergabe_datenmodell_2026-10-10/` | Local ignored handover directory; workbook byte-identical to final build |
| August Accordix comparison source | Archive sandbox, `Import-Accordix_ambulant_August_2026.xlsx` | Retained for DM-41 |

The archive is local within the project's existing ignored `archiv/` directory. No customer
files enter Git. Old migration scripts are retired from the active checkout; historical
build commands and journal paths remain labelled as history. Restore the archived sandbox
and its test directory together if a historical build needs investigation. Do not regenerate
the customer's authoritative workbook from those sources.

The handover filename is `wegpiraten_datenbank.xlsx`, matching the configured operating
source. DM-06 Windows Excel acceptance and actual delivery remain open. Cleanup does not
claim either was performed. The workbook was copied without resaving or recalculating, so
its formula caches and layout are preserved.

Validation: all 43 archived file hashes and sizes match; handover workbook hash matches the
archived final workbook. 35 active tests passed after retiring three one-off migration tests;
`nox` lint/typecheck passed. The live database and other working directories were untouched.
