"""Bereitet migration.json auf das überarbeitete Modell auf: Nummernkreise, Kurzzeichen,
Ansprechpersonen als eigene Dimension, Abrechnungskennzeichen an der Betreuung.

Getrennt von build.py, weil hier fachliche Entscheidungen stecken und dort nur Formatierung.
"""

import collections
import json
from datetime import date, timedelta
from pathlib import Path

SANDBOX = Path(__file__).parent
SRC = SANDBOX / "migration_neu.json"
DST = SANDBOX / "migration_v2_neu.json"


def short_code_base(person):
    """Kurzzeichen-Rohform: zwei Buchstaben Vorname, zwei Buchstaben Nachname."""
    first = (person["first_name"] or "").strip()
    last = (person["last_name"] or "").strip()
    return f"{first[:2]}{last[:2]}"


def build_short_codes(persons, mandates):
    """Bestehendes Kurzzeichen je Kind übernehmen, Kollisionen mit einer Ziffer auflösen."""
    by_person = collections.defaultdict(set)
    for m in mandates:
        if m["short_code"]:
            by_person[m["billing_person_id"]].add(m["short_code"])

    codes, taken, notes = {}, {}, {}
    for p in sorted(persons, key=lambda x: x["person_id"]):
        pid = p["person_id"]
        existing = by_person.get(pid, set())
        wanted = existing.pop() if len(existing) == 1 else short_code_base(p)
        code, suffix, blocked = wanted, 1, []
        while code in taken:
            blocked.append(f"{code} → {'C' + taken[code][1:]}")
            suffix += 1
            code = f"{wanted}{suffix}"
        if blocked:
            notes[pid] = (
                f"Kurzzeichen {wanted} war schon vergeben ({', '.join(blocked)}), "
                f"deshalb {code}."
            )
        taken[code] = pid
        codes[pid] = code
    return codes, notes


def build_contacts(mandates):
    """Ansprechpersonen aus den Auftragszeilen ziehen; Widersprüche notieren, nicht glätten."""
    seen = collections.defaultdict(collections.Counter)
    for m in mandates:
        first = (m["sr_ap_first_name"] or "").strip()
        last = (m["sr_ap_last_name"] or "").strip()
        if not (first or last):
            continue
        seen[(m["service_requester_id"], first, last)][(m["sr_ap_gender"] or "").strip()] += 1

    by_requester = collections.defaultdict(set)
    for requester, first, last in seen:
        by_requester[requester].add((first, last))

    contacts, index = [], {}
    for number, key in enumerate(sorted(seen, key=lambda k: (k[0], k[2], k[1])), start=1):
        requester, first, last = key
        genders = seen[key]
        gender = genders.most_common(1)[0][0]
        remarks = []
        if len(genders) > 1:
            spread = ", ".join(f"{n}× {g or 'ohne'}" for g, n in genders.most_common())
            remarks.append(f"Anrede in den Altdaten uneinheitlich ({spread}) – bitte prüfen.")
        if (last, first) in by_requester[requester]:
            remarks.append(
                f"Beim selben Besteller steht auch »{last}, {first}« – "
                "vermutlich Vor- und Nachname vertauscht."
            )
        cid = f"AP{number:03d}"
        contacts.append({
            "contact_person_id": cid,
            "service_requester_id": requester,
            "gender": gender or None,
            "first_name": first or None,
            "last_name": last or None,
            "notes": " ".join(remarks) or None,
        })
        index[key] = cid
    return contacts, index


# Klärungen von Wegpiraten, 05.09.2026. Die Altdaten widersprachen sich; hier steht,
# wie entschieden wurde, damit ein erneuter Lauf nicht wieder die Mehrheit rät.
# Schlüssel ist (Besteller, Vorname, Nachname), nicht die Nummer: die Nummern hängen an
# der Sortierung und verschieben sich, sobald eine Person dazukommt oder wegfällt.
CONTACT_RULINGS = {
    ("SR011", "David", "Dimitrijevic"): {
        "gender": "Herr",
        "notes": "Anrede geklärt 05.09.2026: Herr. In den Altdaten 7× Frau, "
                 "3× Herr. Die bereits verschickten Anreden sind damit nicht "
                 "rückwirkend korrigiert – das bleibt Handarbeit."},
}
# Vertauschte Namen: Schlüssel der falschen Schreibweise -> der richtigen. Seit der
# Datei vom 24.09.2026 ist Wilhelmi im Quellblatt korrigiert; der Eintrag bleibt für
# den Fall, dass ein alter Stand erneut eingelesen wird.
CONTACT_MERGES = {("SR013", "Wilhelmi", "Regula"): ("SR013", "Regula", "Wilhelmi")}


def apply_contact_rulings(contacts, mandates):
    """Widersprüche aus den Altdaten so auflösen, wie Wegpiraten entschieden hat."""
    key_of = {c["contact_person_id"]:
              (c["service_requester_id"], c["first_name"] or "", c["last_name"] or "")
              for c in contacts}
    id_of = {k: v for v, k in key_of.items()}
    for c in contacts:
        c.update(CONTACT_RULINGS.get(key_of[c["contact_person_id"]], {}))
    for wrong, right in CONTACT_MERGES.items():
        if wrong in id_of and right in id_of:
            for m in mandates:
                if m["contact_person_id"] == id_of[wrong]:
                    m["contact_person_id"] = id_of[right]
            contacts[:] = [c for c in contacts if c["contact_person_id"] != id_of[wrong]]


NUMBERS = SANDBOX / "mandate_numbers.json"


def build_mandate_numbers(mandates):
    """Auftragsnummer A + Startjahr (zweistellig) + Jahreszähler (dreistellig).

    Einmal vergebene Nummern ändern sich nie (Stephan, 25.09.2026), auch wenn später ein
    Auftrag mit früherem Startdatum dazukommt: die Zuordnung alte Klientennummer → Auftragsnummer
    steht in mandate_numbers.json. Neue Aufträge bekommen den nächsten freien Zählerstand ihres
    Startjahrs, bei gleichem Datum ordnet die bisherige Klientennummer.
    """
    frozen = json.loads(NUMBERS.read_text(encoding="utf-8")) if NUMBERS.exists() else {}
    counter = collections.Counter()
    for number in frozen.values():
        counter[number[1:3]] = max(counter[number[1:3]], int(number[3:]))
    fresh = [m for m in mandates if m["mandate_id"] not in frozen]
    for m in sorted(fresh, key=lambda x: (x["start_date"], x["mandate_id"])):
        year = m["start_date"][2:4]
        counter[year] += 1
        frozen[m["mandate_id"]] = f"A{year}{counter[year]:03d}"
    NUMBERS.write_text(json.dumps(frozen, indent=1, sort_keys=True), encoding="utf-8")
    return {m["mandate_id"]: frozen[m["mandate_id"]] for m in mandates}


# Verlängerungen, die das Altmodell durch Überschreiben verschluckt hat; von Wegpiraten am
# 25.09.2026 bestätigt. Die Werte des Vorgängers stammen aus dem Snapshot vom 02.09.2026
# (Archiv/wegpiraten_datenbank_vor_umbau.xlsx), alles andere gilt für Vorgänger und
# Nachfolger gleich. C1011/C1015 (neue Antragsnummer, Ende unverändert) fehlen absichtlich:
# Wann der alte Auftrag endete, steht in keiner Datei. C1036 ist eine Nummernkorrektur.
FOLLOW_UPS = {
    "C1024": {"old_end": "2026-09-30"},
    "C1068": {"old_end": "2026-08-31", "old_requester": "SR006"},
    "C1082": {"old_end": "2026-09-30"},
}


def apply_follow_ups(data):
    """Aus dem überschriebenen Auftrag Vorgänger und Nachfolger machen.

    Die Zeile der Altdatei bleibt der Vorgänger mit dem Snapshot-Ende. Der Nachfolger beginnt
    am Tag danach, übernimmt Kontingent, Antragsnummer und Mitarbeitende und trägt die
    heutigen Werte. Die Betreuung wandert mit dem unveränderten Eintritt (Invariante 21).
    """
    mandates, cares, relations = data["mandates"], data["cares"], data["relations"]
    by_id = {m["mandate_id"]: m for m in mandates}
    for cid, spec in FOLLOW_UPS.items():
        old = by_id[cid]
        new_id = f"{cid}+"
        new = dict(old)
        new["mandate_id"] = new_id
        new["start_date"] = (date.fromisoformat(spec["old_end"]) + timedelta(days=1)).isoformat()
        new["predecessor_mandate_id"] = cid
        new["notes"] = " ".join(x for x in (
            old["notes"], f"Folgeauftrag zu Klient {cid}, Verlängerung von Wegpiraten "
            "bestätigt (25.09.2026); Kontingent und Antragsnummer vom Vorgänger übernommen.")
            if x)

        old["end_date"] = spec["old_end"]
        if "old_requester" in spec:
            old["service_requester_id"] = spec["old_requester"]
        old["notes"] = " ".join(x for x in (
            old["notes"], "Ende aus dem Stand vom 02.09.2026, danach Folgeauftrag.") if x)

        for care in [c for c in cares if c["mandate_id"] == cid]:
            follow = dict(care)
            follow["mandate_id"] = new_id
            cares.append(follow)
            for field in ("end_date", "is_leaving_reason_planned", "leaving_reason",
                          "custom_leaving_reason", "after_leave_situation",
                          "custom_after_leave_situation", "remarks"):
                care[field] = None
        for r in [r for r in relations if r["mandate_id"] == cid]:
            relations.append({**r, "mandate_id": new_id})
        mandates.append(new)
    data["stats"]["mandates"] = len(mandates)
    data["stats"]["cares"] = len(cares)
    data["stats"]["relations"] = len(relations)


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    apply_follow_ups(data)
    persons, mandates = data["persons"], data["mandates"]
    cares, relations = data["cares"], data["relations"]

    person_map = {p["person_id"]: "C" + p["person_id"][1:] for p in persons}
    mandate_map = build_mandate_numbers(mandates)

    codes, code_notes = build_short_codes(persons, mandates)
    contacts, contact_index = build_contacts(mandates)

    # Keine Familien aus den Altdaten: Geschwister sind darin nicht erkennbar, und
    # solange ein Kind allein steht, ist es selbst das Abrechnungskind. Das Blatt
    # startet leer und füllt sich erst, wenn wirklich Geschwister auftauchen.
    families = []

    for p in persons:
        old = p["person_id"]
        p["person_id"] = person_map[old]
        p["family_id"] = None
        p["short_code"] = codes[old]
        note = code_notes.get(old)
        if note:
            p["notes"] = " ".join(x for x in (p.get("notes"), note) if x)

    for m in mandates:
        key = (
            m["service_requester_id"],
            (m["sr_ap_first_name"] or "").strip(),
            (m["sr_ap_last_name"] or "").strip(),
        )
        m["contact_person_id"] = contact_index.get(key)
        old_id = m["mandate_id"]
        m["old_client_id"] = old_id.rstrip("+")
        m["mandate_id"] = mandate_map[old_id]
        m["notes"] = " ".join(
            x for x in (m["notes"], f"Bisherige Klientennummer {m['old_client_id']}.") if x)
        # Die Arbeitsmappe setzt den Vorgänger über die Auswahlspalte; die Nummer allein
        # wird von der Extraktionsformel ebenso gelesen wie die Auswahl mit Klartext.
        m["predecessor_choice"] = mandate_map.get(m.pop("predecessor_mandate_id"))
        for gone in ("short_code", "billing_person_id", "sr_ap_gender",
                     "sr_ap_first_name", "sr_ap_last_name"):
            m.pop(gone, None)

    for c in cares:
        c["mandate_id"] = mandate_map[c["mandate_id"]]
        c["person_id"] = person_map[c["person_id"]]

    for r in relations:
        r["old_client_id"] = r["mandate_id"].rstrip("+")
        r["mandate_id"] = mandate_map[r["mandate_id"]]

    apply_contact_rulings(contacts, mandates)

    data["contacts"] = contacts
    data["families"] = families
    data["stats"]["families"] = len(families)
    data["stats"]["contacts"] = len(contacts)
    data["stats"]["contact_conflicts"] = sum(1 for c in contacts if c["notes"])
    data["stats"]["short_code_conflicts"] = len(code_notes)
    data["stats"]["merged"] = {
        person_map[pid]: [mandate_map[c] for c in cids]
        for pid, cids in data["stats"]["merged"].items()
    }

    DST.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschrieben: {DST}")
    print(f"  Kinder {len(persons)}, Aufträge {len(mandates)}, Betreuungen {len(cares)}, "
          f"Ansprechpersonen {len(contacts)}, Familien {len(families)}")
    print(f"  Kurzzeichen-Kollisionen aufgelöst: {code_notes}")
    print(f"  Ansprechpersonen mit Widerspruch: {data['stats']['contact_conflicts']}")
    for c in contacts:
        if c["notes"]:
            print(f"    {c['contact_person_id']} {c['service_requester_id']} "
                  f"{c['first_name']} {c['last_name']}: {c['notes']}")


if __name__ == "__main__":
    main()
