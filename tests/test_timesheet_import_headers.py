"""
Tests für die Header-Erkennung beim Timesheet-Import.
"""

from data_imports.batch_import_timesheets import TimeSheetsImporter


def test_travel_time_header_accepts_known_variant() -> None:
    """Die bestehende Vorlage mit 'Fahrzeit' wird als Variante von 'Fahrtzeit' akzeptiert."""
    assert TimeSheetsImporter._label_matches("fahrzeit", "fahrtzeit")


def test_travel_time_header_rejects_unknown_variant() -> None:
    """Unbekannte Header bleiben ungültig, damit Strukturfehler sichtbar bleiben."""
    assert not TimeSheetsImporter._label_matches("reisezeit", "fahrtzeit")
