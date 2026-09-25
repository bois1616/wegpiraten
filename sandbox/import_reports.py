"""Füllt die Berichtstabelle aus »2026 Klientenübersicht.xlsx« und schreibt die Klärungsliste.

Rot = Bericht, orange = Zwischenbericht (zwei Berichtsformen, Stephan 25.09.2026). Rote Zellen
tragen kein Datum, nur den Monat: es gilt die Monatsmitte (15.). Orange Zellen tragen teils ein
Datum; es gilt, wenn es zum Monat der Spalte passt. Blau (Abschluss + Bericht) ist der
Abschlussbericht (dritte Form, Stephan 25.09.2026); seine Zelle trägt oft ein Datum mit falschem
Jahr, dann gilt »Bewilligung bis« des Auftrags, wenn es in diesen Monat fällt.

Hauptquelle sind die Blätter der Mitarbeitenden; die Übersicht wird dagegen geprüft, nicht
umgekehrt (sie ist nicht zwingend aktuell). Ergebnis: reports_import.json für build.py und
klaerung_berichte_2026-09-25.md.
"""

import collections
import difflib
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import openpyxl

SANDBOX = Path(__file__).parent
SRC = SANDBOX / "2026 Klientenübersicht.xlsx"
WORKBOOK = SANDBOX / "wegpiraten_datenbank_neu.xlsx"
DATA = SANDBOX / "migration_v2_neu.json"
OUT = SANDBOX / "reports_import.json"
NOTE = SANDBOX / "klaerung_berichte_2026-09-25.md"

TODAY = date.today()
MONTHS = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sept", "Okt", "Nov", "Dez"]
FORM = {"FFFF0000": "Bericht", "FFFFC000": "Zwischenbericht", "FF00B0F0": "Abschlussbericht"}
EMPLOYEE_OF = {"christian": "M003", "johann": "M006", "lotti": "M007", "lotty": "M007",
               "marc": "M008", "isabelle": "M005", "hannah": "M011", "viky": "M001",
               "vicky": "M001", "kloos": "M005"}
# Kürzel der Übersicht (Spalte »SPF/BBT«) gegen den code der Leistungsart
SERVICE_PREFIX = {"SPF": ("SPF",), "UWB": ("UWB",), "JC": ("Jugendcoaching",),
                  "ABKLÄ": ("Abklärung",), "DAF L": ("DAF L",)}


def norm(text):
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[-/]", " ", plain)).strip().lower()


def full_name(first, last):
    return norm(f"{first} {last}").replace(" ", "")


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


def fill_key(cell):
    fill = cell.fill
    if fill is None or fill.fill_type is None or fill.fgColor.type != "rgb":
        return None
    return fill.fgColor.rgb


def parse_sheet(ws):
    """Zeilen mit Stammdaten und den farbigen Monatszellen eines Blatts."""
    header = next((r for r in range(1, 12) if ws.cell(r, 2).value == "Klient*in"), None)
    if header is None:
        return []
    month_cols = []
    for c in range(1, ws.max_column + 1):
        if ws.cell(header, c).value == "Jan":
            month_cols.append(c)
    service_col = next(c for c in range(9, 16) if "SPF" in str(ws.cell(header, c).value or ""))
    rows = []
    for r in range(header + 2, ws.max_row + 1):
        last, first, begin = ws.cell(r, 3).value, ws.cell(r, 2).value, as_date(ws.cell(r, 7).value)
        if not (last and first and begin) or last == "Nachname":
            continue
        marks = []
        for block, start in enumerate(month_cols):
            year = 2026 + block
            for month in range(12):
                cell = ws.cell(r, start + month)
                key = fill_key(cell)
                if key in FORM:
                    marks.append({"year": year, "month": month + 1, "form": FORM[key],
                                  "value": as_date(cell.value)})
        rows.append({
            "sheet": ws.title, "row": r, "first": str(first).strip(), "last": str(last).strip(),
            "requester": str(ws.cell(r, 4).value or "").strip(), "begin": begin,
            "end": as_date(ws.cell(r, 8).value), "who": str(ws.cell(r, 9).value or "").strip(),
            "service": str(ws.cell(r, service_col).value or "").strip(), "marks": marks,
        })
    return rows


def load_master():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    code = {r[0]: r[1] for r in wb["Leistungstypen"].iter_rows(min_row=1, values_only=True) if r[0]}
    requester = {r[1]: str(r[2]).strip() for r in wb["Leistungsbesteller"].iter_rows(
        min_row=1, values_only=True) if r[1] and r[2]}
    persons = {p["person_id"]: p for p in data["persons"]}
    care_persons = collections.defaultdict(set)
    for c in data["cares"]:
        care_persons[c["person_id"]].add(c["mandate_id"])
    staff = collections.defaultdict(set)
    for r in data["relations"]:
        staff[r["mandate_id"]].add(r["employee_id"])
    return data, code, requester, persons, care_persons, staff


def candidates(row, data, code, persons, care_persons):
    """Aufträge, die zu Name und Leistungsart einer Zeile passen."""
    hits = [pid for pid, p in persons.items()
            if norm(p["last_name"]) == norm(row["last"])
            and norm(p["first_name"]).split(" ")[0] == norm(row["first"]).split(" ")[0]]
    if not hits:
        # Tippfehler und Namensteile (Keklig/Keklik, Beuter/Beutter, Derosen/De Rosen)
        wanted_name = full_name(row["first"], row["last"])
        scored = [(difflib.SequenceMatcher(None, wanted_name, full_name(p["first_name"], p["last_name"])).ratio(), pid)
                  for pid, p in persons.items()]
        best = max(scored)
        hits = [best[1]] if best[0] >= 0.8 else []
    mandates = {m["mandate_id"]: m for m in data["mandates"]}
    found = [mandates[mid] for pid in hits for mid in care_persons[pid]]
    wanted = SERVICE_PREFIX.get(row["service"].upper())
    if wanted:
        narrowed = [m for m in found if any(code[m["service_type_id"]].startswith(w) for w in wanted)]
        found = narrowed or found
    return sorted(found, key=lambda m: m["start_date"])


def pick_mandate(cands, when):
    """Der Auftrag, dessen Bewilligung das Datum umfasst; sonst der zeitlich nächste."""
    day = when.isoformat()
    for m in cands:
        if m["start_date"] <= day <= (m["end_date"] or "9999-12-31"):
            return m, True
    def distance(m):
        edge = m["start_date"] if day < m["start_date"] else m["end_date"]
        return abs((date.fromisoformat(edge) - when).days)
    return min(cands, key=distance), False


def mark_date(mark):
    """Fälligkeit einer Markierung: das Datum der Zelle, wenn es zum Monat passt, sonst 15."""
    value = mark["value"]
    if value and (value.year, value.month) == (mark["year"], mark["month"]):
        return value, False
    return date(mark["year"], mark["month"], 15), bool(value)


def main():
    wb = openpyxl.load_workbook(SRC)
    overview = parse_sheet(wb["Übersicht"])
    employee_rows = [r for name in wb.sheetnames[1:] for r in parse_sheet(wb[name])]
    data, code, requester, persons, care_persons, staff = load_master()

    unmatched, reports, diffs = [], {}, collections.defaultdict(list)
    for row in employee_rows:
        cands = candidates(row, data, code, persons, care_persons)
        if not cands:
            unmatched.append(row)
            continue
        row["cands"] = cands
        for mark in row["marks"]:
            due, odd_date = mark_date(mark)
            mandate, inside = pick_mandate(cands, due)
            if mark["form"] == "Abschlussbericht" and mandate["end_date"]:
                end = date.fromisoformat(mandate["end_date"])
                if (end.year, end.month) == (mark["year"], mark["month"]):
                    due, odd_date = end, False
            key = (mandate["mandate_id"], mark["form"], mark["year"], mark["month"])
            entry = reports.setdefault(key, {
                "mandate_id": mandate["mandate_id"], "report_form": mark["form"], "due_date": due,
                "sources": [], "outside": not inside, "odd_date": odd_date,
                "exact": due != date(mark["year"], mark["month"], 15)})
            entry["sources"].append(f'{row["sheet"]}:{row["row"]}')
            if due != entry["due_date"]:
                diffs["Datum abweichend zwischen Mitarbeiterblättern"].append(
                    f'{row["last"]} {mark["form"]} {mark["month"]:02d}/{mark["year"]}')

    # Abgleich Übersicht ↔ Mitarbeiterblätter
    def signature(row):
        return (norm(row["last"]), norm(row["first"]).split(" ")[0], row["begin"],
                tuple(sorted((m["year"], m["month"], m["form"]) for m in row["marks"])))
    def identity(row):
        return (norm(row["last"]), norm(row["first"]).split(" ")[0], row["begin"], row["service"])
    over_by_id = collections.defaultdict(list)
    for row in overview:
        over_by_id[identity(row)].append(row)
    for row in employee_rows:
        peers = over_by_id.get(identity(row))
        label = f'{row["last"]}, {row["first"]} ({row["sheet"]} Z.{row["row"]})'
        if not peers:
            diffs["Zeile fehlt in der Übersicht"].append(label)
            continue
        if not any(signature(p) == signature(row) for p in peers):
            mine = {(m["year"], m["month"], m["form"]) for m in row["marks"]}
            theirs = set().union(*({(m["year"], m["month"], m["form"]) for m in p["marks"]}
                                   for p in peers))
            plus, minus = sorted(mine - theirs), sorted(theirs - mine)
            fields = [f for f, a, b in (("Ende", row["end"], peers[0]["end"]),
                                        ("Leistungsbesteller", row["requester"], peers[0]["requester"]))
                      if a != b]
            bits = []
            if plus: bits.append("nur im Mitarbeiterblatt: " + ", ".join(f"{m:02d}/{y} {f}" for y, m, f in plus))
            if minus: bits.append("nur in der Übersicht: " + ", ".join(f"{m:02d}/{y} {f}" for y, m, f in minus))
            if fields: bits.append("anderer Wert: " + ", ".join(fields))
            diffs["Markierungen oder Stammdaten weichen ab"].append(f"{label}: " + "; ".join(bits))
    employee_ids = {(norm(r["last"]), norm(r["first"]).split(" ")[0], r["begin"], r["service"])
                    for r in employee_rows}
    for row in overview:
        if identity(row) not in employee_ids:
            diffs["Zeile fehlt im Mitarbeiterblatt"].append(
                f'{row["last"]}, {row["first"]} (Übersicht Z.{row["row"]}, Wer: {row["who"]})')

    # Abgleich mit den Aufträgen der Datenbank
    for row in employee_rows:
        cands = row.get("cands")
        if not cands:
            continue
        label = f'{row["last"]}, {row["first"]} ({row["sheet"]} Z.{row["row"]})'
        ends = {m["end_date"] for m in cands}
        starts = {m["start_date"] for m in cands}
        if row["end"] and row["end"].isoformat() not in ends:
            diffs["Ende weicht von den Aufträgen ab"].append(
                f'{label}: Blatt {row["end"]:%d.%m.%Y}, Aufträge {", ".join(sorted(e or "offen" for e in ends))}')
        if row["begin"].isoformat() not in starts:
            diffs["Beginn weicht von den Aufträgen ab"].append(
                f'{label}: Blatt {row["begin"]:%d.%m.%Y}, Aufträge {", ".join(sorted(starts))}')
        names = {requester.get(m["service_requester_id"]) for m in cands}
        if row["requester"] not in names:
            diffs["Leistungsbesteller weicht ab"].append(
                f'{label}: Blatt »{row["requester"]}«, Aufträge {sorted(n for n in names if n)}')
    # Betreuung je Kind über alle Blätter: wer trägt es in seinem Blatt, wer steht in der Zuordnung
    groups = collections.defaultdict(lambda: {"rows": [], "sheet_staff": set(), "assigned": set()})
    for row in employee_rows:
        if not row.get("cands"):
            continue
        g = groups[(row["cands"][0]["mandate_id"], norm(row["last"]))]
        g["rows"].append(row)
        g["sheet_staff"] |= {EMPLOYEE_OF.get(t) for t in re.split(r"[- ]+", row["who"].lower()) if t}
        g["sheet_staff"].add(EMPLOYEE_OF.get(row["sheet"].lower()))
        g["assigned"] |= set().union(*(staff[m["mandate_id"]] for m in row["cands"]))
    seen_groups = set()
    for (_, _), g in groups.items():
        row = g["rows"][0]
        label = f'{row["last"]}, {row["first"]}'
        key = (label, tuple(sorted(g["sheet_staff"] - {None})), tuple(sorted(g["assigned"])))
        if key in seen_groups:
            continue
        seen_groups.add(key)
        only_sheet = g["sheet_staff"] - g["assigned"] - {None}
        only_table = g["assigned"] - g["sheet_staff"]
        if only_sheet:
            diffs["Im Blatt betreut, aber nicht in Zuordnung MA"].append(
                f'{label}: {", ".join(sorted(only_sheet))} (Zuordnung: {", ".join(sorted(g["assigned"])) or "keine"})')
        if only_table:
            diffs["In Zuordnung MA, aber in keinem Blatt"].append(
                f'{label}: {", ".join(sorted(only_table))} (Blätter: {", ".join(sorted(g["sheet_staff"] - {None}))})')

    ordered = sorted(reports.values(), key=lambda e: (e["due_date"], e["mandate_id"], e["report_form"]))
    out = []
    for i, e in enumerate(ordered, start=1):
        notes = []
        if not e["exact"]:
            notes.append("Monatsmitte angenommen, in der Übersicht steht nur der Monat.")
        if e["odd_date"]:
            notes.append("Datum in der Zelle passt nicht zum Monat der Spalte, Monatsmitte genommen.")
        if e["outside"]:
            notes.append("Fälligkeit liegt ausserhalb der Bewilligung; dem zeitlich nächsten Auftrag zugeordnet.")
        out.append({
            "report_id": f"R{i:03d}", "mandate_choice": e["mandate_id"],
            "report_form": e["report_form"], "due_date": e["due_date"].isoformat(),
            "status": "offen" if e["due_date"] >= TODAY else None, "completed_date": None,
            "notes": " ".join(notes) or None})
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    past = sum(1 for r in out if r["status"] is None)
    per_form = collections.Counter(r["report_form"] for r in out)
    lines = [
        "# Klärung: Berichte aus der Klientenübersicht (Stand 25.09.2026)", "",
        f"Quelle `2026 Klientenübersicht.xlsx`: Mitarbeiterblätter als Hauptquelle, die Übersicht "
        f"dagegen abgeglichen. Rot = Bericht, orange = Zwischenbericht (zwei Berichtsformen); blau "
        f"(Abschluss + Bericht) als Abschlussbericht.", "",
        "## Ergebnis", "",
        f"- {len(out)} Berichte angelegt ({per_form['Bericht']}× Bericht, "
        f"{per_form['Zwischenbericht']}× Zwischenbericht, {per_form['Abschlussbericht']}× Abschlussbericht), Fälligkeit je Auftrag.",
        f"- Status: {len(out) - past} mit Fälligkeit ab heute auf `offen`; **{past} liegen in der "
        f"Vergangenheit und haben keinen Status**, weil die Übersicht keinen Erledigt-Vermerk kennt.",
        f"- {sum(1 for e in ordered if not e['exact'])} Fälligkeiten sind Monatsmitte (rote Zellen "
        f"ohne Datum), {sum(1 for e in ordered if e['exact'])} tragen ein Datum aus der Zelle.",
        f"- Nicht zugeordnet ({len(unmatched)} Zeilen): "
        + (", ".join(f'{r["last"]} ({r["sheet"]})' for r in unmatched) or "keine") + ".", "",
    ]
    lines += ["## Abweichungen", ""]
    for title, items in diffs.items():
        lines += [f"### {title} ({len(items)})", ""] + [f"- {i}" for i in sorted(set(items))] + [""]
    lines += ["## Offene Fragen", "",
              "- Bericht und Zwischenbericht: worin unterscheiden sie sich (Inhalt, Empfänger, Frist)?",
              "- Abschlussbericht (blau): gilt für jeden Auftrag, auch für Vorgänger in einer Kette?",
              "- Gibt es leistungsbestellerbezogene Kadenzen? Bis zur Klärung bleibt der Rhythmus am Auftrag (kein Pflichtfeld).",
              "- Erledigt-Stand der vergangenen Berichte: woher nehmen wir ihn?"]
    NOTE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(out)} Berichte, {past} ohne Status, {len(unmatched)} nicht zugeordnet")
    for title, items in diffs.items():
        print(f"  {title}: {len(set(items))}")


if __name__ == "__main__":
    main()
