# Wegpiraten – Makefile
# Verwendung: make <ziel> [MONTH=...] [CLIENT=...]
#
#   make invoices      MONTH=02.2026                    Rechnungen + Arbeitszeitprotokoll (Format MM.YYYY)
#   make invoices      MONTH=02.2026 CLIENT=C1017,C1038 Rechnungen für bestimmte Klienten
#   make timesheets    MONTH=2026-02                    Zeiterfassungsbögen erstellen (Format YYYY-MM)
#   make import-master                                  Stammdaten importieren
#   make import-master FETCH=1                          Stammdaten vorher von Proton Drive holen
#   make fetch-master                                   Stammdaten-Datei von Proton Drive holen
#   make fetch-timesheets TSDIR="Timesheets - Rechnungen-Auswertungen/2026-06 Juni/Timesheets (ausgefüllt)"
#                                                       Timesheets von Proton Drive holen (relativ zum Basis-Ordner)
#   make import-sheets MONTH=2026-02                    Zeiterfassungsbögen importieren
#   make report        MONTH=2026-02                    Arbeitszeitprotokoll erstellen
#   make accordix      MONTH=2026-02                    Accordix-Leistungsmeldung (ambulant) erstellen
#   make validate                                       Konfiguration prüfen
#
# MONTH wird beim ersten Aufruf in .month gespeichert und für Folgeaufrufe
# als Default verwendet. Ein neues MONTH= überschreibt den gespeicherten Wert.
# TSDIR wird analog in .tsdir gespeichert.

-include .month
-include .tsdir

CLI := .venv/bin/wegpiraten

.PHONY: help invoices timesheets import-master fetch-master fetch-timesheets import-sheets report accordix validate _require-month _save-month _require-tsdir _save-tsdir

help:
	@echo ""
	@echo "Wegpiraten – verfügbare Ziele"
	@echo ""
	@echo "  make invoices      MONTH=02.2026                    Rechnungen + Arbeitszeitprotokoll  (Format MM.YYYY)"
	@echo "  make invoices      MONTH=02.2026 CLIENT=C1017,C1038 Rechnungen für bestimmte Klienten"
	@echo "  make timesheets    MONTH=2026-02                    Zeiterfassungsbögen erstellen  (Format YYYY-MM)"
	@echo "  make import-master                                  Stammdaten importieren"
	@echo "  make import-master FETCH=1                          Stammdaten vorher von Proton Drive holen"
	@echo "  make fetch-master                                   Stammdaten-Datei von Proton Drive holen"
	@echo "  make fetch-timesheets TSDIR='Timesheets - .../2026-06 Juni/Timesheets (ausgefüllt)'"
	@echo "                                                      Timesheets von Proton Drive holen (TSDIR wird gecacht)"
	@echo "  make import-sheets MONTH=2026-02                    Zeiterfassungsbögen importieren"
	@echo "  make report        MONTH=2026-02                    Arbeitszeitprotokoll erstellen"
	@echo "  make accordix      MONTH=2026-02                    Accordix-Leistungsmeldung (ambulant) erstellen"
	@echo "  make validate                                       Konfiguration prüfen"
	@echo ""
	@echo "  MONTH wird zwischen Aufrufen in .month gespeichert (kein erneutes Angeben nötig)."
	@echo "  TSDIR wird zwischen Aufrufen in .tsdir gespeichert (relativ zum Proton-Basis-Ordner)."
	@echo ""

invoices: _require-month _save-month
	$(CLI) invoice $(MONTH) $(if $(CLIENT),--clients $(CLIENT),)

timesheets: _require-month
	$(CLI) timesheet $(MONTH)

import-master:
	$(CLI) import-master $(if $(FETCH),--fetch,)

fetch-master:
	$(CLI) fetch-master

fetch-timesheets: _require-tsdir _save-tsdir
	$(CLI) fetch-timesheets "$(TSDIR)"

import-sheets: _require-month _save-month
	$(CLI) import-sheets $(MONTH)

report: _require-month _save-month
	$(CLI) report $(MONTH)

accordix: _require-month _save-month
	$(CLI) accordix $(MONTH)

validate:
	$(CLI) validate

_require-month:
	@test -n "$(MONTH)" || (echo "Fehler: MONTH nicht gesetzt. Beispiel: make $(MAKECMDGOALS) MONTH=2026-02" && exit 1)

_save-month:
	@echo "MONTH := $(MONTH)" > .month

_require-tsdir:
	@test -n "$(TSDIR)" || (echo "Fehler: TSDIR nicht gesetzt. Beispiel: make fetch-timesheets TSDIR='Timesheets - Rechnungen-Auswertungen/2026-06 Juni/Timesheets (ausgefüllt)'" && exit 1)

_save-tsdir:
	@echo "TSDIR := $(TSDIR)" > .tsdir
