"""Gemeinsame datierte Zuordnung MA in einer nativen Kundenmappe."""

from xml.etree import ElementTree as ET

from openpyxl.utils.cell import get_column_letter

from data_imports.workbook_package import NS, WorkbookPackage, cell_map, set_cell, tag

RELATION = "relation_mandate_emp"


def primary_mask(mandate: str, day: str) -> str:
    """P-Zeilen mit offenen oder den Stichtag einschliessenden Datumsgrenzen."""
    return (
        f'({RELATION}[mandate_id]={mandate})*({RELATION}[role]="P")'
        f'*(({RELATION}[valid_from]="")+ISNUMBER({RELATION}[valid_from])*({RELATION}[valid_from]<={day}))'
        f'*(({RELATION}[valid_to]="")+ISNUMBER({RELATION}[valid_to])*({RELATION}[valid_to]>={day}))'
    )


def primary_formula(mandate: str, day: str) -> str:
    """Keine willkürliche Auswahl bei mehreren P oder ungültigen Zeiträumen."""
    mask = primary_mask(mandate, day)
    invalid = (
        f"SUMPRODUCT(({RELATION}[mandate_id]={mandate})*("
        f'({RELATION}[valid_from]<>"")*(1-ISNUMBER({RELATION}[valid_from]))'
        f'+({RELATION}[valid_to]<>"")*(1-ISNUMBER({RELATION}[valid_to]))'
        f'+({RELATION}[valid_from]<>"")*({RELATION}[valid_to]<>"")*({RELATION}[valid_from]>{RELATION}[valid_to])'
        f'+({RELATION}[role]<>"")*({RELATION}[role]<>"P")*({RELATION}[role]<>"S")))'
    )
    return (
        f'IF({mandate}="","",IF(AND(ISNUMBER({day}),({invalid})=0,SUMPRODUCT({mask})=1),'
        f'IFERROR(INDEX({RELATION}[employee_id],MATCH(1,INDEX({mask},0),0))&"",""),""))'
    )


def patch_assignment_formulas(package: WorkbookPackage) -> None:
    """Ersetzt alte Paarzählungen durch Zeitraumprüfungen; Eingaben bleiben erhalten."""
    root = package.read_sheet("Zuordnung MA")
    for row in range(4, 2001):
        count = f"SUMPRODUCT({primary_mask(f'$A{row}', 'TODAY()')})"
        formulas = {
            "F": f'IF($A{row}="","",IF(OR(AND($E{row}<>"",$E{row}<TODAY()),AND($Q{row}<>"",$Q{row}<TODAY())),"ausgelaufen",IF(AND($P{row}<>"",$P{row}>TODAY()),"zukünftig","aktiv")))',
            "I": f'IF($A{row}="","",IF({count}=0,"fehlt",IF({count}>1,"doppelt","ok")))',
            "J": f'IF(AND($A{row}<>"",$C{row}="P",OR($P{row}="",$P{row}<=TODAY()),OR($Q{row}="",$Q{row}>=TODAY())),$A{row},"")',
            "L": f'IF($A{row}="","",MID(""&IF($F{row}="ausgelaufen"," · Auftrag oder Zuordnung beendet; historische Zeile behalten","")&IF($I{row}="fehlt"," · Heute keine primäre Betreuungsperson (P)","")&IF($I{row}="doppelt"," · Heute mehrere primäre Betreuungspersonen (P)","")&IF($C{row}=""," · Rolle nicht gesetzt; Berichtszuständigkeit erfordert P",""),4,900))',
        }
        errors = [
            f'IF(COUNTIF(mandate[mandate_id],$A{row})=0," · Auftrag-Nr gibt es nicht","")',
            f'IF(OR($B{row}="",COUNTIF(masterdata_employee[employee_id],$B{row})=0)," · Mitarbeiter-Nr fehlt oder gibt es nicht","")',
            f'IF(AND($C{row}<>"",NOT(OR($C{row}="P",$C{row}="S")))," · Rolle muss P/S sein","")',
            f'IF(OR(AND($P{row}<>"",NOT(ISNUMBER($P{row}))),AND($Q{row}<>"",NOT(ISNUMBER($Q{row}))))," · Zuordnungsdatum ungültig","")',
            f'IF(AND(ISNUMBER($P{row}),ISNUMBER($Q{row}),$P{row}>$Q{row})," · Ende vor Beginn","")',
            f'IF(COUNTIFS({RELATION}[mandate_id],$A{row},{RELATION}[employee_id],$B{row},{RELATION}[role],$C{row},{RELATION}[valid_from],$P{row},{RELATION}[valid_to],$Q{row})>1," · Gleicher Zeitraum doppelt erfasst","")',
            f'IF(AND($C{row}="P",SUMPRODUCT(({RELATION}[mandate_id]=$A{row})*({RELATION}[role]="P")'
            f'*(({RELATION}[valid_from]="")+ISNUMBER({RELATION}[valid_from])*({RELATION}[valid_from]<=IF($Q{row}="",DATE(9999,12,31),$Q{row})))'
            f'*(({RELATION}[valid_to]="")+ISNUMBER({RELATION}[valid_to])*({RELATION}[valid_to]>=IF($P{row}="",0,$P{row}))))>1)," · P-Zeiträume überschneiden sich","")',
        ]
        formulas["K"] = f'IF($A{row}="","",MID(""&' + "&".join(errors) + ",4,900))"
        for column, formula in formulas.items():
            set_cell(root, f"{column}{row}", formula, "26", True)
    path, table = package.table(RELATION)
    columns = table.findall("m:tableColumns/m:tableColumn", NS)
    cells = cell_map(root)
    for number, column in enumerate(columns, 1):
        formula = cells.get(f"{get_column_letter(number)}4")
        if formula is not None and formula.find(tag("f")) is not None:
            node = column.find(tag("calculatedColumnFormula"))
            if node is None:
                node = ET.SubElement(column, tag("calculatedColumnFormula"))
            node.text = formula.findtext(tag("f"), "")
    package.put_table(path, table)
    package.save_sheet("Zuordnung MA", root)


def patch_report_formulas(package: WorkbookPackage) -> None:
    """Bericht-Zuständigkeit kommt ausschliesslich aus der gemeinsamen Tabelle."""
    root = package.read_sheet("Berichte")
    for row in range(4, 1991):
        set_cell(root, f"M{row}", primary_formula(f"$C{row}", f"$E{row}"), "26", True)
    path, table = package.table("report")
    column = table.findall("m:tableColumns/m:tableColumn", NS)[12]
    node = column.find(tag("calculatedColumnFormula"))
    if node is None:
        node = ET.SubElement(column, tag("calculatedColumnFormula"))
    node.text = cell_map(root)["M4"].findtext(tag("f"), "")
    package.put_table(path, table)
    package.save_sheet("Berichte", root)
