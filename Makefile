# Wegpiraten – Makefile
# Verwendung: make <ziel> [MONTH=...]
#
#   make invoices      MONTH=02.2026   Rechnungen erstellen        (Format MM.YYYY)
#   make timesheets    MONTH=2026-02   Zeiterfassungsbögen erstellen (Format YYYY-MM)
#   make import-master                 Stammdaten importieren
#   make import-sheets MONTH=2026-02   Zeiterfassungsbögen importieren
#   make validate                      Konfiguration prüfen
#
# MONTH wird beim ersten Aufruf in .month gespeichert und für Folgeaufrufe
# als Default verwendet. Ein neues MONTH= überschreibt den gespeicherten Wert.

-include .month

CLI := .venv/bin/wegpiraten

.PHONY: invoices timesheets import-master import-sheets validate _require-month _save-month

invoices: _require-month _save-month
	$(CLI) invoice $(MONTH)

timesheets: _require-month _save-month
	$(CLI) timesheet $(MONTH)

import-master:
	$(CLI) import-master

import-sheets: _require-month _save-month
	$(CLI) import-sheets $(MONTH)

validate:
	$(CLI) validate

_require-month:
	@test -n "$(MONTH)" || (echo "Fehler: MONTH nicht gesetzt. Beispiel: make $(MAKECMDGOALS) MONTH=2026-02" && exit 1)

_save-month:
	@echo "MONTH := $(MONTH)" > .month
