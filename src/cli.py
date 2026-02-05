"""
Wegpiraten CLI - Zentraler Einstiegspunkt für alle Batch-Operationen.

Verwendung:
    python -m cli <command> [options]

Befehle:
    invoice         Rechnungen für einen Abrechnungsmonat erstellen
    timesheet       Neue Zeiterfassungsbögen für einen Monat erstellen
    import-master   Stammdaten aus Excel in SQLite importieren
    import-sheets   Ausgefüllte Zeiterfassungsbögen importieren
"""

from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console

from shared_modules.config import DEFAULT_CONFIG_PATH, Config

app = typer.Typer(
    name="wegpiraten",
    help="CLI für Zeiterfassung und Rechnungsstellung",
    add_completion=False,
)
console = Console()


def get_config(config_path: Optional[Path] = None) -> Config:
    """Lädt die Konfiguration."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        console.print(f"[red]Konfigurationsdatei nicht gefunden: {path}[/red]")
        raise typer.Exit(1)
    return Config(path)


@app.command("invoice")
def invoice_batch(
    month: str = typer.Argument(
        ...,
        help="Abrechnungsmonat im Format MM.YYYY (z.B. 01.2025)",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Pfad zur Konfigurationsdatei (Standard: .config/wegpiraten_config.yaml)",
    ),
) -> None:
    """
    Erstellt Rechnungen für einen Abrechnungsmonat.

    Liest die Leistungsdaten aus der Datenbank und generiert PDF-Rechnungen
    für alle Klienten, gruppiert nach Zahlungsdienstleister.
    """
    console.print(f"[bold blue]Starte Rechnungserstellung für {month}...[/bold blue]")

    try:
        config = get_config(config_path)

        from invoices.modules.invoice_filter import InvoiceFilter
        from invoices.modules.invoice_processor import InvoiceProcessor

        filter_obj = InvoiceFilter(invoice_month=month)
        processor = InvoiceProcessor(config=config, filter=filter_obj)
        processor.run()

        console.print("[bold green]Rechnungserstellung erfolgreich abgeschlossen.[/bold green]")
    except Exception as e:
        logger.exception(f"Fehler bei der Rechnungserstellung: {e}")
        console.print(f"[red]Fehler: {e}[/red]")
        raise typer.Exit(1)


@app.command("timesheet")
def create_timesheets(
    month: str = typer.Argument(
        ...,
        help="Monat für die neuen Zeiterfassungsbögen im Format YYYY-MM (z.B. 2025-02)",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Pfad zur Konfigurationsdatei",
    ),
) -> None:
    """
    Erstellt leere Zeiterfassungsbögen für einen Monat.

    Generiert für jeden aktiven Klienten einen leeren Excel-Zeiterfassungsbogen
    basierend auf der Vorlage und den Stammdaten.
    """
    console.print(f"[bold blue]Erstelle Zeiterfassungsbögen für {month}...[/bold blue]")

    try:
        config = get_config(config_path)

        from time_sheets.modules.time_sheet_batch_processor import TimeSheetBatchProcessor
        from time_sheets.modules.time_sheet_factory import TimeSheetFactory

        factory = TimeSheetFactory(config)
        processor = TimeSheetBatchProcessor(config, reporting_factory=factory)
        processor.run(reporting_month=month)

        console.print("[bold green]Zeiterfassungsbögen erfolgreich erstellt.[/bold green]")
    except Exception as e:
        logger.exception(f"Fehler bei der Erstellung der Zeiterfassungsbögen: {e}")
        console.print(f"[red]Fehler: {e}[/red]")
        raise typer.Exit(1)


@app.command("import-master")
def import_masterdata(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Pfad zur Konfigurationsdatei",
    ),
    source: Optional[Path] = typer.Option(
        None,
        "--source",
        "-s",
        help="Pfad zur Excel-Quelldatei (überschreibt Config)",
    ),
) -> None:
    """
    Importiert Stammdaten aus Excel in die SQLite-Datenbank.

    Importiert Mitarbeiter, Klienten, Zahlungsdienstleister und
    Leistungsbesteller aus der konfigurierten Excel-Datenbank.
    """
    console.print("[bold blue]Importiere Stammdaten...[/bold blue]")

    try:
        config = get_config(config_path)

        from data_imports.import_masterdata import run_import

        count = run_import(config, source_override=source)

        console.print(f"[bold green]{count} Datensätze erfolgreich importiert.[/bold green]")
    except Exception as e:
        logger.exception(f"Fehler beim Import der Stammdaten: {e}")
        console.print(f"[red]Fehler: {e}[/red]")
        raise typer.Exit(1)


@app.command("import-sheets")
def import_timesheets(
    month: Optional[str] = typer.Argument(
        None,
        help="Erfassungsmonat der zu importierenden Bögen im Format YYYY-MM (optional)",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Pfad zur Konfigurationsdatei",
    ),
) -> None:
    """
    Importiert ausgefüllte Zeiterfassungsbögen in die Datenbank.

    Liest alle Excel-Dateien aus dem Eingabeverzeichnis und
    importiert die Leistungsdaten in die SQLite-Datenbank.
    """
    console.print("[bold blue]Importiere Zeiterfassungsbögen...[/bold blue]")

    try:
        config = get_config(config_path)

        from data_imports.batch_import_timesheets import TimeSheetsImporter

        importer = TimeSheetsImporter(config)
        count = importer.run(reporting_month=month)

        console.print(f"[bold green]{count} Einträge importiert.[/bold green]")
    except Exception as e:
        logger.exception(f"Fehler beim Import der Zeiterfassungsbögen: {e}")
        console.print(f"[red]Fehler: {e}[/red]")
        raise typer.Exit(1)


@app.command("validate")
def validate_config(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Pfad zur Konfigurationsdatei",
    ),
) -> None:
    """
    Validiert die Konfigurationsdatei.

    Prüft, ob alle Pflichtfelder gesetzt sind, alle Pfade existieren
    und die Pydantic-Modelle korrekt validieren.
    """
    console.print("[bold blue]Validiere Konfiguration...[/bold blue]")

    try:
        config = get_config(config_path)

        console.print(f"  Projektwurzel: {config.structure.prj_root}")
        console.print(f"  Datenbank: {config.get_db_path()}")
        console.print(f"  Templates: {config.get_template_path()}")
        console.print(f"  Output: {config.get_output_path()}")
        console.print(f"  Locale: {config.get_locale()}")
        console.print(f"  Währung: {config.get_currency()}")
        console.print(f"  Entities: {list(config.models.keys())}")

        console.print("[bold green]Konfiguration ist gültig.[/bold green]")
    except Exception as e:
        console.print(f"[red]Konfigurationsfehler: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Haupteinstiegspunkt für die CLI."""
    app()


if __name__ == "__main__":
    main()
