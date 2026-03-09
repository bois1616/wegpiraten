# Wegpiraten – Makefile
# Verwendung: make <ziel> [MONTH=...] [CLIENT=...]
#
#   make invoices      MONTH=02.2026                    Rechnungen erstellen        (Format MM.YYYY)
#   make invoices      MONTH=02.2026 CLIENT=C1017,C1038 Rechnungen für bestimmte Klienten
#   make timesheets    MONTH=2026-02                    Zeiterfassungsbögen erstellen (Format YYYY-MM)
#   make import-master                                  Stammdaten importieren
#   make import-sheets MONTH=2026-02                    Zeiterfassungsbögen importieren
#   make report        MONTH=2026-02                    Arbeitszeitprotokoll erstellen
#   make validate                                       Konfiguration prüfen
#
# MONTH wird beim ersten Aufruf in .month gespeichert und für Folgeaufrufe
# als Default verwendet. Ein neues MONTH= überschreibt den gespeicherten Wert.

-include .month

CLI := .venv/bin/wegpiraten

.PHONY: help invoices timesheets import-master import-sheets report validate _require-month _save-month

help:
	@echo ""
	@echo "Wegpiraten – verfügbare Ziele"
	@echo ""
	@echo "  make invoices      MONTH=02.2026                    Rechnungen erstellen           (Format MM.YYYY)"
	@echo "  make invoices      MONTH=02.2026 CLIENT=C1017,C1038 Rechnungen für bestimmte Klienten"
	@echo "  make timesheets    MONTH=2026-02                    Zeiterfassungsbögen erstellen  (Format YYYY-MM)"
	@echo "  make import-master                                  Stammdaten importieren"
	@echo "  make import-sheets MONTH=2026-02                    Zeiterfassungsbögen importieren"
	@echo "  make report        MONTH=2026-02                    Arbeitszeitprotokoll erstellen"
	@echo "  make validate                                       Konfiguration prüfen"
	@echo ""
	@echo "  MONTH wird zwischen Aufrufen in .month gespeichert (kein erneutes Angeben nötig)."
	@echo ""

invoices: _require-month _save-month
	$(CLI) invoice $(MONTH) $(if $(CLIENT),--clients $(CLIENT),)

timesheets: _require-month
	$(CLI) timesheet $(MONTH)

import-master:
	$(CLI) import-master

import-sheets: _require-month _save-month
	$(CLI) import-sheets $(MONTH)

report: _require-month _save-month
	$(CLI) report $(MONTH)

validate:
	$(CLI) validate

_require-month:
	@test -n "$(MONTH)" || (echo "Fehler: MONTH nicht gesetzt. Beispiel: make $(MAKECMDGOALS) MONTH=2026-02" && exit 1)

_save-month:
	@echo "MONTH := $(MONTH)" > .month
