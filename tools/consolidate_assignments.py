"""Überführt die vorbereitete Kundenmappe auf eine gemeinsame Zuordnung MA."""

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

from data_imports.workbook_assignments import patch_assignment_formulas, patch_report_formulas
from data_imports.workbook_package import NS, WorkbookPackage, cell_map, serialize, set_cell, tag
from data_imports.workbook_upgrade import _extend_columns, _findings, _inputs
from shared_modules.config import Config


def consolidate(config: Config, source: Path, destination: Path) -> None:
    """Erhält Kundeneingaben, Registerfarben und Reihenfolge aller verbleibenden Blätter."""
    if source.resolve() == destination.resolve():
        raise ValueError("Zuerst eine separate Ausgabekopie vorbereiten.")
    package = WorkbookPackage(source)
    inputs = _inputs(package, config)
    order = list(package.sheets)
    colors = {s: package.read_sheet(s).find("m:sheetPr/m:tabColor", NS) for s in order}
    if "Zuständigkeitsverlauf" in package.sheets:
        history = cell_map(package.read_sheet("Zuständigkeitsverlauf"))
        for ref, cell in history.items():
            import re

            if int(re.sub(r"\D", "", ref)) >= 4 and re.sub(r"\d", "", ref) in "ABCDEFG" and package.value(cell):
                raise ValueError("Der separate Verlauf enthält Eingaben; diese zuerst explizit überführen.")
        package.remove_sheet("Zuständigkeitsverlauf")
    _extend_columns(package, "Zuordnung MA", "relation_mandate_emp", ["valid_from", "valid_to"])
    root = package.read_sheet("Zuordnung MA")
    date_style = cell_map(root)["E4"].get("s", "25")
    for row in range(4, 2001):
        for column in ("P", "Q"):
            cell = set_cell(root, f"{column}{row}", "", date_style)
            cell.set("s", date_style)
    for col in root.findall("m:cols/m:col", NS):
        if col.get("min") in ("16", "17"):
            col.set("style", date_style)
    package.save_sheet("Zuordnung MA", root)
    patch_assignment_formulas(package)
    patch_report_formulas(package)
    root = package.read_sheet("Prüfkatalog")
    cells = cell_map(root)
    for row in range(4, 63):
        if package.value(cells.get(f"D{row}")) == "Auftrag ohne primäre Betreuungsperson":
            set_cell(
                root,
                f"F{row}",
                "SUMPRODUCT((Aufträge!$A$4:$A$1999<>\"\")*(COUNTIF('Zuordnung MA'!$J$4:$J$2000,Aufträge!$A$4:$A$1999)=0))",
                "26",
                True,
            )
        if package.value(cells.get(f"D{row}")) == "Mitarbeiterzuordnung auf einen ausgelaufenen Auftrag":
            set_cell(root, f"D{row}", "Beendeter Auftrag oder Zuordnungszeitraum")
        if package.value(cells.get(f"C{row}")) == "Zuständigkeitsverlauf":
            set_cell(root, f"C{row}", "Zuordnung MA")
            set_cell(root, f"D{row}", "Zuordnungszeiträume prüfen")
            formula = cells[f"F{row}"].find(tag("f"))
            if formula is not None:
                formula.text = (formula.text or "").replace("assignment_history[", "relation_mandate_emp[")
    package.save_sheet("Prüfkatalog", root)
    _findings(package)
    root = package.read_sheet("Anleitung")
    styles = ET.fromstring(package.parts["xl/styles.xml"])
    formats = styles.find(tag("cellXfs"))
    assert formats is not None
    wrap_style = deepcopy(formats[26])
    wrap_style.set("applyAlignment", "1")
    alignment = wrap_style.find(tag("alignment"))
    if alignment is None:
        # CT_Xf verlangt alignment vor protection und extLst.
        alignment = ET.Element(tag("alignment"))
        wrap_style.insert(0, alignment)
    alignment.set("wrapText", "1")
    alignment.set("vertical", "top")
    wrap_index = str(len(formats))
    formats.append(wrap_style)
    formats.set("count", str(len(formats)))
    package.parts["xl/styles.xml"] = serialize(styles, package.parts["xl/styles.xml"])
    data = root.find(tag("sheetData"))
    assert data is not None
    last = max(int(row.get("r", "0")) for row in data)
    instructions = [
        ("Hinweise zur Zuordnung MA: eine Liste für Betreuung und Berichte", ""),
        (
            "Eingabe",
            "Nur A:C sowie P:Q (Gültig ab / Gültig bis) bearbeiten. D:O enthalten Formeln: hier keine Daten hineinkopieren.",
        ),
        (
            "Wechsel",
            "Die alte Zeile mit Gültig bis beenden und eine neue Zeile für den folgenden Zeitraum anlegen. Historische Zeilen und Rollen nicht überschreiben oder löschen.",
        ),
        (
            "Datumsgrenzen",
            "Beginn und Ende gelten einschliesslich. Ende 31.07. und neuer Beginn 01.08. überschneiden sich nicht. Leerer Beginn bedeutet unbekannt/offen; leeres Ende bedeutet fortlaufend.",
        ),
        (
            "Bestehende Zeilen",
            "Ohne Datumsgrenzen gilt die bisherige Zuordnung weiter. Beim ersten Wechsel auch die alte, bisher undatierte Zeile beenden. Keine historische Zuständigkeit erfinden.",
        ),
        (
            "Primäre Zuständigkeit",
            "Für einen Bericht muss an seinem Fälligkeitstag genau eine Zuordnung mit Rolle P gelten. P-Zeiträume eines Auftrags dürfen sich nicht überschneiden; Lücken und ungültige Daten werden gemeldet.",
        ),
        (
            "Erfassungsbögen",
            "Für den Leistungsmonat zählen alle Zuordnungen, deren Zeitraum den Monat berührt. Je Auftrag/Mitarbeiter wird nur ein Bogen erzeugt, auch bei mehreren passenden Zeilen. Bei einem Wechsel im Monat können beide Mitarbeitenden einen Bogen erhalten.",
        ),
        (
            "Berichte",
            "Die Berichtszuständigkeit folgt der Fälligkeit. Das Intervall erzeugt keine Termine: jeden Bericht ausdrücklich in Berichte erfassen. Import und Reporting schreiben keine Termine zurück.",
        ),
        (
            "Kommentare",
            "Kommentare im Prüfkatalog G und Bearbeitungsnotizen in H pflegen. Prüfungen G wird automatisch angezeigt und darf nicht überschrieben werden.",
        ),
    ]
    for offset, (label, text) in enumerate(instructions, last + 2):
        set_cell(root, f"A{offset}", label, "21")
        cell = set_cell(root, f"B{offset}", text, wrap_index)
        cell.set("s", wrap_index)
        merges = root.find(tag("mergeCells"))
        if merges is None:
            # mergeCells folgt vor Druck-/Zeichnungselementen auf sheetData.
            merges = ET.Element(tag("mergeCells"))
            root.insert(list(root).index(data) + 1, merges)
        ET.SubElement(merges, tag("mergeCell"), {"ref": f"B{offset}:F{offset}" if text else f"A{offset}:F{offset}"})
        merges.set("count", str(len(merges)))
        row = next(row for row in data if row.get("r") == str(offset))
        row.set("ht", "65")
        row.set("customHeight", "1")
    package.save_sheet("Anleitung", root)
    assert _inputs(package, config) == inputs
    assert list(package.sheets) == [s for s in order if s != "Zuständigkeitsverlauf"]
    for title in package.sheets:
        color = package.read_sheet(title).find("m:sheetPr/m:tabColor", NS)
        assert (color.attrib if color is not None else {}) == (
            colors[title].attrib if colors[title] is not None else {}
        )
    assert not any(b"assignment_history[" in part for part in package.parts.values())
    package.write(destination)
    destination.with_suffix(".vereinigung.json").write_text(
        json.dumps(
            {
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "preserved_input_cells": len(inputs),
                "preserved_sheet_order_and_colors": True,
                "removed_empty_sheet": "Zuständigkeitsverlauf",
                "input_dates": "Zuordnung MA!P:Q",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    consolidate(Config(args.config), args.source, args.destination)
