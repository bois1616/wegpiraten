"""Einheitliche Datumsgrenzen für die gemeinsame Zuordnung MA."""

import sqlite3
from datetime import date


def assignment_window_sql(alias: str = "r") -> str:
    """SQL mit zwei Parametern: Fensterende, Fensterbeginn; leere Grenzen sind offen."""
    return (
        f"COALESCE({alias}.is_active,1)=1 "
        f"AND (NULLIF({alias}.valid_from,'') IS NULL OR date({alias}.valid_from)<=date(?)) "
        f"AND (NULLIF({alias}.valid_to,'') IS NULL OR date({alias}.valid_to)>=date(?)) "
        f"AND (NULLIF({alias}.valid_from,'') IS NULL OR NULLIF({alias}.valid_to,'') IS NULL "
        f"OR date({alias}.valid_from)<=date({alias}.valid_to))"
    )


def assigned_employees(conn: sqlite3.Connection, mandate_id: str, start: date, end: date) -> set[str]:
    """Liest jedes im inklusiven Fenster gültige Paar genau einmal."""
    return {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT r.employee_id FROM relation_mandate_emp r WHERE r.mandate_id=? AND "
            + assignment_window_sql(),
            (mandate_id, end.isoformat(), start.isoformat()),
        )
        if row[0]
    }
