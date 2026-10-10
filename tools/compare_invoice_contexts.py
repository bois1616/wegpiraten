"""Vergleicht lokale Rechnungskontexte, ohne Personendaten ins Ergebnis zu schreiben."""

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel

from data_imports.legacy_mandates import LegacyMandateResolver
from shared_modules.month_period import get_month_period


class Snapshot(BaseModel):
    """Kontext aus der tatsächlichen Rechnungserzeugung, weitere Felder bleiben erhalten."""

    model_config = ConfigDict(extra="allow")
    invoice_id: str
    client: dict[str, Any]
    positions: list[dict[str, Any]]
    summe_kosten: float
    mandate_id: str | None = None


class Snapshots(RootModel[list[Snapshot]]):
    """Validierte lokale Vergleichsdatei."""


FIELDS = (
    "positions",
    "summe_fahrtzeit",
    "summe_direkt",
    "summe_indirekt",
    "summe_stunden",
    "summe_kosten",
    "service_type",
    "service_type_description",
    "service_requester",
    "client_name",
    "payer",
    "service_provider",
    "tenant_id",
    "tenant_name",
    "tenant_street",
    "tenant_zip",
    "tenant_city",
    "tenant_iban",
    "sr_ap_first_name",
    "sr_ap_last_name",
    "sr_ap_gender",
    "has_intro_position",
    "allowed_travel_time",
    "allowed_direct_effort",
    "allowed_indirect_effort",
    "budget_exceeded",
)


def compare(old_path: Path, new_path: Path, db: Path, mapping: Path, month: str) -> dict[str, Any]:
    """Meldet alle Abweichungen nach alter Auftragsidentität, niemals Namen oder AHV."""
    old = Snapshots.model_validate_json(old_path.read_text()).root
    new = Snapshots.model_validate_json(new_path.read_text()).root
    resolver = LegacyMandateResolver(db, mapping)
    by_new = {r.mandate_id: r for r in new}
    differences: list[dict[str, str]] = []
    matched: set[str] = set()
    for row in old:
        source_id = str(row.client.get("key") or "")
        dates = []
        # Bei einem Wechsel innerhalb des Monats darf kein falscher 1:1-Vergleich entstehen.
        for position in row.positions:
            raw = str(position.get("Leistungsdatum") or "")
            if raw:
                from datetime import date

                dates.append(date.fromisoformat(raw[:10]))
        if not dates:
            dates.append(get_month_period(month).start.date())
        targets = {resolver.resolve(source_id, day)[0] for day in dates}
        if len(targets) != 1:
            differences.append({"old": source_id, "new": ",".join(sorted(targets)), "field": "split_requires_review"})
            continue
        target = targets.pop()
        matched.add(target)
        other = by_new.get(target)
        if other is None:
            differences.append({"old": source_id, "new": target, "field": "missing_invoice"})
            continue
        left, right = row.model_dump(), other.model_dump()
        for field in FIELDS:
            if left.get(field) != right.get(field):
                differences.append({"old": source_id, "new": target, "field": field})
        client_left, client_right = dict(row.client), dict(other.client)
        client_left.pop("key", None)
        client_right.pop("key", None)
        if client_left != client_right:
            differences.append({"old": source_id, "new": target, "field": "client_person"})
    for target in by_new:
        if target not in matched:
            differences.append({"old": "", "new": str(target), "field": "unmatched_new_invoice"})
    return {
        "old_invoices": len(old),
        "new_invoices": len(new),
        "old_invoice_total": sum(round(r.summe_kosten * 100) for r in old) / 100,
        "new_invoice_total": sum(round(r.summe_kosten * 100) for r in new) / 100,
        "old_raw_total": sum(r.summe_kosten for r in old),
        "new_raw_total": sum(r.summe_kosten for r in new),
        "differences": differences,
    }


def main() -> None:
    """Schreibt nur den Vergleichsbericht; die Eingaben bleiben lokal und unverändert."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "new", "database", "mapping", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    result = compare(args.old, args.new, args.database, args.mapping, args.month)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
