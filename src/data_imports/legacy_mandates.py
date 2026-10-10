"""Löst alte Auftragsnummern aus Timesheets je Leistungsdatum auf."""

import sqlite3
from datetime import date
from pathlib import Path

from pydantic import RootModel


class LegacyMapping(RootModel[dict[str, list[str]]]):
    """Unveränderliche technische Zuordnung, ohne Namen oder AHV-Nummern."""


class LegacyMandateResolver:
    """Verwendet nur belegte Zuordnungen und aktuelle Bewilligungszeiträume."""

    def __init__(self, db_path: Path, mapping_path: Path) -> None:
        self.db_path = db_path
        self.mapping_path = mapping_path
        self._mapping: dict[str, list[str]] | None = None

    def candidate_ids(self, source_id: str) -> list[str]:
        """Neue Nummern und SA brauchen kein Legacy-Mapping."""
        if not source_id.startswith("C"):
            return [source_id]
        if self._mapping is None:
            self._mapping = LegacyMapping.model_validate_json(self.mapping_path.read_text()).root
        candidates = self._mapping.get(source_id, [])
        if not candidates:
            raise ValueError(f"Keine belegte Auftragszuordnung für {source_id}")
        return candidates

    def resolve(self, source_id: str, service_date: date) -> tuple[str, bool]:
        """Gibt Auftrag und Bewilligungsüberschreitung zurück; Mehrdeutigkeit ist ein Fehler."""
        ids = self.candidate_ids(source_id)
        with sqlite3.connect(self.db_path) as conn:
            rows = [
                conn.execute(
                    "SELECT mandate_id,date(start_date),date(end_date) FROM mandate WHERE mandate_id=?", (mid,)
                ).fetchone()
                for mid in ids
            ]
        if any(r is None for r in rows):
            raise ValueError(f"{source_id}: Kandidaten fehlen in den Stammdaten: {ids}")
        day = service_date.isoformat()
        valid = [r for r in rows if r and (not r[1] or r[1] <= day) and (not r[2] or day <= r[2])]
        if len(ids) == 1:
            return ids[0], not bool(valid)
        if len(valid) != 1:
            raise ValueError(f"{source_id} am {day}: {len(valid)} passende Aufträge, Kandidaten {ids}")
        return str(valid[0][0]), False
