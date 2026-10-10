"""Prüft die Datenübernahme beim finalen Workbook-Build mit synthetischen Daten."""

import importlib.util
from pathlib import Path
from types import ModuleType

from openpyxl import Workbook
from pytest import MonkeyPatch


def load_script(name: str) -> ModuleType:
    """Lädt ein Sandbox-Skript, ohne dessen Build auszuführen."""
    path = Path(__file__).resolve().parents[1] / "sandbox" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_follow_up_preserves_current_number_and_corrects_predecessor(monkeypatch: MonkeyPatch) -> None:
    """Eine Quellnummer des Nachfolgers darf nicht in den Vorgänger gelangen."""
    prepare = load_script("prepare")
    monkeypatch.setattr(
        prepare,
        "FOLLOW_UPS",
        {
            "C9000": {"old_end": "2026-09-30", "old_application_number": "250101001"},
        },
    )
    data = {
        "mandates": [
            {
                "mandate_id": "C9000",
                "start_date": "2025-01-01",
                "end_date": "2027-09-30",
                "application_number": "260901002",
                "notes": "Original",
            }
        ],
        "cares": [
            {
                "mandate_id": "C9000",
                "person_id": "K9000",
                "start_date": "2025-01-01",
                "end_date": None,
                "remarks": "Originalbemerkung",
            }
        ],
        "relations": [{"mandate_id": "C9000", "employee_id": "E9000"}],
        "stats": {},
    }
    prepare.apply_follow_ups(data)
    old, new = data["mandates"]
    assert old["application_number"] == "250101001"
    assert new["application_number"] == "260901002"
    assert new["start_date"] == "2026-10-01"
    assert new["end_date"] == "2027-09-30"
    assert all(m["notes"].startswith("ZU PRÜFEN:") for m in (old, new))
    assert all(c["start_date"] == "2025-01-01" for c in data["cares"])
    assert data["cares"][1]["remarks"] == "Originalbemerkung"
    assert len(data["relations"]) == 2


def test_final_carry_over_excludes_demo_and_preserves_reports(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Berichte bleiben vollständig erhalten, Familien und Rollen kommen aus dem Original."""
    build = load_script("build")
    workbook = Workbook()
    workbook.remove(workbook.active)
    tables = {
        "Kinder": (["person_id", "family_id"], ["C9000", "Demo Familie"]),
        "Zuordnung MA": (["mandate_id", "employee_id", "role"], ["A26090", "E9000", "S"]),
        "Berichte": (
            ["report_id", "mandate_id", "report_form", "notes"],
            ["R9000", "A26090", "Bericht", "Originalnotiz"],
        ),
    }
    for title, (header, row) in tables.items():
        ws = workbook.create_sheet(title)
        ws.append(header)
        ws.append(row)
    path = tmp_path / "hand.xlsx"
    workbook.save(path)
    monkeypatch.setattr(build, "HAND", path)
    monkeypatch.setattr(build, "CARRY_FAMILIES", False)
    monkeypatch.setattr(build, "CARRY_ROLES", False)
    monkeypatch.setattr(build, "MARK_REPORTS", True)
    persons = [{"person_id": "C9000", "family_id": None}]
    relations = [{"mandate_id": "A26090", "employee_id": "E9000"}]
    reports = build.carry_over_handwork(persons, relations)
    assert persons[0]["family_id"] is None
    assert "role" not in relations[0]
    assert len(reports) == 1
    assert reports[0]["mandate_choice"] == "A26090"
    assert reports[0]["notes"].startswith("ZU PRÜFEN:")
    assert reports[0]["notes"].endswith("Originalnotiz")


def test_existing_numbers_stay_fixed(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Ein nachträglich früherer Auftrag verschiebt keine bereits vergebene Nummer."""
    prepare = load_script("prepare")
    path = tmp_path / "numbers.json"
    path.write_text('{"C9000": "A26005"}', encoding="utf-8")
    monkeypatch.setattr(prepare, "NUMBERS", path)
    result = prepare.build_mandate_numbers(
        [
            {"mandate_id": "C9000", "start_date": "2026-10-01"},
            {"mandate_id": "C9001", "start_date": "2026-01-01"},
        ]
    )
    assert result == {"C9000": "A26005", "C9001": "A26006"}
