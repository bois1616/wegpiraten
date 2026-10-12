"""Eine direkte Freitextspalte mit stabiler Zuordnung zur jeweiligen Prüfung."""

from copy import deepcopy
from xml.etree import ElementTree as ET

from openpyxl.utils.cell import get_column_letter, range_boundaries

from data_imports.workbook_package import NS, WorkbookPackage, cell_map, serialize, set_cell, tag


def enable_direct_check_comments(package: WorkbookPackage) -> None:
    """Kommentare in Prüfungen G; feste IDs verhindern ein Verrutschen bei Neuberechnung."""
    catalogue = package.read_sheet("Prüfkatalog")
    catalog_cells = cell_map(catalogue)
    _, table = package.table("check_catalog")
    _, top, _, bottom = range_boundaries(table.get("ref", ""))
    assert top and bottom
    identifiers = [package.value(catalog_cells.get(f"A{row}")) for row in range(top + 1, bottom + 1)]
    comments = {key: package.value(catalog_cells.get(f"G{row}")) for row, key in enumerate(identifiers, top + 1)}
    root = package.read_sheet("Prüfungen")
    cells = cell_map(root)
    for row in range(7, len(identifiers) + 7):
        cell = cells.get(f"G{row}")
        if cell is None or cell.find(tag("f")) is not None:
            continue
        identifier = package.value(cells.get(f"H{row}"))
        if identifier in comments:
            comments[identifier] = package.value(cell)
        else:
            matched = [
                key
                for source_row, key in enumerate(identifiers, top + 1)
                if package.value(catalog_cells.get(f"J{source_row}")) == str(row - 6)
            ]
            if len(matched) == 1:
                comments[matched[0]] = package.value(cell)
    styles = ET.fromstring(package.parts["xl/styles.xml"])
    formats = styles.find(tag("cellXfs"))
    assert formats is not None
    style = deepcopy(formats[25])
    style.set("numFmtId", "49")
    alignment = style.find(tag("alignment"))
    if alignment is None:
        alignment = ET.Element(tag("alignment"))
        style.insert(0, alignment)
    style.set("applyAlignment", "1")
    alignment.set("wrapText", "1")
    alignment.set("vertical", "top")
    comment_style = str(len(formats))
    formats.append(style)
    formats.set("count", str(len(formats)))
    package.parts["xl/styles.xml"] = serialize(styles, package.parts["xl/styles.xml"])
    set_cell(
        root,
        "A2",
        "Alle Prüfungen bleiben sichtbar. Anzahl 0: grau und durchgestrichen. Kommentare direkt in G eintragen; sie bleiben beim Erledigen erhalten. Ganze Liste sortieren, niemals eine einzelne Spalte.",
        "100",
    )
    set_cell(root, "H6", "Prüfung-ID", "21")
    last = len(identifiers) + 6
    for row_node in root.findall("m:sheetData/m:row", NS):
        if 7 <= int(row_node.get("r", "0")) <= last:
            row_node.attrib.pop("hidden", None)
    for row, identifier in enumerate(identifiers, 7):
        set_cell(root, f"H{row}", identifier, "27")
        for column, field in enumerate(("Art", "Blatt", "Prüfung", "Erläuterung", "Anzahl"), 1):
            expression = f"IFERROR(INDEX(check_catalog[{field}],MATCH($H{row},check_catalog[Prüfung-ID],0))"
            expression += ("" if field == "Anzahl" else '&""') + ',"")'
            set_cell(root, f"{get_column_letter(column)}{row}", expression, "27", True)
        set_cell(root, f"G{row}", comments[identifier], comment_style).set("s", comment_style)
    for row in range(top + 1, bottom + 1):
        set_cell(
            catalogue,
            f"G{row}",
            f'IFERROR(INDEX(Prüfungen!$G$7:$G${last},MATCH(A{row},Prüfungen!$H$7:$H${last},0))&"","")',
            "27",
            True,
        )
    filter_node = root.find(tag("autoFilter"))
    if filter_node is None:
        filter_node = ET.Element(tag("autoFilter"))
        data = root.find(tag("sheetData"))
        assert data is not None
        root.insert(list(root).index(data) + 1, filter_node)
    filter_node.set("ref", f"A6:H{last}")
    for child in list(filter_node):
        filter_node.remove(child)
    merges = root.find(tag("mergeCells"))
    if merges is None:
        merges = ET.Element(tag("mergeCells"))
        root.insert(list(root).index(filter_node) + 1, merges)
    if not any(node.get("ref") == "A2:G2" for node in merges):
        ET.SubElement(merges, tag("mergeCell"), {"ref": "A2:G2"})
    merges.set("count", str(len(merges)))
    description_row = root.find('m:sheetData/m:row[@r="2"]', NS)
    assert description_row is not None
    description_row.set("ht", "40")
    description_row.set("customHeight", "1")
    differentials = styles.find(tag("dxfs"))
    if differentials is None:
        differentials = ET.Element(tag("dxfs"))
        cell_styles = styles.find(tag("cellStyles"))
        assert cell_styles is not None
        styles.insert(list(styles).index(cell_styles) + 1, differentials)
    differential_index = str(len(differentials))
    differential = ET.SubElement(differentials, tag("dxf"))
    font = ET.SubElement(differential, tag("font"))
    ET.SubElement(font, tag("strike"), {"val": "1"})
    ET.SubElement(font, tag("color"), {"rgb": "FF808080"})
    differentials.set("count", str(len(differentials)))
    for rule in root.findall("m:conditionalFormatting/m:cfRule", NS):
        rule.set("priority", str(int(rule.get("priority", "1")) + 1))
    conditional = ET.Element(tag("conditionalFormatting"), {"sqref": f"A7:F{last}"})
    rule = ET.SubElement(
        conditional,
        tag("cfRule"),
        {"type": "expression", "priority": "1", "dxfId": differential_index, "stopIfTrue": "1"},
    )
    ET.SubElement(rule, tag("formula")).text = "$E7=0"
    root.insert(list(root).index(merges) + 1, conditional)
    package.parts["xl/styles.xml"] = serialize(styles, package.parts["xl/styles.xml"])
    package.save_sheet("Prüfungen", root)
    set_cell(
        catalogue,
        "A1",
        "Technischer Prüfkatalog. Kommentare ausschliesslich in Prüfungen, Spalte G, pflegen; hier werden sie nur angezeigt.",
        "100",
    )
    package.save_sheet("Prüfkatalog", catalogue)
    for sheet in package.workbook.findall("m:sheets/m:sheet", NS):
        if sheet.get("name") == "Prüfkatalog":
            sheet.set("state", "hidden")
    root = package.read_sheet("Anleitung")
    for cell in root.findall(".//m:c", NS):
        if "Kommentare im Prüfkatalog G" in package.value(cell):
            set_cell(
                root,
                cell.get("r", ""),
                "Kommentare direkt in Prüfungen, Spalte G, pflegen. Alle Prüfungen bleiben sichtbar; Anzahl 0 wird grau und durchgestrichen. Kommentare bleiben erhalten.",
                cell.get("s", "100"),
            )
    package.save_sheet("Anleitung", root)
