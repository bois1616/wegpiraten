"""Gezielte XLSX-Patches ohne Verlust unbekannter Excel-Erweiterungen."""

import re
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl.utils.cell import column_index_from_string, get_column_letter

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN}


def tag(name: str) -> str:
    """Qualifiziert ein SpreadsheetML-Element."""
    return f"{{{MAIN}}}{name}"


def serialize(root: ET.Element, original: bytes = b"") -> bytes:
    """Behält auch nur in mc:Ignorable verwendete Namespace-Deklarationen."""
    declarations = re.findall(rb'xmlns(?::([\w]+))?="([^"]+)"', original.split(b">", 2)[-2] if original else b"")
    for prefix, uri in declarations:
        if not re.fullmatch(rb"ns\d+", prefix):
            ET.register_namespace(prefix.decode(), uri.decode())
    if not declarations:
        ET.register_namespace("", MAIN)
        ET.register_namespace("r", REL)
    data = ET.tostring(root, encoding="utf-8")
    opening = data.index(b">")
    extra = b""
    for prefix, uri in declarations:
        name = b"xmlns" + (b":" + prefix if prefix else b"")
        if name + b"=" not in data[:opening]:
            extra += b" " + name + b'="' + uri + b'"'
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + data[:opening] + extra + data[opening:]


class WorkbookPackage:
    """Behält unberührte ZIP-Teile bytegleich; verändert nur benannte Bestandteile."""

    def __init__(self, source: Path) -> None:
        with ZipFile(source) as archive:
            self.parts = {name: archive.read(name) for name in archive.namelist()}
        self.shared: list[str] = []
        if "xl/sharedStrings.xml" in self.parts:
            self.shared = [
                "".join(node.itertext())
                for node in ET.fromstring(self.parts["xl/sharedStrings.xml"]).findall(tag("si"))
            ]
        self.workbook = ET.fromstring(self.parts["xl/workbook.xml"])
        self.rels = ET.fromstring(self.parts["xl/_rels/workbook.xml.rels"])
        targets = {node.get("Id"): node.get("Target", "") for node in self.rels}
        self.sheets: dict[str, str] = {}
        for sheet in self.workbook.findall("m:sheets/m:sheet", NS):
            target = targets[sheet.get(f"{{{REL}}}id")]
            self.sheets[sheet.get("name", "")] = target.lstrip("/") if target.startswith("/") else "xl/" + target

    def read_sheet(self, title: str) -> ET.Element:
        """Liest ein Blatt mit seinen nativen Erweiterungen."""
        return ET.fromstring(self.parts[self.sheets[title]])

    def save_sheet(self, title: str, root: ET.Element) -> None:
        """Serialisiert ausschliesslich das bearbeitete Blatt."""
        path = self.sheets[title]
        self.parts[path] = serialize(root, self.parts.get(path, b""))

    def value(self, cell: ET.Element | None) -> str:
        """Liest einen gespeicherten Wert ohne Formelauswertung."""
        if cell is None:
            return ""
        if cell.get("t") == "inlineStr":
            inline = cell.find(tag("is"))
            return "".join(inline.itertext()) if inline is not None else ""
        value = cell.findtext(tag("v"), "")
        return self.shared[int(value)] if cell.get("t") == "s" and value else value

    def table(self, name: str) -> tuple[str, ET.Element]:
        """Findet die native Definition einer benannten Excel-Tabelle."""
        for path, data in self.parts.items():
            if re.fullmatch(r"xl/tables/table\d+\.xml", path):
                root = ET.fromstring(data)
                if root.get("displayName") == name:
                    return path, root
        raise ValueError(f"Excel-Tabelle fehlt: {name}")

    def put_table(self, path: str, root: ET.Element) -> None:
        """Erhält die Namespace-Konventionen einer vorhandenen Tabelle."""
        self.parts[path] = serialize(root, self.parts.get(path, b""))

    def add_sheet(self, title: str, root: ET.Element, table_name: str, fields: list[str], end_row: int = 4) -> None:
        """Fügt ein leeres Eingabeblatt mit einer echten Excel-Tabelle hinzu."""
        if title in self.sheets:
            raise ValueError(f"Blatt {title} existiert bereits; keine zweite Umstellung ausführen.")
        sheet_number = max(int(re.findall(r"sheet(\d+)\.xml$", path)[0]) for path in self.sheets.values()) + 1
        table_number = (
            max(
                [
                    int(re.findall(r"table(\d+)\.xml$", path)[0])
                    for path in self.parts
                    if re.fullmatch(r"xl/tables/table\d+\.xml", path)
                ]
                + [0]
            )
            + 1
        )
        sheet_path = f"xl/worksheets/sheet{sheet_number}.xml"
        rel_id = "rId" + str(
            max([int(node.get("Id", "rId0")[3:]) for node in self.rels if node.get("Id", "").startswith("rId")] + [0])
            + 1
        )
        sheets = self.workbook.find(tag("sheets"))
        assert sheets is not None
        ET.SubElement(sheets, tag("sheet"), {"name": title, "sheetId": str(sheet_number), f"{{{REL}}}id": rel_id})
        ET.SubElement(
            self.rels,
            f"{{{PKG}}}Relationship",
            {"Id": rel_id, "Type": f"{REL}/worksheet", "Target": f"worksheets/sheet{sheet_number}.xml"},
        )
        self.sheets[title] = sheet_path
        table_parts = ET.SubElement(root, tag("tableParts"), {"count": "1"})
        ET.SubElement(table_parts, tag("tablePart"), {f"{{{REL}}}id": "rId1"})
        table_path = f"xl/tables/table{table_number}.xml"
        table = ET.Element(
            tag("table"),
            {
                "id": str(table_number),
                "name": table_name,
                "displayName": table_name,
                "ref": f"A3:{get_column_letter(len(fields))}{end_row}",
                "totalsRowShown": "0",
            },
        )
        ET.SubElement(table, tag("autoFilter"), {"ref": table.get("ref", "")})
        columns = ET.SubElement(table, tag("tableColumns"), {"count": str(len(fields))})
        for index, name in enumerate(fields, 1):
            ET.SubElement(columns, tag("tableColumn"), {"id": str(index), "name": name})
        ET.SubElement(
            table,
            tag("tableStyleInfo"),
            {
                "name": "TableStyleMedium2",
                "showFirstColumn": "0",
                "showLastColumn": "0",
                "showRowStripes": "1",
                "showColumnStripes": "0",
            },
        )
        self.put_table(table_path, table)
        self.save_sheet(title, root)
        self.parts[f"xl/worksheets/_rels/sheet{sheet_number}.xml.rels"] = (
            f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{REL}/table" Target="../tables/table{table_number}.xml"/></Relationships>'
        ).encode()
        content = ET.fromstring(self.parts["[Content_Types].xml"])
        uri = "http://schemas.openxmlformats.org/package/2006/content-types"
        for path, suffix in ((sheet_path, "worksheet"), (table_path, "table")):
            ET.SubElement(
                content,
                f"{{{uri}}}Override",
                {
                    "PartName": "/" + path,
                    "ContentType": f"application/vnd.openxmlformats-officedocument.spreadsheetml.{suffix}+xml",
                },
            )
        self.parts["[Content_Types].xml"] = serialize(content, self.parts["[Content_Types].xml"])

    def define_name(self, name: str, reference: str) -> None:
        """Neue Listen bleiben reguläre Excel-Namen ohne führendes Gleichheitszeichen."""
        names = self.workbook.find(tag("definedNames"))
        if names is None:
            names = ET.SubElement(self.workbook, tag("definedNames"))
        for node in names:
            if node.get("name") == name:
                node.text = reference
                return
        ET.SubElement(names, tag("definedName"), {"name": name}).text = reference

    def write(self, destination: Path) -> None:
        """Schreibt atomar; der ursprüngliche Dateipfad wird nicht überschrieben."""
        calculation = self.workbook.find(tag("calcPr"))
        if calculation is not None:
            calculation.set("fullCalcOnLoad", "1")
            calculation.set("forceFullCalc", "1")
        self.parts["xl/workbook.xml"] = serialize(self.workbook, self.parts["xl/workbook.xml"])
        self.parts["xl/_rels/workbook.xml.rels"] = serialize(self.rels, self.parts["xl/_rels/workbook.xml.rels"])
        if "xl/calcChain.xml" in self.parts:
            del self.parts["xl/calcChain.xml"]
            for node in list(self.rels):
                if node.get("Type", "").endswith("/calcChain"):
                    self.rels.remove(node)
            self.parts["xl/_rels/workbook.xml.rels"] = serialize(self.rels, self.parts["xl/_rels/workbook.xml.rels"])
            content = ET.fromstring(self.parts["[Content_Types].xml"])
            for node in list(content):
                if node.get("PartName") == "/xl/calcChain.xml":
                    content.remove(node)
            self.parts["[Content_Types].xml"] = serialize(content, self.parts["[Content_Types].xml"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".pending.xlsx")
        with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
            for name, data in self.parts.items():
                archive.writestr(name, data)
        temporary.replace(destination)


def cell_map(root: ET.Element) -> dict[str, ET.Element]:
    """Indiziert die tatsächlichen Zellen eines Blatts."""
    return {cell.get("r", ""): cell for cell in root.findall("m:sheetData/m:row/m:c", NS)}


@lru_cache(maxsize=24)
def _indices(root: ET.Element) -> tuple[dict[str, ET.Element], dict[str, ET.Element]]:
    """Vermeidet wiederholte lineare Suche in vorbefüllten Formelbereichen."""
    return ({row.get("r", ""): row for row in root.findall("m:sheetData/m:row", NS)}, cell_map(root))


def set_cell(root: ET.Element, reference: str, value: str, style: str = "24", formula: bool = False) -> ET.Element:
    """Setzt eine einzelne Zelle mit explizitem Text- oder Formeltyp."""
    data = root.find(tag("sheetData"))
    if data is None:
        data = ET.SubElement(root, tag("sheetData"))
    number = int(re.findall(r"\d+$", reference)[0])
    rows, cells = _indices(root)
    row = rows.get(str(number))
    if row is None:
        row = ET.Element(tag("row"), {"r": str(number)})
        index = next((i for i, existing in enumerate(data) if int(existing.get("r", "0")) > number), len(data))
        data.insert(index, row)
        rows[str(number)] = row
    cell = cells.get(reference)
    if cell is None:
        cell = ET.Element(tag("c"), {"r": reference, "s": style})
        column = column_index_from_string(re.findall(r"^[A-Z]+", reference)[0])
        index = next(
            (
                i
                for i, existing in enumerate(row)
                if column_index_from_string(re.findall(r"^[A-Z]+", existing.get("r", "A1"))[0]) > column
            ),
            len(row),
        )
        row.insert(index, cell)
        cells[reference] = cell
    for child in list(cell):
        cell.remove(child)
    cell.attrib.pop("t", None)
    if formula:
        ET.SubElement(cell, tag("f")).text = value.lstrip("=")
    else:
        cell.set("t", "inlineStr")
        text = ET.SubElement(ET.SubElement(cell, tag("is")), tag("t"))
        text.text = value
    return cell


def merge_calculated_values(destination: Path, calculated_copy: Path) -> int:
    """Übernimmt nur Formelwerte; Excel-Erweiterungen und Eingaben bleiben nativ."""
    native, calculated = WorkbookPackage(destination), WorkbookPackage(calculated_copy)
    updated = 0
    for title in native.sheets:
        root = native.read_sheet(title)
        cached = cell_map(calculated.read_sheet(title))
        for reference, cell in cell_map(root).items():
            if cell.find(tag("f")) is None:
                continue
            other = cached.get(reference)
            if other is None or other.find(tag("v")) is None:
                continue
            if other.get("t") == "e":
                raise ValueError(f"Formelfehler nach Neuberechnung: {title}!{reference} {calculated.value(other)}")
            old = cell.find(tag("v"))
            if old is not None:
                cell.remove(old)
            ET.SubElement(cell, tag("v")).text = calculated.value(other)
            if other.get("t") in ("str", "s", "inlineStr"):
                cell.set("t", "str")
            elif other.get("t") == "b":
                cell.set("t", "b")
            else:
                cell.attrib.pop("t", None)
            updated += 1
        native.save_sheet(title, root)
    native.write(destination)
    return updated
