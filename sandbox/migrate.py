"""Migriert die Klientenliste in das Modell Kind / Auftrag / Betreuung.

Liest sandbox/wegpiraten_datenbank.xlsx (Stand 24.09.2026, aktualisierte Originaldatei)
und schreibt das Ergebnis als JSON neben das Skript, damit der Aufbau der Arbeitsmappe
die Zuordnung nicht noch einmal herleiten muss.
"""

import json
from datetime import date, datetime
from pathlib import Path

import openpyxl

SANDBOX = Path(__file__).parent
SRC = SANDBOX / "wegpiraten_datenbank.xlsx"
OUT = SANDBOX / "migration_neu.json"

# Spalten der Tabelle masterdata_client, Kopfzeile 2, Daten ab Zeile 3.
FIRST_COL, LAST_COL, HEADER_ROW = 2, 37, 2

# Felder, die zum Kind gehören (Anhang A.2 des Konzepts).
PERSON_FIELDS = [
    "social_security_number",
    "last_name",
    "first_name",
    "date_of_birth",
    "gender",
    "uma_umf",
    "spoken_language",
    "canton_of_residence",
    "residence_legal_guardian",
]

# Felder der Betreuung; alle übrigen bleiben beim Auftrag.
CARE_FIELDS = [
    "is_leaving_reason_planned",
    "leaving_reason",
    "custom_leaving_reason",
    "after_leave_situation",
    "custom_after_leave_situation",
    "is_consultative_adolescent_psychiatric_care",
    "number_of_care_days_per_week",
    "remarks",
]

# Austrittsangaben: nur wenn eines dieser Felder gefüllt ist, gilt das
# end_date der Altzeile als Austritt des Kindes und nicht bloss als
# Bewilligungsende (Konzept, Abschnitt 4).
LEAVE_MARKERS = [
    "is_leaving_reason_planned",
    "leaving_reason",
    "custom_leaving_reason",
    "after_leave_situation",
    "custom_after_leave_situation",
]

EXCEL_EPOCH = datetime(1899, 12, 30)


def norm(value):
    """Leere Zellen zu None, Strings trimmen, Excel-Datumszahlen zu datetime."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def as_date(value):
    """Wandelt Datumsangaben inkl. Excel-Serienzahlen in ein date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 10000 < value < 80000:
        return (EXCEL_EPOCH + __import__("datetime").timedelta(days=int(value))).date()
    return None


def iso(value):
    d = as_date(value)
    return d.isoformat() if d else None


def read_clients():
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb["Klienten"]
    header = [ws.cell(row=HEADER_ROW, column=c).value for c in range(FIRST_COL, LAST_COL + 1)]
    rows = []
    for r in range(HEADER_ROW + 1, ws.max_row + 1):
        values = [norm(ws.cell(row=r, column=c).value) for c in range(FIRST_COL, LAST_COL + 1)]
        record = dict(zip(header, values))
        if record.get("client_id"):
            record["_row"] = r
            rows.append(record)
    return rows


def is_real_ahv(value):
    """'Privat' und leere Werte sind keine Identität, sondern ein Platzhalter."""
    return bool(value) and str(value).startswith("756.")


def build_person_groups(rows):
    """Gruppiert Altzeilen zu Kindern.

    Zusammengelegt wird nur bei echter AHV-Nummer UND gleichem Namen. Die
    Kollision Stauffer (gleiche AHV, verschiedene Kinder) bleibt dadurch
    getrennt und wird als Konflikt gemeldet.
    """
    groups, conflicts = {}, []
    by_ahv = {}
    for row in rows:
        ahv = row.get("social_security_number")
        if not is_real_ahv(ahv):
            continue
        by_ahv.setdefault(str(ahv), []).append(row)

    assigned = {}
    for ahv, members in by_ahv.items():
        names = {(r.get("last_name"), r.get("first_name")) for r in members}
        if len(names) > 1:
            conflicts.append(
                {
                    "art": "AHV-Kollision",
                    "ahv": ahv,
                    "client_ids": [r["client_id"] for r in members],
                    "namen": sorted(f"{n[0]}, {n[1]}" for n in names),
                    "entscheid": "nicht zusammengelegt, jede Zeile bleibt ein eigenes Kind",
                }
            )
            continue
        if len(members) > 1:
            key = min(r["client_id"] for r in members)
            for r in members:
                assigned[r["client_id"]] = key

    for row in rows:
        cid = row["client_id"]
        key = assigned.get(cid, cid)
        groups.setdefault(key, []).append(row)
    return groups, conflicts


def pick(members, field, conflicts, person_id):
    """Wählt den Wert eines Kindfelds aus mehreren Altzeilen.

    Datumsfelder werden vorher normalisiert, damit die beiden Schreibweisen
    des Burri-Geburtsdatums (29.10.2018 und 43402) nicht als Widerspruch
    gelten. Echte Widersprüche werden gemeldet, der erste Wert gewinnt.
    """
    is_date_field = field == "date_of_birth"
    values, seen = [], set()
    for row in members:
        raw = row.get(field)
        value = iso(raw) if is_date_field else raw
        if value is None:
            continue
        if value not in seen:
            seen.add(value)
            values.append((value, row["client_id"]))
    if not values:
        return None
    if len(values) > 1:
        conflicts.append(
            {
                "art": "abweichende Kinddaten",
                "person_id": person_id,
                "feld": field,
                "werte": [{"wert": str(v), "aus": cid} for v, cid in values],
                "entscheid": f"übernommen: {values[0][0]} (aus {values[0][1]})",
            }
        )
    return values[0][0]


def read_relations():
    """Klient-MA-Paare werden zu Auftrag-MA-Paaren; die Nummern bleiben gleich."""
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb["Relation Klient-MA"]
    out, seen = [], set()
    for r in range(2, ws.max_row + 1):
        mandate = norm(ws.cell(row=r, column=1).value)
        employee = norm(ws.cell(row=r, column=2).value)
        if not mandate or not employee:
            continue
        key = (mandate, employee)
        if key in seen:
            continue
        seen.add(key)
        out.append({"mandate_id": mandate, "employee_id": employee})
    return sorted(out, key=lambda d: (d["mandate_id"], d["employee_id"]))


def main():
    rows = read_clients()
    groups, conflicts = build_person_groups(rows)

    persons, mandates, cares = [], [], []
    person_of_client = {}

    for key in sorted(groups):
        members = sorted(groups[key], key=lambda r: r["client_id"])
        person_id = "K" + str(key).lstrip("C")
        person = {"person_id": person_id}
        for field in PERSON_FIELDS:
            person[field] = pick(members, field, conflicts, person_id)
        person["notes"] = None
        persons.append(person)
        for row in members:
            person_of_client[row["client_id"]] = person_id

    for row in sorted(rows, key=lambda r: r["client_id"]):
        cid = row["client_id"]
        person_id = person_of_client[cid]
        mandates.append(
            {
                "mandate_id": cid,
                "short_code": row.get("short_code"),
                "service_type_id": row.get("service_type_id"),
                "service_requester_id": row.get("service_requester_id"),
                "payer_id": row.get("payer_id"),
                "tenant_id": row.get("tenant_id"),
                "sr_ap_gender": row.get("sr_ap_gender"),
                "sr_ap_first_name": row.get("sr_ap_first_name"),
                "sr_ap_last_name": row.get("sr_ap_last_name"),
                "application_number": row.get("application_number"),
                "start_date": iso(row.get("start_date")),
                "end_date": iso(row.get("end_date")),
                "allowed_travel_time": row.get("allowed_travel_time"),
                "allowed_direct_effort": row.get("allowed_direct_effort"),
                "allowed_indirect_effort": row.get("allowed_indirect_effort"),
                "allocation": row.get("allocation"),
                "billing_person_id": person_id,
                "predecessor_mandate_id": None,
                "notes": row.get("notes"),
            }
        )

        has_leave_data = any(row.get(f) is not None for f in LEAVE_MARKERS)
        care = {
            "mandate_id": cid,
            "person_id": person_id,
            "start_date": iso(row.get("start_date")),
            "end_date": iso(row.get("end_date")) if has_leave_data else None,
        }
        for field in CARE_FIELDS:
            care[field] = row.get(field)
        cares.append(care)

    relations = read_relations()
    merged = {
        person_id: sorted(cid for cid, p in person_of_client.items() if p == person_id)
        for person_id in {p["person_id"] for p in persons}
        if sum(1 for p in person_of_client.values() if p == person_id) > 1
    }

    result = {
        "quelle": str(SRC),
        "altzeilen": len(rows),
        "persons": persons,
        "mandates": mandates,
        "cares": cares,
        "relations": relations,
        "conflicts": conflicts,
        "stats": {
            "rows": len(rows),
            "persons": len(persons),
            "mandates": len(mandates),
            "cares": len(cares),
            "relations": len(relations),
            "with_leave": sum(1 for c in cares if c["end_date"]),
            "merged": merged,
        },
        "zusammengelegt": merged,
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Altzeilen        : {len(rows)}")
    print(f"Kinder           : {len(persons)}")
    print(f"Aufträge         : {len(mandates)}")
    print(f"Betreuungen      : {len(cares)}")
    print(f"mit Austritt     : {sum(1 for c in cares if c['end_date'])}")
    print(f"MA-Zuordnungen   : {len(relations)}")
    print()
    print("Zusammengelegt:")
    for pid, cids in sorted(result["zusammengelegt"].items()):
        print(f"  {pid} <- {', '.join(cids)}")
    print()
    print("Konflikte:")
    for c in conflicts:
        print(" ", json.dumps(c, ensure_ascii=False))


if __name__ == "__main__":
    main()
