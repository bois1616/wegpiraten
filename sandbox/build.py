"""Baut sandbox/wegpiraten_datenbank_sandbox.xlsx auf das Modell Kind/Auftrag/Betreuung um.

Arbeitet auf der gesicherten Ausgangsdatei und schreibt die Zieldatei neu.
Die Blätter Leistungstypen, Leistungsbesteller, Kostenträger, Mitarbeiter,
Büros und Hilfsdaten bleiben unangetastet.

Spaltenverweise stehen als {Blatt.feldname} in den Formeln und werden erst beim
Bauen zu Buchstaben aufgelöst; Umsortieren einer Spalte zieht damit alle Formeln,
Gültigkeiten und Prüfungen mit.

Erfasst wird direkt in den Blättern; LibreOffice' Daten → Formular übernimmt den
geführten Weg. Eigene Erfassungsmasken gab es am 04.09.2026 kurz, sie sind wieder
entfernt: sie konnten nicht selbst in die Tabelle schreiben, und der Kopierschritt
war teurer als der Gewinn.
"""

import collections
import copy
import json
import os
import re
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.protection import SheetProtection
from openpyxl.worksheet.table import Table, TableStyleInfo

SANDBOX = Path(__file__).parent
SRC = SANDBOX / "wegpiraten_datenbank(1).xlsx"
DST = Path(os.environ.get("WEGPIRATEN_DST", SANDBOX / "wegpiraten_datenbank_neu.xlsx"))
DATA = SANDBOX / "migration_v2_neu.json"
REPORTS_SEED = SANDBOX / "reports_import.json"
# Handarbeit (Rollen in Zuordnung MA, Berichte) stammt aus der bisherigen Sandbox-Datei.
# Familien und Kind-Familie-Zuordnung werden nicht übernommen: die Sandbox trägt dort nur
# Demonstrationszeilen (Nipote, Burri), keine Daten.
HAND = Path(os.environ.get("WEGPIRATEN_HAND", DST))
CARRY_FAMILIES = False
# Blattschutz aus (24.09.2026): Sortieren scheitert, sobald ein Blatt gesperrte Formelzellen
# enthält – »Geschützte Zellen können nicht geändert werden«. Die grauen Spalten bleiben
# als Markierung, gesperrt sind sie nicht mehr.
PROTECT_SHEETS = False
STAND = "04.09.2026"

MAX = 2000  # Zeilenreserve für Formeln, Namen und Gültigkeiten
TOP = 4     # erste Datenzeile: 1 Kurzerklärung, 2 Beschriftung, 3 Feldname
ST_MAX = 60  # Zeilenreserve auf dem Blatt Leistungstypen
FONT = "Calibri"

# ---------------------------------------------------------------- Formatierung

C_LABEL = "DDEBF7"   # Beschriftungszeile
C_TECH = "729FCF"    # technische Kopfzeile (Farbe der Altdatei)
C_AUTO = "F2F2F2"    # automatisch berechnet, gesperrt
C_HINT = "FFF2CC"    # Annahme / zu klären
C_BAD = "FFC7CE"     # Prüfung angeschlagen
C_REQ = "9DC3E6"     # Pflichtfeld im Tabellenkopf

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
OPEN = Protection(locked=False)

# ------------------------------------------------------------ Spaltenauflösung

SHEETS = {"K": "Kinder", "A": "Aufträge", "B": "Betreuungen",
          "Z": "Zuordnung MA", "P": "Ansprechpersonen", "F": "Familien",
          "R": "Berichte"}
TOKEN = re.compile(r"\{([KABZPFR])\.([a-z_]+)\}")
MODEL = {}


def resolve(text):
    """{K.last_name} -> D, {MAX} -> 2000; {row} bleibt für write_rows stehen.

    Die Formeln sind geschrieben, als begänne die erste Datenzeile bei 3. Seit die
    Blätter eine Kurzerklärung in Zeile 1 tragen, ist es Zeile TOP; die beiden
    Ersetzungen unten schieben genau die eigenen Bereiche nach. Erkennungsmerkmal
    ist ${MAX}: die unveränderten Stammdatenblätter enden auf $200, nicht auf $2000.
    """
    def sub(match):
        prefix, field = match.groups()
        columns = MODEL[prefix]
        index = next(i for i, c in enumerate(columns, 1) if c["name"] == field)
        return get_column_letter(index)
    out = TOKEN.sub(sub, text).replace("{MAX}", str(MAX))
    out = re.sub(r"\$3:(\$[A-Z]{1,3}\$%d)(?![0-9])" % MAX, r"$%d:\1" % TOP, out)
    out = re.sub(r"(\$[A-Z]{1,3})3(?![0-9])", r"\g<1>%d" % TOP, out)
    return out


def _wrap_index(formula, kind):
    """Jedes INDEX(...) gegen leere Zielzellen absichern.

    Excel liefert für INDEX auf eine leere Zelle die Zahl 0, LibreOffice liefert
    leer. Ungeschützt wird daraus in Excel eine 0, die sich als Text wie "0"
    verhält und jeden Folgevergleich verdreht: genau daran hingen am 05.09.2026
    die leeren Kurzzeichen und Indexkinder. Text bekommt &"" angehängt,
    Datums- und Zahlenspalten einen IF-Vergleich, weil &"" dort den Typ zerstören
    würde.
    """
    out, i = [], 0
    while True:
        j = formula.find("INDEX(", i)
        if j == -1:
            out.append(formula[i:])
            return "".join(out)
        depth, k = 0, j + len("INDEX(") - 1
        while k < len(formula):
            if formula[k] == "(":
                depth += 1
            elif formula[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        inner = formula[j:k + 1]
        out.append(formula[i:j])
        out.append(f'IF({inner}="","",{inner})' if kind in ("date", "number")
                   else f'({inner}&"")')
        i = k + 1


def guard_all_lookups():
    """Einmalig beim Laden: alle Auto-Spalten gegen die Excel-Nullfalle sichern."""
    for cols in MODEL.values():
        for col in cols:
            if col.get("auto") and "INDEX(" in col["formula"]:
                col["formula"] = _wrap_index(col["formula"], col.get("kind"))


def _exact(token, name):
    """Ein Codefeld exakt gegen seine Werteliste; COUNTIF wäre hier zu nachsichtig."""
    return f'IF(${token}{{row}}="",0,--(SUMPRODUCT(--EXACT({name},${token}{{row}}))=0))'


def _array(values):
    """Excel-Array-Literal aus einer festen Liste von Strings, Komma-getrennt."""
    return "{" + ",".join('"' + v.replace('"', '""') + '"' for v in values) + "}"


def issue_columns(prefix, guard, fehler, hinweise):
    """Fünf versteckte Spalten, aus denen das Blatt Fehlerliste seine Zeilen zieht.

    Jede Regel ist ein Paar aus Bedingung und Meldung. Zusammengesetzt wird mit
    einem führenden " · " je Treffer; MID schneidet das erste wieder ab. Die ganze
    Kette hängt an IF(id="",...): auf den rund 1900 leeren Reservezeilen wird damit
    keine einzige Bedingung gerechnet.
    """
    def kette(regeln):
        return "".join(f'&IF({bed}," · {text}","")' for bed, text in regeln)

    p = prefix
    err, hint = "{%s.issue_err}" % p, "{%s.issue_hint}" % p
    kind, run = "{%s.issue_kind}" % p, "{%s.issue_run}" % p
    gemeinsam = {"auto": True, "hidden": True, "width": 44}
    return [
        dict(gemeinsam, name="issue_err", label="▸ Fehler dieser Zeile",
             formula='=IF(' + guard + '="","",MID(""' + kette(fehler) + ',4,900))'),
        dict(gemeinsam, name="issue_hint", label="▸ Hinweise dieser Zeile",
             formula='=IF(' + guard + '="","",MID(""' + kette(hinweise) + ',4,900))'),
        dict(gemeinsam, name="issue_kind", label="▸ Art", width=10,
             formula=f'=IF(${err}{{row}}<>"","Fehler",'
                     f'IF(${hint}{{row}}<>"","Hinweis",""))'),
        dict(gemeinsam, name="issue_text", label="▸ Meldung",
             formula=f'=${err}{{row}}&IF(AND(${err}{{row}}<>"",${hint}{{row}}<>""),'
                     f'" · ","")&${hint}{{row}}'),
        # Laufende Nummer über die ganze Spalte: N() der Zeile darüber plus eins,
        # wenn diese Zeile etwas meldet. Ein COUNTIF auf den wachsenden Bereich
        # gäbe dasselbe Ergebnis für das Zweitausendfache an Rechenzeit.
        dict(gemeinsam, name="issue_run", label="▸ lfd. Nr", width=9,
             formula=f'=N(${run}{{prow}})+(${kind}{{row}}<>"")'),
    ]


def spelling_column(id_token, pairs):
    """Auto-Spalte, die alle Codefelder einer Zeile auf exakte Schreibweise prüft."""
    terms = "+".join(_exact(token, name) for token, name in pairs)
    return {
        "name": "spelling_check",
        "status": [],
        "label": "▸ Schreibweise Codewerte",
        "auto": True,
        "width": 16,
        "formula": f'=IF(${id_token}{{row}}="","",IF(' + terms + ',"Schreibweise prüfen","ok"))',
    }


# --------------------------------------------------------------- Blattaufbau

def write_intro(ws, columns, text):
    """Kurzerklärung in Zeile 1, über die ganze Blattbreite.

    Eine Zeile und kein Textfeld: openpyxl kann keine Zeichnungsobjekte anlegen,
    und ein Kommentar wäre erst beim Darüberfahren zu sehen. Wen sie stört, blendet
    Zeile 1 aus – die Tabelle beginnt darunter und bleibt davon unberührt.
    """
    cell = ws.cell(row=1, column=1, value=text)
    cell.font = Font(name=FONT, size=9, italic=True, color="1F4E79")
    cell.alignment = Alignment(wrap_text=True, vertical="center")
    cell.fill = PatternFill("solid", fgColor="EAF1F8")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
    ws.row_dimensions[1].height = 30


def style_header(ws, columns, row_label=TOP - 2, row_tech=TOP - 1):
    """Zeile 1 deutsche Beschriftung, Zeile 2 technischer Feldname."""
    for idx, col in enumerate(columns, start=1):
        letter = get_column_letter(idx)
        auto = col.get("auto", False)

        label = ws.cell(row=row_label, column=idx, value=col["label"])
        label.font = Font(name=FONT, size=10, bold=True, italic=auto)
        label.fill = PatternFill("solid", fgColor=(
            C_AUTO if auto else C_REQ if col.get("required") else C_LABEL))
        label.alignment = Alignment(wrap_text=True, vertical="bottom")
        label.border = BORDER

        tech = ws.cell(row=row_tech, column=idx, value=col["name"])
        tech.font = Font(name=FONT, size=10, bold=True)
        tech.fill = PatternFill("solid", fgColor=C_TECH)
        tech.border = BORDER

        ws.column_dimensions[letter].width = col["width"]
        if col.get("hidden"):
            ws.column_dimensions[letter].hidden = True
    ws.row_dimensions[row_label].height = 42


def add_table(ws, name, columns, last_row):
    ref = f"A{TOP - 1}:{get_column_letter(len(columns))}{max(last_row, TOP)}"
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False
    )
    ws.add_table(table)


def write_rows(ws, columns, records, start_row=TOP):
    """Schreibt Daten und Formelspalten; gibt die letzte belegte Zeile zurück."""
    for r_off, record in enumerate(records):
        row = start_row + r_off
        for c_idx, col in enumerate(columns, start=1):
            cell = ws.cell(row=row, column=c_idx)
            if col.get("auto"):
                cell.value = (resolve(col["formula"])
                              .replace("{row}", str(row))
                              .replace("{prow}", str(row - 1)))
                cell.font = Font(name=FONT, size=10, italic=True, color="595959")
                cell.fill = PatternFill("solid", fgColor=C_AUTO)
            else:
                value = record.get(col["name"])
                if col.get("kind") == "date" and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                cell.value = value
                cell.font = Font(name=FONT, size=10)
                cell.protection = OPEN
            if col.get("kind") == "date":
                cell.number_format = "DD.MM.YYYY"
            elif col.get("kind") == "number":
                cell.number_format = "0.##"
            cell.border = BORDER
    last = start_row + len(records) - 1

    # Formelspalten in die Zeilenreserve verlängern, damit neue Zeilen rechnen.
    for c_idx, col in enumerate(columns, start=1):
        if not col.get("auto"):
            continue
        formula = resolve(col["formula"])
        for row in range(last + 1, MAX + 1):
            cell = ws.cell(row=row, column=c_idx)
            cell.value = (formula.replace("{row}", str(row))
                                 .replace("{prow}", str(row - 1)))
            cell.font = Font(name=FONT, size=10, italic=True, color="595959")
            if col.get("kind") == "date":
                cell.number_format = "DD.MM.YYYY"
    return last


def protect(ws, columns=None):
    """Eingabespalten entsperren, Rest sperren, Blattschutz ohne Kennwort setzen.

    Der Schutz ist Leitplanke, nicht Sicherung: er lässt sich in LibreOffice mit
    einem Klick aufheben. Er verhindert das versehentliche Überschreiben einer
    Formel, mehr soll er nicht.
    """
    for idx, col in enumerate(columns or [], start=1):
        if col.get("auto"):
            continue
        dim = ws.column_dimensions[get_column_letter(idx)]
        dim.protection = OPEN
        dim.font = Font(name=FONT, size=10)
        if col.get("kind") == "date":
            dim.number_format = "DD.MM.YYYY"
        elif col.get("kind") == "number":
            dim.number_format = "0.##"
    if not PROTECT_SHEETS:
        return
    ws.protection = SheetProtection(
        sheet=True, formatCells=False, formatColumns=False, formatRows=False,
        insertRows=False, deleteRows=False, sort=False, autoFilter=False,
        insertColumns=True, deleteColumns=True, objects=True, scenarios=True,
    )


def colour_status_columns(ws, columns):
    """Jede ▸-Spalte, die einen Status meldet: rot bei Fehler, gelb sonst, »ok« farblos."""
    for idx, col in enumerate(columns, start=1):
        if "status" not in col:
            continue
        letter = get_column_letter(idx)
        ref = f"{letter}{TOP}:{letter}{MAX}"
        hart = col["status"]
        if hart:
            bedingung = ",".join(f'${letter}{TOP}="{v}"' for v in hart)
            ws.conditional_formatting.add(
                ref, FormulaRule(formula=[f"OR({bedingung})"],
                                 fill=PatternFill("solid", fgColor=C_BAD),
                                 stopIfTrue=True))
        ws.conditional_formatting.add(
            ref, FormulaRule(formula=[f'AND(${letter}{TOP}<>"",${letter}{TOP}<>"ok")'],
                             fill=PatternFill("solid", fgColor=C_HINT)))


def add_dv(ws, token, dv_type, formula1, title, prompt, formula2=None, operator=None):
    letter = resolve(token)
    dv = DataValidation(
        type=dv_type,
        formula1=resolve(formula1),
        formula2=formula2,
        operator=operator,
        allow_blank=True,
        showDropDown=False,
        showErrorMessage=True,
        showInputMessage=True,
    )
    dv.errorTitle = title
    dv.error = prompt
    dv.promptTitle = title
    dv.prompt = prompt
    dv.add(f"{letter}{TOP}:{letter}{MAX}")
    ws.add_data_validation(dv)


INTRO = {
    "Aufträge":
        "Eine Zeile ist ein bewilligter Auftrag: Leistungsart, Besteller, "
        "Kostenträger, Zeitraum, Kontingent. Daraus entstehen Rechnungsempfänger, "
        "Anrede und Stundensatz. Ein neuer Auftrag braucht anschliessend mindestens "
        "eine Zeile in »Betreuungen« und eine in »Zuordnung MA«. Verlängerung: neuer "
        "Auftrag mit Vorgänger, beim alten »Bewilligung bis« setzen. Auftragsnummern "
        "ändern sich nie mehr, auch wenn später ein Auftrag mit früherem Beginn "
        "dazukommt. Die Geschäftsnummer ist beim Kostenträger P1000 (KJA) verbindlich "
        "yymmddnnn — Datum des Auftrags, nicht der Bewilligung; bei allen anderen "
        "Freitext, fehlen darf sie nie. Bewilligung abgelaufen erkennt man am Filter "
        "auf »Bewilligung bis«, nicht an einem Text in der Geschäftsnummer.",
    "Betreuungen":
        "Eine Zeile ist ein Kind in einem Auftrag, mit Eintritt und Austritt. Jede "
        "Zeile hier ist genau eine Zeile der Accordix-Meldung — was hier fehlt, fehlt "
        "dort. Der Eintritt ist der Beginn der Betreuung dieses Kindes, nicht der "
        "Beginn der Bewilligung. Kommt ein jüngeres Geschwister dazu, im Blatt "
        "»Familien« das Indexkind prüfen.",
    "Zuordnung MA":
        "Wer arbeitet auf welchem Auftrag. Diese Liste allein steuert, für wen ein "
        "Erfassungsbogen erzeugt wird: eine fehlende Zeile erzeugt keinen Bogen, eine "
        "überzählige einen unnötigen. Zeigt eine Zeile auf einen ausgelaufenen "
        "Auftrag, gehört sie entfernt — oder der Auftrag verlängert.",
    "Kinder":
        "Jedes Kind genau einmal, unabhängig davon, wie viele Aufträge es hat. "
        "Geburtsdatum, Geschlecht, UMA/UMF und Wohnkanton verlangt Accordix. Das "
        "Kurzzeichen steht im Erfassungsbogen und im Dateinamen. »Familie« nur bei "
        "Geschwistern füllen; dann bestimmt das Blatt »Familien«, über welches Kind "
        "abgerechnet wird.",
    "Familien":
        "Nur nötig, wo Geschwister betreut werden. Die Familie hält fest, über welches "
        "Kind abgerechnet wird — in der Regel das jüngste. Diese eine Zelle bestimmt "
        "Kurzzeichen und Indexkind aller Aufträge der Familie. Sie ändert sich "
        "nicht, wenn ein Auftrag ausläuft; sie ändert sich, wenn ein jüngeres Kind "
        "dazukommt.",
    "Ansprechpersonen":
        "Die zuständige Person beim Leistungsbesteller; sie erscheint als Anrede auf "
        "der Rechnung. Wechselt die Zuständigkeit, hier eine neue Zeile anlegen und "
        "im Auftrag umhängen. Die alte Zeile bleibt stehen — sie gehört zu den bereits "
        "gestellten Rechnungen.",
    "Berichte":
        "Aufgabenliste, keine Regelverwaltung, Stand 25.09.2026 (aus der Klientenübersicht "
        "befüllt, Erwartung: ändert sich nach Sichtung). Eine Zeile ist ein fälliger oder "
        "erledigter Bericht zu einem Auftrag — berichtet wird über die Familie, deshalb "
        "hängt die Zeile am Auftrag. Rote Zellen der Übersicht sind »Bericht«, orange "
        "»Zwischenbericht«, blaue »Abschlussbericht«; ohne Datum in der Zelle gilt die Monatsmitte. Zuständig ist "
        "automatisch die primäre Betreuungsperson (Rolle P) aus »Zuordnung MA«. Rhythmus "
        "und Intervall stehen am Auftrag.",
}


# --------------------------------------------------------------- Spaltenmodell
# Regel: links wird erfasst, rechts wird gerechnet. Alle Eingabespalten stehen
# lückenlos vorne, alle ▸-Spalten dahinter. Das hält die Erfassungsmasken
# kopierbar und macht den Blattschutz an der Spaltengrenze ablesbar.

KINDER = [
    {"name": "person_id", "label": "Kind-Nr", "required": True, "width": 11},
    {"name": "short_code", "label": "Kurzzeichen", "required": True, "width": 11},
    {"name": "family_id", "label": "Familie (nur bei Geschwistern)", "width": 22},
    {"name": "social_security_number", "label": "AHV-Nummer", "width": 19},
    {"name": "last_name", "label": "Nachname", "required": True, "width": 20},
    {"name": "first_name", "label": "Vorname", "required": True, "width": 18},
    {"name": "date_of_birth", "label": "Geburtsdatum", "required": True, "kind": "date", "width": 13},
    {"name": "gender", "label": "Geschlecht", "required": True, "width": 11},
    {"name": "uma_umf", "label": "unbegleiteter minderjähriger Flüchtling / Ausländer", "required": True, "width": 13},
    {"name": "spoken_language", "label": "Hauptsprache", "width": 12},
    {"name": "canton_of_residence", "label": "Wohnkanton", "required": True, "width": 12},
    {"name": "residence_legal_guardian", "label": "Wohnort (Sorgeberechtigte)", "width": 22},
    {"name": "notes", "label": "Bemerkung (intern)", "width": 30},
    {
        "name": "short_code_proposal",
        "label": "▸ Kurzzeichen-Vorschlag",
        "auto": True,
        "width": 13,
        "formula": '=IF($'"{K.person_id}"'{row}="","",'
                   'LEFT($'"{K.first_name}"'{row},2)&LEFT($'"{K.last_name}"'{row},2))',
    },
    {
        "name": "short_code_check",
        "status": [],
        "label": "▸ Kurzzeichen eindeutig?",
        "auto": True,
        "width": 14,
        "formula": '=IF($'"{K.person_id}"'{row}="","",'
                   'IF($'"{K.short_code}"'{row}="","fehlt",'
                   'IF(COUNTIF($'"{K.short_code}"'$3:$'"{K.short_code}"'${MAX},'
                   '$'"{K.short_code}"'{row})>1,"doppelt","ok")))',
    },
    {
        "name": "care_count_current",
        "label": "▸ Betreuungen heute",
        "auto": True,
        "width": 12,
        "formula": '=IF($'"{K.person_id}"'{row}="","",SUMPRODUCT('
                   '(Betreuungen!$'"{B.person_id}"'$3:$'"{B.person_id}"'${MAX}='
                   '$'"{K.person_id}"'{row})'
                   '*(Betreuungen!$'"{B.start_date}"'$3:$'"{B.start_date}"'${MAX}<>"")'
                   '*(Betreuungen!$'"{B.start_date}"'$3:$'"{B.start_date}"'${MAX}<=TODAY())'
                   '*((Betreuungen!$'"{B.end_date}"'$3:$'"{B.end_date}"'${MAX}="")'
                   '+((Betreuungen!$'"{B.end_date}"'$3:$'"{B.end_date}"'${MAX}<>"")'
                   '*(Betreuungen!$'"{B.end_date}"'$3:$'"{B.end_date}"'${MAX}>=TODAY())))))',
    },
    {
        "name": "care_count_total",
        "label": "▸ Betreuungen gesamt",
        "auto": True,
        "width": 12,
        "formula": '=IF($'"{K.person_id}"'{row}="","",'
                   'COUNTIF(Betreuungen!$'"{B.person_id}"'$3:$'"{B.person_id}"'${MAX},'
                   '$'"{K.person_id}"'{row}))',
    },
    {
        "name": "display_name",
        "label": "▸ Kind (Nr und Name)",
        "auto": True,
        "hidden": True,
        "width": 30,
        # Speist die Auswahlliste im Blatt Familien. Die Nummer steht vorne, damit
        # sie sich wieder abschneiden lässt; getrennt wird am ersten Leerzeichen.
        "formula": '=IF($'"{K.person_id}"'{row}="","",'
                   '$'"{K.person_id}"'{row}&" — "&$'"{K.last_name}"'{row}&", "'
                   '&$'"{K.first_name}"'{row})',
    },
    spelling_column("{K.person_id}", [
        ("{K.gender}", "accordix_gender"),
        ("{K.uma_umf}", "accordix_uma_umf"),
        ("{K.spoken_language}", "accordix_spoken_language"),
        ("{K.canton_of_residence}", "accordix_canton_of_residence"),
    ]),
]

APP_T = 'TRIM(${A.application_number}{row}&"")'

AUFTRAEGE = [
    {"name": "mandate_id", "label": "Auftrag-Nr", "required": True, "width": 11},
    {"name": "service_type_id", "label": "Leistungsart", "required": True, "width": 12},
    {"name": "service_requester_id", "label": "Leistungsbesteller", "required": True, "width": 13},
    {"name": "contact_person_id", "label": "Ansprechperson", "required": True, "width": 13},
    {"name": "payer_id", "label": "Kostenträger", "required": True, "width": 12},
    {"name": "tenant_id", "label": "Standort", "required": True, "width": 10},
    {"name": "application_number", "label": "Geschäftsnummer", "width": 14},
    {"name": "start_date", "label": "Bewilligung von", "required": True, "kind": "date", "width": 13},
    {"name": "end_date", "label": "Bewilligung bis", "kind": "date", "width": 13},
    {"name": "allowed_travel_time", "label": "Kontingent Fahrzeit (h)", "kind": "number", "width": 11},
    {"name": "allowed_direct_effort", "label": "Kontingent direkt (h)", "kind": "number", "width": 11},
    {"name": "allowed_indirect_effort", "label": "Kontingent indirekt (h)", "kind": "number", "width": 11},
    {"name": "allocation", "label": "Zuweisungsgrundlage", "width": 22},
    {"name": "notes", "label": "Bemerkung (intern)", "width": 24},
    {"name": "predecessor_choice", "label": "Vorgängerauftrag", "width": 13},
    {"name": "report_cadence", "label": "Berichtsrhythmus", "width": 16},
    {"name": "report_interval_months", "label": "Berichtsintervall (Monate)", "kind": "number", "width": 14},
    {
        "name": "mandate_display",
        "label": "▸ Auftrag (Anzeige)",
        "auto": True,
        "hidden": True,
        "width": 44,
        # Speist liste_auftrag_namen; dieselbe Idee wie Kinder.display_name für
        # das Indexkind der Familien.
        # Kein TEXT(): dessen Formatcode ist locale-abhängig und in LibreOffice
        # anders ausgewertet worden als erwartet – nur DAY/MONTH/YEAR sind es
        # nicht (vgl. die INDEX/MATCH- statt XLOOKUP-Begründung weiter unten).
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",$'"{A.mandate_id}"'{row}'
                   '&" — "&$'"{A.index_person_name}"'{row}'
                   '&" ("&$'"{A.service_type_name}"'{row}'
                   '&IF($'"{A.end_date}"'{row}="","",", bis "'
                   '&RIGHT("0"&DAY($'"{A.end_date}"'{row}),2)&"."'
                   '&RIGHT("0"&MONTH($'"{A.end_date}"'{row}),2)&"."'
                   '&YEAR($'"{A.end_date}"'{row}))&")")',
    },
    {
        "name": "predecessor_mandate_id",
        "label": "▸ Vorgängerauftrag (Nr)",
        "auto": True,
        "hidden": True,
        "width": 13,
        # Gewählt wird »A1002 — Nipote, Luan (SPF, bis 31.03.2027)«, gespeichert
        # wird A1002. Eine von Hand getippte blosse Nummer bleibt gültig.
        "formula": '=IF($'"{A.predecessor_choice}"'{row}="","",'
                   'IF(ISNUMBER(FIND(" ",$'"{A.predecessor_choice}"'{row})),'
                   'LEFT($'"{A.predecessor_choice}"'{row},'
                   'FIND(" ",$'"{A.predecessor_choice}"'{row})-1),'
                   '$'"{A.predecessor_choice}"'{row}))',
    },
    {
        "name": "successor_mandate_id",
        "label": "▸ Nachfolgeauftrag",
        "auto": True,
        "width": 13,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",IFERROR(INDEX('
                   '$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},'
                   'MATCH($'"{A.mandate_id}"'{row},'
                   '$'"{A.predecessor_mandate_id}"'$3:'
                   '$'"{A.predecessor_mandate_id}"'${MAX},0)),""))',
    },
    {
        "name": "short_code",
        "label": "▸ Kurzzeichen",
        "auto": True,
        "width": 11,
        "formula": '=IF($'"{A.index_person_id}"'{row}="","",IFERROR(INDEX('
                   'Kinder!$'"{K.short_code}"'$3:$'"{K.short_code}"'${MAX},'
                   'MATCH($'"{A.index_person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0)),"unbekannt"))',
    },
    {
        "name": "index_person_name",
        "label": "▸ Indexkind (Name)",
        "auto": True,
        "width": 22,
        "formula": '=IF($'"{A.index_person_id}"'{row}="","",IFERROR(INDEX('
                   'Kinder!$'"{K.last_name}"'$3:$'"{K.last_name}"'${MAX},'
                   'MATCH($'"{A.index_person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0))&", "&INDEX('
                   'Kinder!$'"{K.first_name}"'$3:$'"{K.first_name}"'${MAX},'
                   'MATCH($'"{A.index_person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0)),"unbekannt"))',
    },
    {
        "name": "sr_ap_gender",
        "label": "▸ Ansprechperson Anrede",
        "auto": True,
        "width": 11,
        "formula": '=IF($'"{A.contact_person_id}"'{row}="","",IFERROR(INDEX('
                   'Ansprechpersonen!$'"{P.gender}"'$3:$'"{P.gender}"'${MAX},'
                   'MATCH($'"{A.contact_person_id}"'{row},'
                   'Ansprechpersonen!$'"{P.contact_person_id}"'$3:'
                   '$'"{P.contact_person_id}"'${MAX},0)),"unbekannt"))',
    },
    {
        "name": "sr_ap_first_name",
        "label": "▸ Ansprechperson Vorname",
        "auto": True,
        "width": 16,
        "formula": '=IF($'"{A.contact_person_id}"'{row}="","",IFERROR(INDEX('
                   'Ansprechpersonen!$'"{P.first_name}"'$3:$'"{P.first_name}"'${MAX},'
                   'MATCH($'"{A.contact_person_id}"'{row},'
                   'Ansprechpersonen!$'"{P.contact_person_id}"'$3:'
                   '$'"{P.contact_person_id}"'${MAX},0)),"unbekannt"))',
    },
    {
        "name": "sr_ap_last_name",
        "label": "▸ Ansprechperson Nachname",
        "auto": True,
        "width": 16,
        "formula": '=IF($'"{A.contact_person_id}"'{row}="","",IFERROR(INDEX('
                   'Ansprechpersonen!$'"{P.last_name}"'$3:$'"{P.last_name}"'${MAX},'
                   'MATCH($'"{A.contact_person_id}"'{row},'
                   'Ansprechpersonen!$'"{P.contact_person_id}"'$3:'
                   '$'"{P.contact_person_id}"'${MAX},0)),"unbekannt"))',
    },
    {
        "name": "care_person_id",
        "label": "▸ Betreuungskind",
        "auto": True,
        "width": 13,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",'
                   'IF($'"{A.person_count_total}"'{row}=0,"keines",'
                   'IF($'"{A.person_count_total}"'{row}>1,'
                   '"mehrere ("&$'"{A.person_count_total}"'{row}&")",'
                   'IFERROR(INDEX(Betreuungen!$'"{B.person_id}"'$3:$'"{B.person_id}"'${MAX},'
                   'MATCH($'"{A.mandate_id}"'{row},'
                   'Betreuungen!$'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX},0)),""))))',
    },
    {
        "name": "family_id",
        "label": "▸ Familie",
        "auto": True,
        "width": 10,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Betreuungen!$'"{B.family_id}"'$3:$'"{B.family_id}"'${MAX},'
                   'MATCH($'"{A.mandate_id}"'{row},'
                   'Betreuungen!$'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX},0)),""))',
    },
    {
        "name": "index_person_id",
        "label": "▸ Indexkind",
        "auto": True,
        "width": 13,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",'
                   'IF($'"{A.family_id}"'{row}<>"",IFERROR(INDEX('
                   'Familien!$'"{F.index_person_id}"'$3:'
                   '$'"{F.index_person_id}"'${MAX},'
                   'MATCH($'"{A.family_id}"'{row},'
                   'Familien!$'"{F.family_id}"'$3:$'"{F.family_id}"'${MAX},0)),""),'
                   'IFERROR(INDEX(Betreuungen!$'"{B.person_id}"'$3:'
                   '$'"{B.person_id}"'${MAX},MATCH($'"{A.mandate_id}"'{row},'
                   'Betreuungen!$'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX},0)),"")))',
    },
    {
        "name": "family_check",
        "status": ['Geschwister ohne Familie'],
        "label": "▸ Kinder aus einer Familie?",
        "auto": True,
        "width": 18,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",'
                   'IF($'"{A.person_count_total}"'{row}=0,"keine Betreuung",'
                   'IF(SUMPRODUCT('
                   '(Betreuungen!$'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX}='
                   '$'"{A.mandate_id}"'{row})'
                   '*(Betreuungen!$'"{B.family_id}"'$3:$'"{B.family_id}"'${MAX}<>'
                   '$'"{A.family_id}"'{row}))>0,"mehrere Familien",'
                   'IF(AND($'"{A.person_count_total}"'{row}>1,'
                   '$'"{A.family_id}"'{row}=""),"Geschwister ohne Familie","ok"))))',
    },
    {
        "name": "person_count_current",
        "label": "▸ Kinder betreut heute",
        "auto": True,
        "width": 12,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",SUMPRODUCT('
                   '(Betreuungen!$'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX}='
                   '$'"{A.mandate_id}"'{row})'
                   '*(Betreuungen!$'"{B.start_date}"'$3:$'"{B.start_date}"'${MAX}<>"")'
                   '*(Betreuungen!$'"{B.start_date}"'$3:$'"{B.start_date}"'${MAX}<=TODAY())'
                   '*((Betreuungen!$'"{B.end_date}"'$3:$'"{B.end_date}"'${MAX}="")'
                   '+((Betreuungen!$'"{B.end_date}"'$3:$'"{B.end_date}"'${MAX}<>"")'
                   '*(Betreuungen!$'"{B.end_date}"'$3:$'"{B.end_date}"'${MAX}>=TODAY())))))',
    },
    {
        "name": "person_count_total",
        "label": "▸ Kinder gesamt",
        "auto": True,
        "width": 11,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",'
                   'COUNTIF(Betreuungen!$'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX},'
                   '$'"{A.mandate_id}"'{row}))',
    },
    {
        "name": "quota_total",
        "label": "▸ Kontingent gesamt (h)",
        "auto": True,
        "width": 12,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",'
                   'N($'"{A.allowed_travel_time}"'{row})'
                   '+N($'"{A.allowed_direct_effort}"'{row})'
                   '+N($'"{A.allowed_indirect_effort}"'{row}))',
    },
    {
        "name": "quota_check",
        "status": [],
        "label": "▸ Kontrolle direkt/indirekt",
        "auto": True,
        "width": 16,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",'
                   'IF(N($'"{A.allowed_direct_effort}"'{row})>='
                   '2*N($'"{A.allowed_indirect_effort}"'{row}),"ok","indirekt prüfen"))',
    },
    {
        "name": "service_type_name",
        "label": "▸ Leistungsart (Klartext)",
        "auto": True,
        "width": 30,
        "formula": '=IF($'"{A.service_type_id}"'{row}="","",IFERROR(INDEX('
                   'Leistungstypen!$C$2:$C$200,MATCH($'"{A.service_type_id}"'{row},'
                   'Leistungstypen!$A$2:$A$200,0)),"unbekannt"))',
    },
    {
        "name": "service_type_check",
        "status": ["Leistungsart unbekannt", "Leistungsart ausgelaufen"],
        "label": "▸ Leistungsart gültig?",
        "auto": True,
        "width": 16,
        "formula": '=IF($'"{A.mandate_id}"'{row}="","",'
                   'IF(COUNTIF(Leistungstypen!$A$2:$A$200,'
                   '$'"{A.service_type_id}"'{row})=0,"Leistungsart unbekannt",'
                   'IF(AND(OR($'"{A.end_date}"'{row}="",'
                   '$'"{A.end_date}"'{row}>=TODAY()),'
                   'IFERROR(INDEX(Leistungstypen!$K$2:$K$' + str(ST_MAX) + ','
                   'MATCH($'"{A.service_type_id}"'{row},'
                   'Leistungstypen!$A$2:$A$' + str(ST_MAX) + ',0)),"")="ausgelaufen"),'
                   '"Leistungsart ausgelaufen","ok")))',
    },
    {
        "name": "application_number_check",
        "status": ["fehlt", "Notation", "Datum ungültig"],
        "label": "▸ Geschäftsnummer gültig?",
        "auto": True,
        "width": 16,
        # Kostenträger P1000 (KJA): yymmddnnn ist verbindlich, das Datum muss es geben.
        # Alle anderen Kostenträger: Freitext, nur »fehlt« ist ein Fehler.
        "formula": '=IF(${A.mandate_id}{row}="","",IF(' + APP_T + '="","fehlt",'
                   'IF(${A.payer_id}{row}<>"P1000","ok",'
                   'IFERROR(IF(NOT(AND(LEN(' + APP_T + ')=9,SUMPRODUCT(--ISNUMBER(VALUE('
                   'MID(' + APP_T + ',{1,2,3,4,5,6,7,8,9},1))))=9,'
                   'VALUE(MID(' + APP_T + ',7,3))>0)),"Notation",'
                   'IF(AND(VALUE(MID(' + APP_T + ',3,2))>=1,VALUE(MID(' + APP_T + ',3,2))<=12,'
                   'VALUE(MID(' + APP_T + ',5,2))>=1,'
                   'DAY(DATE(2000+VALUE(LEFT(' + APP_T + ',2)),VALUE(MID(' + APP_T + ',3,2)),'
                   'VALUE(MID(' + APP_T + ',5,2))))=VALUE(MID(' + APP_T + ',5,2))),'
                   '"ok","Datum ungültig")),"Notation"))))',
    },
    spelling_column("{A.mandate_id}", [("{A.allocation}", "accordix_allocation")]),
]

BETREUUNGEN = [
    {"name": "mandate_id", "label": "Auftrag-Nr", "required": True, "width": 11},
    {"name": "person_id", "label": "Kind-Nr", "required": True, "width": 11},
    {"name": "start_date", "label": "Eintritt", "required": True, "kind": "date", "width": 12},
    {"name": "end_date", "label": "Austritt", "kind": "date", "width": 12},
    {"name": "is_leaving_reason_planned", "label": "war der Austritt geplant?", "width": 12},
    {"name": "leaving_reason", "label": "Austrittsgrund", "width": 30},
    {"name": "custom_leaving_reason", "label": "Anderer Austrittsgrund", "width": 22},
    {"name": "after_leave_situation", "label": "Situation nach Austritt", "width": 30},
    {"name": "custom_after_leave_situation", "label": "Andere Situation nach Austritt", "width": 22},
    {
        "name": "is_consultative_adolescent_psychiatric_care",
        "label": "IBF: Konsiliarische jugendpsychiatrische Versorgung",
        "width": 13,
    },
    {
        "name": "number_of_care_days_per_week",
        "label": "SPT: Anzahl Betreuungstage pro Woche",
        "kind": "number",
        "width": 12,
    },
    {"name": "remarks", "label": "Bemerkungen (Accordix)", "width": 26},
    {
        "name": "person_name",
        "label": "▸ Kind (Name)",
        "auto": True,
        "width": 22,
        "formula": '=IF($'"{B.person_id}"'{row}="","",IFERROR(INDEX('
                   'Kinder!$'"{K.last_name}"'$3:$'"{K.last_name}"'${MAX},'
                   'MATCH($'"{B.person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0))&", "&INDEX('
                   'Kinder!$'"{K.first_name}"'$3:$'"{K.first_name}"'${MAX},'
                   'MATCH($'"{B.person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0)),"unbekannt"))',
    },
    {
        "name": "is_index_case",
        "label": "▸ Indexkind?",
        "auto": True,
        "width": 12,
        "formula": '=IF(OR($'"{B.mandate_id}"'{row}="",$'"{B.person_id}"'{row}=""),"",'
                   'IF(IFERROR(INDEX(Aufträge!$'"{A.index_person_id}"'$3:'
                   '$'"{A.index_person_id}"'${MAX},MATCH($'"{B.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),"")='
                   '$'"{B.person_id}"'{row},"Ja","Nein"))',
    },
    {
        "name": "service_type_name",
        "label": "▸ Leistungsart",
        "auto": True,
        "width": 30,
        "formula": '=IF($'"{B.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.service_type_name}"'$3:$'"{A.service_type_name}"'${MAX},'
                   'MATCH($'"{B.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),"unbekannt"))',
    },
    {
        "name": "mandate_start",
        "label": "▸ Bewilligung von",
        "auto": True,
        "kind": "date",
        "width": 13,
        "formula": '=IF($'"{B.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.start_date}"'$3:$'"{A.start_date}"'${MAX},'
                   'MATCH($'"{B.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),""))',
    },
    {
        "name": "mandate_end",
        "label": "▸ Bewilligung bis",
        "auto": True,
        "kind": "date",
        "width": 13,
        "formula": '=IF($'"{B.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.end_date}"'$3:$'"{A.end_date}"'${MAX},'
                   'MATCH($'"{B.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),""))',
    },
    {
        "name": "overlap_check",
        "status": [],
        "label": "▸ Auftrag überschneidet sich?",
        "auto": True,
        "width": 16,
        "formula": '=IF(OR($'"{B.mandate_id}"'{row}="",$'"{B.person_id}"'{row}="",'
                   '$'"{B.mandate_start}"'{row}=""),"",IF(SUMPRODUCT('
                   '($'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX}<>"")'
                   '*($'"{B.person_id}"'$3:$'"{B.person_id}"'${MAX}='
                   '$'"{B.person_id}"'{row})'
                   '*($'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX}<>'
                   '$'"{B.mandate_id}"'{row})'
                   '*($'"{B.service_type_name}"'$3:$'"{B.service_type_name}"'${MAX}='
                   '$'"{B.service_type_name}"'{row})'
                   '*($'"{B.mandate_start}"'$3:$'"{B.mandate_start}"'${MAX}<>"")'
                   '*($'"{B.mandate_start}"'$3:$'"{B.mandate_start}"'${MAX}<='
                   'IF($'"{B.mandate_end}"'{row}="",DATE(2100,12,31),'
                   '$'"{B.mandate_end}"'{row}))'
                   '*(($'"{B.mandate_end}"'$3:$'"{B.mandate_end}"'${MAX}="")'
                   '+(($'"{B.mandate_end}"'$3:$'"{B.mandate_end}"'${MAX}<>"")'
                   '*($'"{B.mandate_end}"'$3:$'"{B.mandate_end}"'${MAX}>='
                   '$'"{B.mandate_start}"'{row})))'
                   ')>0,"Überschneidung","ok"))',
    },
    {
        "name": "entry_chain_check",
        "status": [],
        "label": "▸ Eintritt aus Vorgänger?",
        "auto": True,
        "width": 16,
        "formula": '=IF(OR($'"{B.mandate_id}"'{row}="",$'"{B.person_id}"'{row}="",'
                   '$'"{B.predecessor_mandate_id}"'{row}=""),"",'
                   'IF(COUNTIFS($'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX},'
                   '$'"{B.predecessor_mandate_id}"'{row},'
                   '$'"{B.person_id}"'$3:$'"{B.person_id}"'${MAX},'
                   '$'"{B.person_id}"'{row})=0,"",'
                   'IF(SUMIFS($'"{B.start_date}"'$3:$'"{B.start_date}"'${MAX},'
                   '$'"{B.mandate_id}"'$3:$'"{B.mandate_id}"'${MAX},'
                   '$'"{B.predecessor_mandate_id}"'{row},'
                   '$'"{B.person_id}"'$3:$'"{B.person_id}"'${MAX},'
                   '$'"{B.person_id}"'{row})=$'"{B.start_date}"'{row},"ok",'
                   '"Eintritt aus Vorgänger übernehmen")))',
    },
    {
        "name": "entry_vs_mandate",
        "label": "▸ Auftrag beginnt vor dem Eintritt?",
        "status": [],
        "auto": True,
        "width": 16,
        "formula": '=IF(OR($'"{B.mandate_id}"'{row}="",$'"{B.start_date}"'{row}="",'
                   '$'"{B.mandate_start}"'{row}=""),"",'
                   'IF(DATE(YEAR($'"{B.mandate_start}"'{row}),MONTH($'"{B.mandate_start}"'{row}),1)'
                   '<DATE(YEAR($'"{B.start_date}"'{row}),MONTH($'"{B.start_date}"'{row}),1),'
                   '"Auftrag älter als der Eintritt","ok"))',
    },
    spelling_column("{B.mandate_id}", [
        ("{B.leaving_reason}", "accordix_leaving_reason"),
        ("{B.after_leave_situation}", "accordix_after_leave_situation"),
    ]),
    {
        "name": "family_id",
        "label": "▸ Familie des Kindes",
        "auto": True,
        "hidden": True,
        "width": 10,
        "formula": '=IF($'"{B.person_id}"'{row}="","",IFERROR(INDEX('
                   'Kinder!$'"{K.family_id}"'$3:$'"{K.family_id}"'${MAX},'
                   'MATCH($'"{B.person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0)),""))',
    },
    {
        "name": "person_dob",
        "label": "▸ Geburtsdatum des Kindes",
        "auto": True,
        "hidden": True,
        "kind": "date",
        "width": 12,
        "formula": '=IF($'"{B.person_id}"'{row}="","",IFERROR(INDEX('
                   'Kinder!$'"{K.date_of_birth}"'$3:$'"{K.date_of_birth}"'${MAX},'
                   'MATCH($'"{B.person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0)),""))',
    },
    {
        "name": "predecessor_mandate_id",
        "label": "▸ Vorgängerauftrag",
        "auto": True,
        "hidden": True,
        "width": 12,
        "formula": '=IF($'"{B.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.predecessor_mandate_id}"'$3:'
                   '$'"{A.predecessor_mandate_id}"'${MAX},'
                   'MATCH($'"{B.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),""))',
    },
]

ANSPRECHPERSONEN = [
    {"name": "contact_person_id", "label": "AP-Nr", "required": True, "width": 10},
    {"name": "service_requester_id", "label": "Leistungsbesteller", "required": True, "width": 13},
    {"name": "gender", "label": "Anrede", "required": True, "width": 10},
    {"name": "first_name", "label": "Vorname", "required": True, "width": 18},
    {"name": "last_name", "label": "Nachname", "required": True, "width": 20},
    {"name": "notes", "label": "Bemerkung (intern)", "width": 46},
    {
        "name": "requester_name",
        "label": "▸ Leistungsbesteller (Name)",
        "auto": True,
        "width": 30,
        "formula": '=IF($'"{P.service_requester_id}"'{row}="","",IFERROR(INDEX('
                   'Leistungsbesteller!$C$3:$C$200,'
                   'MATCH($'"{P.service_requester_id}"'{row},'
                   'Leistungsbesteller!$B$3:$B$200,0)),"unbekannt"))',
    },
    {
        "name": "display_name",
        "label": "▸ Anrede in der Rechnung",
        "auto": True,
        "width": 28,
        "formula": '=IF($'"{P.contact_person_id}"'{row}="","",'
                   'TRIM($'"{P.gender}"'{row}&" "&$'"{P.first_name}"'{row}&" "'
                   '&$'"{P.last_name}"'{row}))',
    },
    {
        "name": "mandate_count",
        "label": "▸ Aufträge",
        "auto": True,
        "width": 10,
        "formula": '=IF($'"{P.contact_person_id}"'{row}="","",'
                   'COUNTIF(Aufträge!$'"{A.contact_person_id}"'$3:'
                   '$'"{A.contact_person_id}"'${MAX},$'"{P.contact_person_id}"'{row}))',
    },
]

FAMILIEN = [
    {"name": "family_id", "label": "Familie", "required": True, "width": 26},
    {"name": "index_person", "label": "Indexkind", "required": True, "width": 32},
    {"name": "notes", "label": "Bemerkung (intern)", "width": 46},
    {
        "name": "index_person_id",
        "label": "▸ Indexkind (Nr)",
        "auto": True,
        "width": 13,
        # Gewählt wird »C1068 — Nipote, Yarrah Orion«, gespeichert wird C1068.
        # Eine von Hand getippte blosse Nummer bleibt ebenfalls gültig.
        "formula": '=IF($'"{F.index_person}"'{row}="","",'
                   'IF(ISNUMBER(FIND(" ",$'"{F.index_person}"'{row})),'
                   'LEFT($'"{F.index_person}"'{row},'
                   'FIND(" ",$'"{F.index_person}"'{row})-1),'
                   '$'"{F.index_person}"'{row}))',
    },
    {
        "name": "person_count",
        "label": "▸ Kinder",
        "auto": True,
        "width": 9,
        "formula": '=IF($'"{F.family_id}"'{row}="","",'
                   'COUNTIF(Kinder!$'"{K.family_id}"'$3:$'"{K.family_id}"'${MAX},'
                   '$'"{F.family_id}"'{row}))',
    },
    {
        "name": "index_person_dob",
        "label": "▸ Geburtsdatum Indexkind",
        "auto": True,
        "hidden": True,
        "kind": "date",
        "width": 12,
        "formula": '=IF($'"{F.index_person_id}"'{row}="","",IFERROR(INDEX('
                   'Kinder!$'"{K.date_of_birth}"'$3:$'"{K.date_of_birth}"'${MAX},'
                   'MATCH($'"{F.index_person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0)),""))',
    },
    {
        "name": "index_family",
        "label": "▸ Familie des Indexkinds",
        "auto": True,
        "hidden": True,
        "width": 12,
        "formula": '=IF($'"{F.index_person_id}"'{row}="","",IFERROR(INDEX('
                   'Kinder!$'"{K.family_id}"'$3:$'"{K.family_id}"'${MAX},'
                   'MATCH($'"{F.index_person_id}"'{row},'
                   'Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},0)),""))',
    },
    {
        "name": "index_check",
        "status": ["fehlt", "gehört nicht zu dieser Familie"],
        "label": "▸ Indexkind plausibel?",
        "auto": True,
        "width": 20,
        # Der Altersvergleich liest bewusst die Datumsspalte oben und nicht INDEX
        # direkt: der Leerzellen-Schutz macht aus einem Datum sonst Text, und N()
        # davon ist 0 – dann gilt jedes Kind als jünger.
        "formula": '=IF($'"{F.family_id}"'{row}="","",'
                   'IF($'"{F.person_count}"'{row}=0,"ohne Kinder",'
                   'IF($'"{F.index_person_id}"'{row}="","fehlt",'
                   'IF($'"{F.index_family}"'{row}<>$'"{F.family_id}"'{row},'
                   '"gehört nicht zu dieser Familie",'
                   'IF(SUMPRODUCT(MAX((Kinder!$'"{K.family_id}"'$3:'
                   '$'"{K.family_id}"'${MAX}=$'"{F.family_id}"'{row})'
                   '*(Kinder!$'"{K.date_of_birth}"'$3:'
                   '$'"{K.date_of_birth}"'${MAX})))>N($'"{F.index_person_dob}"'{row}),'
                   '"nicht das jüngste Kind","ok")))))',
    },
]

ZUORDNUNG = [
    {"name": "mandate_id", "label": "Auftrag-Nr", "required": True, "width": 11},
    {"name": "employee_id", "label": "Mitarbeiter-Nr", "required": True, "width": 12},
    {"name": "role", "label": "Rolle (P/S)", "width": 11},
    {
        "name": "employee_name",
        "label": "▸ Mitarbeiter (Name)",
        "auto": True,
        "width": 24,
        "formula": '=IF($'"{Z.employee_id}"'{row}="","",IFERROR(INDEX('
                   'Mitarbeiter!$D$3:$D$200,MATCH($'"{Z.employee_id}"'{row},'
                   'Mitarbeiter!$B$3:$B$200,0))&", "&INDEX(Mitarbeiter!$C$3:$C$200,'
                   'MATCH($'"{Z.employee_id}"'{row},Mitarbeiter!$B$3:$B$200,0)),'
                   '"unbekannt"))',
    },
    {
        "name": "mandate_end",
        "label": "▸ Bewilligung bis",
        "auto": True,
        "kind": "date",
        "width": 13,
        "formula": '=IF($'"{Z.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.end_date}"'$3:$'"{A.end_date}"'${MAX},'
                   'MATCH($'"{Z.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),""))',
    },
    {
        "name": "mandate_active",
        "label": "▸ Auftrag aktiv?",
        "status": ["ausgelaufen"],
        "auto": True,
        "width": 14,
        "formula": '=IF($'"{Z.mandate_id}"'{row}="","",'
                   'IF($'"{Z.mandate_end}"'{row}="","aktiv",'
                   'IF($'"{Z.mandate_end}"'{row}>=TODAY(),"aktiv","ausgelaufen")))',
    },
    {
        "name": "mandate_short_code",
        "label": "▸ Kurzzeichen (Kind)",
        "auto": True,
        "width": 16,
        "formula": '=IF($'"{Z.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.short_code}"'$3:$'"{A.short_code}"'${MAX},'
                   'MATCH($'"{Z.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),'
                   '"unbekannt"))',
    },
    {
        "name": "index_person_name",
        "label": "▸ Indexkind (Name)",
        "auto": True,
        "width": 22,
        "formula": '=IF($'"{Z.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.index_person_name}"'$3:'
                   '$'"{A.index_person_name}"'${MAX},'
                   'MATCH($'"{Z.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),'
                   '"unbekannt"))',
    },
    {
        "name": "role_check",
        "label": "▸ Primäre Betreuungsperson?",
        "status": ["fehlt", "doppelt"],
        "auto": True,
        "width": 16,
        # Wegpiraten, 22.09.2026: es gibt immer eine primäre Betreuungsperson, die
        # der KESB gegenüber benannt ist. Ändert nichts an Timesheets oder
        # Rechnung, legt nur fest, wer die Berichte zugeteilt bekommt.
        "formula": '=IF($'"{Z.mandate_id}"'{row}="","",'
                   'IF(COUNTIFS($'"{Z.mandate_id}"'$3:$'"{Z.mandate_id}"'${MAX},'
                   '$'"{Z.mandate_id}"'{row},$'"{Z.role}"'$3:$'"{Z.role}"'${MAX},'
                   '"P")=0,"fehlt",'
                   'IF(COUNTIFS($'"{Z.mandate_id}"'$3:$'"{Z.mandate_id}"'${MAX},'
                   '$'"{Z.mandate_id}"'{row},$'"{Z.role}"'$3:$'"{Z.role}"'${MAX},'
                   '"P")>1,"doppelt","ok")))',
    },
    {
        "name": "primary_mandate_id",
        "label": "▸ Auftrag, falls primär",
        "auto": True,
        "hidden": True,
        "width": 11,
        # Speist Berichte.assigned_employee_id: ein einfacher MATCH statt einer
        # zweikriterigen Feldformel, die als Matrixformel eingegeben werden müsste.
        "formula": '=IF(AND($'"{Z.mandate_id}"'{row}<>"",$'"{Z.role}"'{row}="P"),'
                   '$'"{Z.mandate_id}"'{row},"")',
    },
]

BERICHTE = [
    {"name": "report_id", "label": "Bericht-Nr", "required": True, "width": 11},
    {"name": "mandate_choice", "label": "Auftrag", "required": True, "width": 13},
    {
        "name": "mandate_id",
        "label": "▸ Auftrag-Nr",
        "auto": True,
        "hidden": True,
        "width": 11,
        # Dasselbe Auswahl-plus-Extraktion-Muster wie Aufträge.predecessor_choice.
        "formula": '=IF($'"{R.mandate_choice}"'{row}="","",'
                   'IF(ISNUMBER(FIND(" ",$'"{R.mandate_choice}"'{row})),'
                   'LEFT($'"{R.mandate_choice}"'{row},'
                   'FIND(" ",$'"{R.mandate_choice}"'{row})-1),'
                   '$'"{R.mandate_choice}"'{row}))',
    },
    {"name": "report_form", "label": "Berichtsform", "width": 16},
    {"name": "due_date", "label": "Fällig am", "kind": "date", "width": 13},
    {"name": "status", "label": "Status", "required": True, "width": 12},
    {"name": "completed_date", "label": "Erledigt am", "kind": "date", "width": 13},
    {"name": "notes", "label": "Bemerkung", "width": 40},
    {
        "name": "index_person_name",
        "label": "▸ Familie / Indexkind",
        "auto": True,
        "width": 24,
        "formula": '=IF($'"{R.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.index_person_name}"'$3:'
                   '$'"{A.index_person_name}"'${MAX},'
                   'MATCH($'"{R.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),'
                   '"unbekannt"))',
    },
    {
        "name": "service_type_name",
        "label": "▸ Leistungsart",
        "auto": True,
        "width": 26,
        "formula": '=IF($'"{R.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.service_type_name}"'$3:'
                   '$'"{A.service_type_name}"'${MAX},'
                   'MATCH($'"{R.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),'
                   '"unbekannt"))',
    },
    {
        "name": "service_requester_id",
        "label": "▸ Leistungsbesteller-Nr",
        "auto": True,
        "hidden": True,
        "width": 13,
        "formula": '=IF($'"{R.mandate_id}"'{row}="","",IFERROR(INDEX('
                   'Aufträge!$'"{A.service_requester_id}"'$3:'
                   '$'"{A.service_requester_id}"'${MAX},'
                   'MATCH($'"{R.mandate_id}"'{row},'
                   'Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},0)),""))',
    },
    {
        "name": "requester_name",
        "label": "▸ Leistungsbesteller",
        "auto": True,
        "width": 30,
        "formula": '=IF($'"{R.service_requester_id}"'{row}="","",IFERROR(INDEX('
                   'Leistungsbesteller!$C$3:$C$200,'
                   'MATCH($'"{R.service_requester_id}"'{row},'
                   'Leistungsbesteller!$B$3:$B$200,0)),"unbekannt"))',
    },
    {
        "name": "assigned_employee_id",
        "label": "▸ Zuständig (Nr)",
        "auto": True,
        "hidden": True,
        "width": 12,
        # Die primäre Betreuungsperson (Rolle P) des Auftrags, aus Zuordnung MA.
        # Leer, solange dort niemand als P markiert ist – siehe role_check dort.
        "formula": '=IF($'"{R.mandate_id}"'{row}="","",IFERROR(INDEX('
                   '\'Zuordnung MA\'!$'"{Z.employee_id}"'$3:'
                   '$'"{Z.employee_id}"'${MAX},'
                   'MATCH($'"{R.mandate_id}"'{row},'
                   '\'Zuordnung MA\'!$'"{Z.primary_mandate_id}"'$3:'
                   '$'"{Z.primary_mandate_id}"'${MAX},0)),""))',
    },
    {
        "name": "assigned_employee_name",
        "label": "▸ Zuständig",
        "auto": True,
        "width": 22,
        "formula": '=IF($'"{R.assigned_employee_id}"'{row}="","",IFERROR(INDEX('
                   'Mitarbeiter!$D$3:$D$200,MATCH($'"{R.assigned_employee_id}"'{row},'
                   'Mitarbeiter!$B$3:$B$200,0))&", "&INDEX(Mitarbeiter!$C$3:$C$200,'
                   'MATCH($'"{R.assigned_employee_id}"'{row},Mitarbeiter!$B$3:$B$200,0)),'
                   '"unbekannt"))',
    },
    {
        "name": "status_check",
        "label": "▸ Termin im Blick?",
        "status": ["überfällig"],
        "auto": True,
        "width": 16,
        "formula": '=IF($'"{R.report_id}"'{row}="","",'
                   'IF(AND($'"{R.status}"'{row}="offen",$'"{R.due_date}"'{row}<>"",'
                   '$'"{R.due_date}"'{row}<TODAY()),"überfällig",'
                   'IF(AND($'"{R.status}"'{row}="erledigt",'
                   '$'"{R.completed_date}"'{row}=""),"Datum fehlt","ok")))',
    },
]

MODEL.update({"K": KINDER, "A": AUFTRAEGE, "B": BETREUUNGEN,
              "Z": ZUORDNUNG, "P": ANSPRECHPERSONEN, "F": FAMILIEN,
              "R": BERICHTE})


# ------------------------------------------------ Meldungen der einzelnen Zeile
# Dieselben Sachverhalte wie im Blatt Prüfungen, nur zeilenweise statt gezählt.
# Das Blatt Fehlerliste setzt daraus eine durchgehende Liste zusammen.

def _c(pre, field):
    """Zelle der laufenden Zeile."""
    return "${%s.%s}{row}" % (pre, field)


def _r(pre, field):
    """Ganze Datenspalte eines eigenen Blatts als Bereich."""
    blatt = SHEETS[pre]
    q = f"'{blatt}'!" if " " in blatt else f"{blatt}!"
    return "%s${%s.%s}$3:${%s.%s}${MAX}" % (q, pre, field, pre, field)


KINDER += issue_columns(
    "K", _c("K", "person_id"),
    fehler=[
        (f'COUNTIF({_r("K", "person_id")},{_c("K", "person_id")})>1',
         "Kind-Nr doppelt vergeben"),
        (f'AND({_c("K", "family_id")}<>"",'
         f'COUNTIF({_r("F", "family_id")},{_c("K", "family_id")})=0)',
         "Familie gibt es im Blatt Familien nicht"),
    ],
    hinweise=[
        (f'{_c("K", "short_code_check")}="fehlt"', "Kurzzeichen fehlt"),
        (f'{_c("K", "short_code_check")}="doppelt"',
         "Kurzzeichen ist doppelt vergeben"),
        (f'{_c("K", "spelling_check")}="Schreibweise prüfen"',
         "Codewert weicht in der Schreibweise von der Werteliste ab"),
        (f'AND({_c("K", "social_security_number")}<>"",'
         f'{_c("K", "social_security_number")}<>"Privat",'
         f'COUNTIF({_r("K", "social_security_number")},'
         f'{_c("K", "social_security_number")})>1)',
         "AHV-Nummer steht bei mehreren Kindern"),
        (f'AND({_c("K", "care_count_total")}>0,'
         f'OR({_c("K", "date_of_birth")}="",{_c("K", "gender")}="",'
         f'{_c("K", "uma_umf")}="",{_c("K", "canton_of_residence")}=""))',
         "Accordix-Pflichtfeld fehlt: Geburtsdatum, Geschlecht, UMA/UMF oder Wohnkanton"),
        (f'{_c("K", "care_count_total")}=0', "Kind ohne jede Betreuung"),
    ])

AUFTRAEGE += issue_columns(
    "A", _c("A", "mandate_id"),
    fehler=[
        (f'COUNTIF({_r("A", "mandate_id")},{_c("A", "mandate_id")})>1',
         "Auftrag-Nr doppelt vergeben"),
        (f'{_c("A", "index_person_id")}=""', "Auftrag ohne Indexkind"),
        (f'{_c("A", "family_check")}="Geschwister ohne Familie"',
         "Mehrere Kinder im Auftrag, aber keine Familie gesetzt"),
        (f'{_c("A", "person_count_total")}=0', "Auftrag ohne jede Betreuung"),
        (f'{_c("A", "application_number_check")}="fehlt"', "Geschäftsnummer fehlt"),
        (f'{_c("A", "application_number_check")}="Notation"',
         "Geschäftsnummer beim Kostenträger P1000 entspricht nicht yymmddnnn"),
        (f'{_c("A", "application_number_check")}="Datum ungültig"',
         "Geschäftsnummer beim Kostenträger P1000 enthält ein Datum, das es nicht gibt"),
        (f'AND({_c("A", "predecessor_mandate_id")}<>"",'
         f'COUNTIF({_r("A", "mandate_id")},'
         f'{_c("A", "predecessor_mandate_id")})=0)',
         "Vorgängerauftrag gibt es nicht"),
        (f'{_c("A", "predecessor_mandate_id")}={_c("A", "mandate_id")}',
         "Auftrag ist sein eigener Vorgänger"),
        (f'AND({_c("A", "predecessor_mandate_id")}<>"",'
         f'COUNTIF({_r("A", "predecessor_mandate_id")},'
         f'{_c("A", "predecessor_mandate_id")})>1)',
         "Derselbe Vorgänger steht bei zwei Aufträgen"),
        (f'AND({_c("A", "contact_person_id")}<>"",'
         f'COUNTIF({_r("P", "contact_person_id")},'
         f'{_c("A", "contact_person_id")})=0)',
         "Ansprechperson-Nr gibt es nicht"),
        (f'AND({_c("A", "contact_person_id")}<>"",'
         f'COUNTIF({_r("P", "contact_person_id")},'
         f'{_c("A", "contact_person_id")})>0,'
         f'COUNTIFS({_r("P", "contact_person_id")},{_c("A", "contact_person_id")},'
         f'{_r("P", "service_requester_id")},'
         f'{_c("A", "service_requester_id")})=0)',
         "Ansprechperson gehört zu einem anderen Leistungsbesteller"),
        (f'{_c("A", "service_type_check")}="Leistungsart unbekannt"',
         "Leistungsart gibt es im Blatt Leistungstypen nicht"),
    ],
    hinweise=[
        (f'{_c("A", "family_check")}="mehrere Familien"',
         "Der Auftrag betreut Kinder aus mehreren Familien"),
        (f'{_c("A", "contact_person_id")}=""', "Auftrag ohne Ansprechperson"),
        (f'{_c("A", "service_type_check")}="Leistungsart ausgelaufen"',
         "Die Leistungsart ist ausgelaufen, der Auftrag läuft weiter"),
        (f'{_c("A", "quota_check")}="indirekt prüfen"',
         "Kontingent indirekt ist mehr als die Hälfte des direkten"),
        (f'{_c("A", "spelling_check")}="Schreibweise prüfen"',
         "Zuweisungsgrundlage weicht in der Schreibweise von der Werteliste ab"),
        (f'AND({_c("A", "end_date")}<>"",{_c("A", "end_date")}<TODAY(),'
         f'COUNTIFS({_r("B", "mandate_id")},{_c("A", "mandate_id")},'
         f'{_r("B", "end_date")},"")>0)',
         "Bewilligung abgelaufen, aber eine Betreuung ist noch offen"),
    ])

BETREUUNGEN += issue_columns(
    "B", _c("B", "mandate_id"),
    fehler=[
        (f'COUNTIFS({_r("B", "mandate_id")},{_c("B", "mandate_id")},'
         f'{_r("B", "person_id")},{_c("B", "person_id")})>1',
         "Diese Betreuung ist zweimal erfasst"),
        (f'COUNTIF({_r("A", "mandate_id")},{_c("B", "mandate_id")})=0',
         "Auftrag-Nr gibt es nicht"),
        (f'OR({_c("B", "person_id")}="",'
         f'COUNTIF({_r("K", "person_id")},{_c("B", "person_id")})=0)',
         "Kind-Nr fehlt oder gibt es nicht"),
    ],
    hinweise=[
        (f'{_c("B", "overlap_check")}="Überschneidung"',
         "Überschneidung mit einem zweiten Auftrag derselben Leistungsart"),
        (f'{_c("B", "entry_vs_mandate")}="Auftrag älter als der Eintritt"',
         "Der Auftrag beginnt vor dem Eintritt dieses Kindes"),
        (f'{_c("B", "entry_chain_check")}="Eintritt aus Vorgänger übernehmen"',
         "Folgeauftrag: der Eintritt wurde nicht aus dem Vorgänger übernommen"),
        (f'AND({_c("B", "end_date")}<>"",{_c("B", "leaving_reason")}="")',
         "Austritt erfasst, aber kein Austrittsgrund"),
        (f'{_c("B", "spelling_check")}="Schreibweise prüfen"',
         "Austrittsgrund oder Situation nach Austritt weicht in der Schreibweise ab"),
    ])

ZUORDNUNG += issue_columns(
    "Z", _c("Z", "mandate_id"),
    fehler=[
        (f'COUNTIF({_r("A", "mandate_id")},{_c("Z", "mandate_id")})=0',
         "Auftrag-Nr gibt es nicht"),
        (f'OR({_c("Z", "employee_id")}="",'
         f'COUNTIF(Mitarbeiter!$B$3:$B$200,{_c("Z", "employee_id")})=0)',
         "Mitarbeiter-Nr fehlt oder gibt es nicht"),
        (f'COUNTIFS({_r("Z", "mandate_id")},{_c("Z", "mandate_id")},'
         f'{_r("Z", "employee_id")},{_c("Z", "employee_id")})>1',
         "Diese Zuordnung ist zweimal erfasst"),
    ],
    hinweise=[
        (f'{_c("Z", "mandate_active")}="ausgelaufen"',
         "Der Auftrag ist ausgelaufen – aus dieser Zeile entsteht kein Erfassungsbogen mehr"),
        (f'{_c("Z", "role_check")}="fehlt"',
         "Für diesen Auftrag ist niemand als primäre Betreuungsperson (P) markiert"),
        (f'{_c("Z", "role_check")}="doppelt"',
         "Für diesen Auftrag ist mehr als eine primäre Betreuungsperson (P) markiert"),
    ])

FAMILIEN += issue_columns(
    "F", _c("F", "family_id"),
    fehler=[
        (f'COUNTIF({_r("F", "family_id")},{_c("F", "family_id")})>1',
         "Familie doppelt angelegt"),
        (f'{_c("F", "index_check")}="fehlt"', "Familie ohne Indexkind"),
        (f'{_c("F", "index_check")}="gehört nicht zu dieser Familie"',
         "Das Indexkind steht im Blatt Kinder bei einer anderen Familie"),
    ],
    hinweise=[
        (f'{_c("F", "index_check")}="nicht das jüngste Kind"',
         "Das Indexkind ist nicht das jüngste Kind der Familie"),
        (f'{_c("F", "index_check")}="ohne Kinder"',
         "Keinem Kind ist diese Familie zugeordnet – die Zeile kann gelöscht werden"),
    ])

ANSPRECHPERSONEN += issue_columns(
    "P", _c("P", "contact_person_id"),
    fehler=[
        (f'COUNTIF({_r("P", "contact_person_id")},'
         f'{_c("P", "contact_person_id")})>1', "AP-Nr doppelt vergeben"),
        (f'COUNTIF(Leistungsbesteller!$B$3:$B$200,'
         f'{_c("P", "service_requester_id")})=0',
         "Leistungsbesteller gibt es nicht"),
    ],
    hinweise=[
        (f'{_c("P", "mandate_count")}=0',
         "Ansprechperson ohne Auftrag – nicht mehr zuständig?"),
    ])

BERICHTE += issue_columns(
    "R", _c("R", "report_id"),
    fehler=[
        (f'COUNTIF({_r("R", "report_id")},{_c("R", "report_id")})>1',
         "Bericht-Nr doppelt vergeben"),
        (f'AND({_c("R", "mandate_id")}<>"",'
         f'COUNTIF({_r("A", "mandate_id")},{_c("R", "mandate_id")})=0)',
         "Auftrag gibt es nicht"),
    ],
    hinweise=[
        (f'{_c("R", "status_check")}="überfällig"',
         "Fällig-Datum liegt in der Vergangenheit, Status noch offen"),
        (f'{_c("R", "status_check")}="Datum fehlt"',
         "Als erledigt markiert, aber kein Erledigt-am-Datum erfasst"),
        (f'AND({_c("R", "mandate_id")}<>"",{_c("R", "assigned_employee_id")}="")',
         "Für diesen Auftrag ist niemand als primäre Betreuungsperson (P) "
         "markiert – Zuordnung MA ergänzen"),
    ])

guard_all_lookups()


# ---------------------------------------------------------------- Leistungsarten

ST_ENDE = {   # Zeitscheiben, die mit dem Nachfolger zum 01.01.2026 geschlossen wurden
    "ST01_alt": datetime(2025, 12, 31),
    "ST02_alt": datetime(2025, 12, 31),
}

# Gespiegelt aus src/shared_modules/accordix.py (SERVICE_TYPE_MAP). Bei einer
# Änderung dort auch hier nachziehen – die Meldung selbst läuft am code vorbei
# an dieser Datei, dieser Check ist nur die Frühwarnung im Workbook.
ST_ACCORDIX_CODES = (
    "SPF", "UWB  (Ausübung Gruppe)", "UWB (Übergabe Gruppe)",
    "UWB (Begleitung Individuell)", "DAF L",
)
# code-Werte, die Wegpiraten bewusst nicht an Accordix meldet (siehe
# docs/accordix_mapping.md, Abschnitt Leistungsarten-Mapping).
ST_ACCORDIX_AUSGESCHLOSSEN = (
    "PRIVAT", "SONST", "Jugendcoaching", "Abklärung", "med./therap. Bericht",
)


def extend_leistungstypen(wb):
    """to_date ergänzen und eine gefilterte Auswahlliste danebenlegen.

    Die Zeitscheibe steckte bisher im Schlüssel (ST01 / ST01_alt). Umbenennen ist
    nicht gratis: clients.service_type zeigt auf die service_type_id, service_data
    und die archivierten Erfassungsbögen tragen den code. Deshalb bleiben beide
    stehen, und die Gültigkeit steht in from_date/to_date – die Rechnungsabfrage
    löst über code + from_date ohnehin schon so auf.
    """
    ws = wb["Leistungstypen"]
    alt = ws.tables["service_types"]
    stil = alt.tableStyleInfo
    del ws.tables["service_types"]

    ws.insert_cols(8)
    vorbild = ws.cell(row=1, column=7)
    kopf = ws.cell(row=1, column=8, value="to_date")
    for attr in ("font", "fill", "border", "alignment"):
        setattr(kopf, attr, copy.copy(getattr(vorbild, attr)))
    ws.column_dimensions["H"].width = 13

    last = 1
    for row in range(2, ws.max_row + 1):
        stid = ws.cell(row=row, column=1).value
        if not stid:
            continue
        last = row
        zelle = ws.cell(row=row, column=8)
        zelle.number_format = "DD.MM.YYYY"
        if stid in ST_ENDE:
            zelle.value = ST_ENDE[stid]

    neu = Table(displayName="service_types", ref=f"A1:I{last}")
    neu.tableStyleInfo = stil
    ws.add_table(neu)

    for col, label, breite, versteckt in [
        (11, "▸ aktuell?", 13, False),
        (12, "▸ Rang", 8, True),
        (13, "▸ Auswahl", 12, True),
        (14, "▸ Accordix-Meldung", 18, False),
    ]:
        zelle = ws.cell(row=1, column=col, value=label)
        zelle.font = Font(name=FONT, size=10, bold=True, italic=True)
        zelle.fill = PatternFill("solid", fgColor=C_AUTO)
        zelle.border = BORDER
        letter = get_column_letter(col)
        ws.column_dimensions[letter].width = breite
        ws.column_dimensions[letter].hidden = versteckt

    for row in range(2, ST_MAX + 1):
        ws.cell(row=row, column=11).value = (
            f'=IF($A{row}="","",IF(AND(N($G{row})<=TODAY(),'
            f'OR($H{row}="",N($H{row})>=TODAY())),"aktuell","ausgelaufen"))')
        ws.cell(row=row, column=12).value = (
            f'=IF($K{row}="aktuell",COUNTIF($K$2:$K{row},"aktuell"),"")')
        ws.cell(row=row, column=13).value = (
            f'=IFERROR(INDEX($A$2:$A${ST_MAX},MATCH(ROW()-1,$L$2:$L${ST_MAX},0))&"","")')
        ws.cell(row=row, column=14).value = (
            f'=IF($A{row}="","",IF(SUMPRODUCT(--($B{row}={_array(ST_ACCORDIX_CODES)}))>0,'
            f'"meldepflichtig",IF(SUMPRODUCT(--($B{row}='
            f'{_array(ST_ACCORDIX_AUSGESCHLOSSEN)}))>0,"nicht meldepflichtig",'
            f'"kein Mapping – prüfen")))')
        for col in (11, 12, 13, 14):
            zelle = ws.cell(row=row, column=col)
            zelle.font = Font(name=FONT, size=10, italic=True, color="595959")
            zelle.fill = PatternFill("solid", fgColor=C_AUTO)

    ws.conditional_formatting.add(
        f"K2:K{ST_MAX}",
        FormulaRule(formula=['$K2="ausgelaufen"'],
                    fill=PatternFill("solid", fgColor=C_HINT)))
    ws.conditional_formatting.add(
        f"N2:N{ST_MAX}",
        FormulaRule(formula=['$N2="kein Mapping – prüfen"'],
                    fill=PatternFill("solid", fgColor=C_BAD)))


# ------------------------------------------------------------------ Wertelisten

WERTELISTEN = [
    ("gender", "Geschlecht", ["m", "w", "d"]),
    ("uma_umf", "UMA/UMF", ["Ja", "Nein", "Unbekannt"]),
    ("spoken_language", "Hauptsprache", ["DE", "FR"]),
    (
        "canton_of_residence",
        "Wohnkanton",
        ["AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU", "LU", "NE",
         "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR", "VD", "VS", "ZG", "ZH",
         "Ausland"],
    ),
    (
        "allocation",
        "Zuweisungsgrundlage",
        ["Einvernehmlich über Sozialdienst", "KESB (zusammen mit Gericht)", "Jugendanwaltschaft"],
    ),
    (
        "leaving_reason",
        "Austrittsgrund",
        ["Abbruch durch Sorgeberechtigte/Leistungsempfänger",
         "Abbruch durch Leistungsbesteller (KESB, Sozialdienst, Jugendanwaltschaft)",
         "Abbruch durch KESB aufgrund Volljährigkeit",
         "Abbruch durch Leistungserbringer aufgrund Konfliktsituationen",
         "Abbruch durch Leistungserbringer aufgrund kurzfristig notwendigen Wechsels "
         "des Leistungsangebots",
         "Anderer"],
    ),
    (
        "after_leave_situation",
        "Situation nach Austritt",
        ["weitere ambulante Leistung bei aktuellem Leistungserbringer",
         "weitere ambulante Leistung bei anderem Leistungserbringer",
         "stationäre Einrichtung", "Pflegefamilie", "keine weitere Leistung", "andere"],
    ),
    ("anrede", "Anrede", ["Frau", "Herr"]),
    ("ja_nein", "Ja / Nein", ["Ja", "Nein"]),
    ("rolle", "Rolle (P/S)", ["P", "S"]),
    ("berichtsrhythmus", "Rhythmus", ["einmalig", "periodisch", "ereignisbezogen"]),
    ("berichtsform", "Berichtsform", ["Bericht", "Zwischenbericht", "Abschlussbericht"]),
    ("berichtsstatus", "Status", ["offen", "erledigt", "entfällt"]),
]


def build_wertelisten(wb):
    if "Wertelisten" in wb.sheetnames:
        del wb["Wertelisten"]
    ws = wb.create_sheet("Wertelisten")
    ws.sheet_properties.tabColor = "BFBFBF"

    col = 1
    for tech, label, values in WERTELISTEN:
        letter = get_column_letter(col)
        head = ws.cell(row=1, column=col, value=label)
        head.font = Font(name=FONT, size=10, bold=True)
        head.fill = PatternFill("solid", fgColor=C_LABEL)
        tech_cell = ws.cell(row=2, column=col, value=tech)
        tech_cell.font = Font(name=FONT, size=10, bold=True)
        tech_cell.fill = PatternFill("solid", fgColor=C_TECH)
        for i, value in enumerate(values):
            cell = ws.cell(row=3 + i, column=col, value=value)
            cell.font = Font(name=FONT, size=10)
            cell.border = BORDER
        ws.column_dimensions[letter].width = max(12, min(48, max(len(v) for v in values) + 2))
        last = 2 + len(values)
        table = Table(displayName=f"wl_{tech}", ref=f"{letter}2:{letter}{last}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleLight11", showRowStripes=True)
        ws.add_table(table)
        col += 2

    ws.freeze_panes = "A3"
    protect(ws)


# ------------------------------------------------------------------- Prüfungen

CHECKS = [
    ("Fehler", "Kind-Nr doppelt vergeben",
     "Jede Kind-Nr darf nur einmal vorkommen.",
     '=SUMPRODUCT((Kinder!${K.person_id}$3:${K.person_id}${MAX}<>"")'
     '*(COUNTIF(Kinder!${K.person_id}$3:${K.person_id}${MAX},'
     'Kinder!${K.person_id}$3:${K.person_id}${MAX})>1))'),
    ("Fehler", "Auftrag-Nr doppelt vergeben",
     "Jede Auftrag-Nr darf nur einmal vorkommen.",
     '=SUMPRODUCT((Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX}<>"")'
     '*(COUNTIF(Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX},'
     'Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX})>1))'),
    ("Fehler", "Dieselbe Betreuung zweimal erfasst",
     "Auftrag-Nr und Kind-Nr zusammen dürfen nur einmal vorkommen.",
     '=SUMPRODUCT((Betreuungen!${B.mandate_id}$3:${B.mandate_id}${MAX}<>"")'
     '*(COUNTIFS(Betreuungen!${B.mandate_id}$3:${B.mandate_id}${MAX},'
     'Betreuungen!${B.mandate_id}$3:${B.mandate_id}${MAX},'
     'Betreuungen!${B.person_id}$3:${B.person_id}${MAX},'
     'Betreuungen!${B.person_id}$3:${B.person_id}${MAX})>1))'),
    ("Fehler", "Betreuung verweist auf einen Auftrag, den es nicht gibt",
     "Die Zeile fehlt sonst in der Accordix-Meldung.",
     '=SUMPRODUCT((Betreuungen!${B.mandate_id}$3:${B.mandate_id}${MAX}<>"")'
     '*(COUNTIF(Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX},'
     'Betreuungen!${B.mandate_id}$3:${B.mandate_id}${MAX})=0))'),
    ("Fehler", "Betreuung verweist auf ein Kind, das es nicht gibt",
     "Die Zeile fehlt sonst in der Accordix-Meldung.",
     '=SUMPRODUCT((Betreuungen!${B.person_id}$3:${B.person_id}${MAX}<>"")'
     '*(COUNTIF(Kinder!${K.person_id}$3:${K.person_id}${MAX},'
     'Betreuungen!${B.person_id}$3:${B.person_id}${MAX})=0))'),
    ("Fehler", "Auftrag ohne Indexkind",
     "Ohne Indexkind entsteht keine Rechnung.",
     '=SUMPRODUCT((Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX}<>"")'
     '*(Aufträge!${A.index_person_id}$3:${A.index_person_id}${MAX}=""))'),
    ("Fehler", "Kind zeigt auf eine Familie, die es nicht gibt",
     "Das Feld darf leer bleiben – dann ist das Kind selbst das Indexkind. "
     "Steht etwas drin, muss es im Blatt Familien stehen.",
     '=SUMPRODUCT((Kinder!${K.family_id}$3:${K.family_id}${MAX}<>"")'
     '*(COUNTIF(Familien!${F.family_id}$3:${F.family_id}${MAX},'
     'Kinder!${K.family_id}$3:${K.family_id}${MAX})=0))'),
    ("Fehler", "Auftrag betreut Geschwister, aber ohne Familie",
     "Bei mehr als einem Kind im Auftrag ist ohne Familie nicht bestimmt, über "
     "welches Kind abgerechnet wird. Dann eine Familie anlegen, beide Kinder "
     "eintragen und dort das jüngste als Indexkind setzen.",
     '=COUNTIF(Aufträge!${A.family_check}$3:${A.family_check}${MAX},'
     '"Geschwister ohne Familie")'),
    ("Fehler", "Familie ohne Indexkind",
     "Je Familie ein Kind, über das abgerechnet wird – das jüngste.",
     '=COUNTIF(Familien!${F.index_check}$3:${F.index_check}${MAX},"fehlt")'),
    ("Fehler", "Indexkind gehört nicht zu seiner Familie",
     "Das eingetragene Kind steht im Blatt Kinder bei einer anderen Familie.",
     '=COUNTIF(Familien!${F.index_check}$3:${F.index_check}${MAX},'
     '"gehört nicht zu dieser Familie")'),
    ("Fehler", "Auftrag ohne jede Betreuung",
     "Ein Auftrag, in dem kein Kind betreut wird, ist unvollständig erfasst.",
     '=SUMPRODUCT((Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX}<>"")'
     '*(COUNTIF(Betreuungen!${B.mandate_id}$3:${B.mandate_id}${MAX},'
     'Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX})=0))'),
    ("Fehler", "Vorgängerauftrag zeigt auf einen Auftrag, den es nicht gibt",
     "Tippfehler in der Auftragskette.",
     '=SUMPRODUCT((Aufträge!${A.predecessor_mandate_id}$3:'
     '${A.predecessor_mandate_id}${MAX}<>"")'
     '*(COUNTIF(Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX},'
     'Aufträge!${A.predecessor_mandate_id}$3:${A.predecessor_mandate_id}${MAX})=0))'),
    ("Fehler", "Auftrag ist sein eigener Vorgänger",
     "Die Kette würde sich im Kreis drehen.",
     '=SUMPRODUCT((Aufträge!${A.predecessor_mandate_id}$3:'
     '${A.predecessor_mandate_id}${MAX}<>"")'
     '*(Aufträge!${A.predecessor_mandate_id}$3:${A.predecessor_mandate_id}${MAX}='
     'Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX}))'),
    ("Fehler", "Zwei Aufträge haben denselben Vorgänger",
     "Eine Auftragskette darf sich nicht verzweigen – sonst ist »Nachfolgeauftrag« "
     "nicht mehr eindeutig.",
     '=SUMPRODUCT((Aufträge!${A.predecessor_mandate_id}$3:'
     '${A.predecessor_mandate_id}${MAX}<>"")'
     '*(COUNTIF(Aufträge!${A.predecessor_mandate_id}$3:'
     '${A.predecessor_mandate_id}${MAX},'
     'Aufträge!${A.predecessor_mandate_id}$3:'
     '${A.predecessor_mandate_id}${MAX})>1))'),
    ("Fehler", "Ansprechperson-Nr gibt es nicht",
     "Abgleich gegen das Blatt Ansprechpersonen.",
     '=SUMPRODUCT((Aufträge!${A.contact_person_id}$3:${A.contact_person_id}${MAX}<>"")'
     '*(COUNTIF(Ansprechpersonen!${P.contact_person_id}$3:'
     '${P.contact_person_id}${MAX},'
     'Aufträge!${A.contact_person_id}$3:${A.contact_person_id}${MAX})=0))'),
    ("Fehler", "Ansprechperson gehört zu einem anderen Leistungsbesteller",
     "Die Anrede auf der Rechnung ginge an die falsche Stelle.",
     '=SUMPRODUCT((Aufträge!${A.contact_person_id}$3:${A.contact_person_id}${MAX}<>"")'
     '*(COUNTIF(Ansprechpersonen!${P.contact_person_id}$3:'
     '${P.contact_person_id}${MAX},'
     'Aufträge!${A.contact_person_id}$3:${A.contact_person_id}${MAX})>0)'
     '*(COUNTIFS(Ansprechpersonen!${P.contact_person_id}$3:'
     '${P.contact_person_id}${MAX},'
     'Aufträge!${A.contact_person_id}$3:${A.contact_person_id}${MAX},'
     'Ansprechpersonen!${P.service_requester_id}$3:${P.service_requester_id}${MAX},'
     'Aufträge!${A.service_requester_id}$3:${A.service_requester_id}${MAX})=0))'),
    ("Fehler", "Mitarbeiterzuordnung auf einen Auftrag, den es nicht gibt",
     "Für diesen Auftrag entsteht kein Erfassungsbogen.",
     '=SUMPRODUCT((\'Zuordnung MA\'!${Z.mandate_id}$3:${Z.mandate_id}${MAX}<>"")'
     '*(COUNTIF(Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX},'
     '\'Zuordnung MA\'!${Z.mandate_id}$3:${Z.mandate_id}${MAX})=0))'),
    ("Fehler", "Mitarbeiter-Nr in der Zuordnung ist unbekannt",
     "Abgleich gegen das Blatt Mitarbeiter.",
     '=SUMPRODUCT((\'Zuordnung MA\'!${Z.employee_id}$3:${Z.employee_id}${MAX}<>"")'
     '*(COUNTIF(Mitarbeiter!$B$3:$B$200,'
     '\'Zuordnung MA\'!${Z.employee_id}$3:${Z.employee_id}${MAX})=0))'),
    ("Fehler", "Geschäftsnummer fehlt",
     "Ohne Geschäftsnummer lässt sich der Auftrag nicht zuordnen. Bei Kostenträgern "
     "ausser P1000 genügt Freitext, z.B. die Nummer der KESB.",
     '=COUNTIF(Aufträge!${A.application_number_check}$3:'
     '${A.application_number_check}${MAX},"fehlt")'),
    ("Fehler", "Geschäftsnummer beim KJA (P1000) entspricht nicht yymmddnnn",
     "Beim Kantonalen Jugendamt ist die Nummer verbindlich neun Ziffern: Jahr, Monat, "
     "Tag des Auftragsdatums (nicht der Bewilligung), dann die laufende Nummer, z.B. "
     "260819008. Texte wie »brief«, »beendet« oder »Sonderfall« gehören nicht ins Feld.",
     '=COUNTIF(Aufträge!${A.application_number_check}$3:'
     '${A.application_number_check}${MAX},"Notation")'),
    ("Fehler", "Geschäftsnummer beim KJA (P1000) enthält ein Datum, das es nicht gibt",
     "Die Ziffern 3 bis 6 sind Monat und Tag, z.B. ist 260631002 ein 31. Juni.",
     '=COUNTIF(Aufträge!${A.application_number_check}$3:'
     '${A.application_number_check}${MAX},"Datum ungültig")'),
    ("Fehler", "Leistungsart des Auftrags gibt es nicht",
     "Abgleich gegen das Blatt Leistungstypen.",
     '=COUNTIF(Aufträge!${A.service_type_check}$3:${A.service_type_check}${MAX},'
     '"Leistungsart unbekannt")'),
    ("Hinweis", "Laufender Auftrag mit ausgelaufener Leistungsart",
     "Die Zeitscheibe der Leistungsart ist zu Ende (Spalte to_date), der Auftrag "
     "läuft weiter. Entweder gilt der alte Ansatz noch – dann to_date verlängern – "
     "oder der Auftrag gehört auf die neue Leistungsart umgestellt.",
     '=COUNTIF(Aufträge!${A.service_type_check}$3:${A.service_type_check}${MAX},'
     '"Leistungsart ausgelaufen")'),
    ("Hinweis", "Indexkind ist nicht das jüngste Kind der Familie",
     "Die Regel lautet: über das jüngste Kind. Bei Patchwork-Konstellationen kann "
     "eine andere Wahl richtig sein – dann bleibt der Hinweis stehen.",
     '=COUNTIF(Familien!${F.index_check}$3:${F.index_check}${MAX},'
     '"nicht das jüngste Kind")'),
    ("Hinweis", "Familie ohne Kinder",
     "Bleibt übrig, wenn zwei Familien zusammengelegt wurden: die Kinder tragen "
     "jetzt die andere Nummer. Die leere Zeile kann gelöscht werden.",
     '=COUNTIF(Familien!${F.index_check}$3:${F.index_check}${MAX},"ohne Kinder")'),
    ("Hinweis", "Auftrag betreut Kinder aus mehreren Familien",
     "Dann ist unklar, über welche Familie abgerechnet wird. Entweder gehören die "
     "Kinder doch zu einer Familie, oder es sind zwei Aufträge.",
     '=COUNTIF(Aufträge!${A.family_check}$3:${A.family_check}${MAX},'
     '"mehrere Familien")'),
    ("Hinweis", "Kurzzeichen fehlt oder ist doppelt vergeben",
     "Das Kurzzeichen steht im Erfassungsbogen und im Dateinamen. Zwei Kinder mit "
     "demselben Kurzzeichen sind dort nicht mehr auseinanderzuhalten – an die "
     "Rohform eine Ziffer anhängen (MaSt, MaSt2, MaSt3).",
     '=COUNTIF(Kinder!${K.short_code_check}$3:${K.short_code_check}${MAX},"doppelt")'
     '+COUNTIF(Kinder!${K.short_code_check}$3:${K.short_code_check}${MAX},"fehlt")'),
    ("Hinweis", "Auftrag ohne Ansprechperson",
     "Die Rechnung bekommt dann keine persönliche Anrede.",
     '=SUMPRODUCT((Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX}<>"")'
     '*(Aufträge!${A.contact_person_id}$3:${A.contact_person_id}${MAX}=""))'),
    ("Hinweis", "Dieselbe AHV-Nummer bei mehreren Kindern",
     "Entweder ist ein Kind doppelt angelegt, oder eine AHV-Nummer ist falsch erfasst.",
     '=SUMPRODUCT((Kinder!${K.social_security_number}$3:'
     '${K.social_security_number}${MAX}<>"")'
     '*(Kinder!${K.social_security_number}$3:'
     '${K.social_security_number}${MAX}<>"Privat")'
     '*(COUNTIF(Kinder!${K.social_security_number}$3:'
     '${K.social_security_number}${MAX},'
     'Kinder!${K.social_security_number}$3:'
     '${K.social_security_number}${MAX})>1))'),
    ("Hinweis", "Kind ohne jede Betreuung",
     "Erfasst, aber nirgends zugeordnet — fehlt in der Accordix-Meldung.",
     '=SUMPRODUCT((Kinder!${K.person_id}$3:${K.person_id}${MAX}<>"")'
     '*(COUNTIF(Betreuungen!${B.person_id}$3:${B.person_id}${MAX},'
     'Kinder!${K.person_id}$3:${K.person_id}${MAX})=0))'),
    ("Hinweis", "Austritt erfasst, aber kein Austrittsgrund",
     "Accordix erwartet zum Austritt auch den Grund.",
     '=SUMPRODUCT((Betreuungen!${B.end_date}$3:${B.end_date}${MAX}<>"")'
     '*(Betreuungen!${B.leaving_reason}$3:${B.leaving_reason}${MAX}=""))'),
    ("Hinweis", "Accordix-Pflichtfeld fehlt bei einem betreuten Kind",
     "Geburtsdatum, Geschlecht, UMA/UMF und Wohnkanton sind Pflicht.",
     '=SUMPRODUCT((Kinder!${K.person_id}$3:${K.person_id}${MAX}<>"")'
     '*(COUNTIF(Betreuungen!${B.person_id}$3:${B.person_id}${MAX},'
     'Kinder!${K.person_id}$3:${K.person_id}${MAX})>0)'
     '*(((Kinder!${K.date_of_birth}$3:${K.date_of_birth}${MAX}="")'
     '+(Kinder!${K.gender}$3:${K.gender}${MAX}="")'
     '+(Kinder!${K.uma_umf}$3:${K.uma_umf}${MAX}="")'
     '+(Kinder!${K.canton_of_residence}$3:${K.canton_of_residence}${MAX}=""))>0))'),
    ("Hinweis", "Schreibweise eines Codewerts weicht von der Werteliste ab",
     "Accordix vergleicht buchstabengetreu: »Keine weitere Leistung« wird abgewiesen, "
     "richtig ist »keine weitere Leistung«. Betroffene Zellen sind rot hinterlegt.",
     '=COUNTIF(Kinder!${K.spelling_check}$3:${K.spelling_check}${MAX},'
     '"Schreibweise prüfen")'
     '+COUNTIF(Aufträge!${A.spelling_check}$3:${A.spelling_check}${MAX},'
     '"Schreibweise prüfen")'
     '+COUNTIF(Betreuungen!${B.spelling_check}$3:${B.spelling_check}${MAX},'
     '"Schreibweise prüfen")'),
    ("Hinweis", "Bewilligung abgelaufen, Betreuung noch offen",
     "Entweder wurde verlängert und der Auftrag ist nicht nachgeführt, oder der "
     "Austritt fehlt.",
     '=SUMPRODUCT((Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX}<>"")'
     '*(Aufträge!${A.end_date}$3:${A.end_date}${MAX}<>"")'
     '*(Aufträge!${A.end_date}$3:${A.end_date}${MAX}<TODAY())'
     '*(COUNTIFS(Betreuungen!${B.mandate_id}$3:${B.mandate_id}${MAX},'
     'Aufträge!${A.mandate_id}$3:${A.mandate_id}${MAX},'
     'Betreuungen!${B.end_date}$3:${B.end_date}${MAX},"")>0))'),
    ("Hinweis", "Zwei Aufträge derselben Leistungsart überschneiden sich beim selben Kind",
     "Bei einer Verlängerung gehört der neue Auftrag hinter den alten, nicht daneben: "
     "»Bewilligung von« des Folgeauftrags nach »Bewilligung bis« des Vorgängers, und "
     "der Vorgänger eingetragen. Läuft wirklich zweimal dieselbe Leistung parallel, "
     "ist der Hinweis richtig und bleibt stehen.",
     '=COUNTIF(Betreuungen!${B.overlap_check}$3:${B.overlap_check}${MAX},'
     '"Überschneidung")'),
    ("Hinweis", "Mitarbeiterzuordnung auf einen ausgelaufenen Auftrag",
     "Aus der Zuordnung entstehen die Erfassungsbögen. Ist der Auftrag abgelaufen, "
     "gehört die Zeile entfernt – oder der Auftrag verlängert.",
     '=COUNTIF(\'Zuordnung MA\'!${Z.mandate_active}$3:${Z.mandate_active}${MAX},'
     '"ausgelaufen")'),
    ("Hinweis", "Auftrag beginnt vor dem Eintritt des Kindes",
     "Die Bewilligung kann nicht älter sein als die Betreuung dieses Kindes – dann "
     "ist der Eintritt zu spät gesetzt. Verglichen wird monatsgerundet: Eintritt "
     "17.02.2026 verträgt einen Auftrag ab 01.02.2026, bei 01.01.2026 erscheint der "
     "Hinweis. Zwei Ausnahmen sind echt: ein Geschwister, "
     "das später in einen laufenden Auftrag kommt, und eine Bewilligung, die vor "
     "dem tatsächlichen Beginn erteilt wurde.",
     '=COUNTIF(Betreuungen!${B.entry_vs_mandate}$3:${B.entry_vs_mandate}${MAX},'
     '"Auftrag älter als der Eintritt")'),
    ("Hinweis", "Folgeauftrag: Eintritt wurde nicht aus dem Vorgänger übernommen",
     "Der Eintritt ist der Beginn der Betreuung dieses Kindes, nicht der Beginn der "
     "aktuellen Bewilligung. Bei einer Verlängerung bleibt er stehen.",
     '=COUNTIF(Betreuungen!${B.entry_chain_check}$3:${B.entry_chain_check}${MAX},'
     '"Eintritt aus Vorgänger übernehmen")'),
    ("Hinweis", "Auftrag ohne primäre Betreuungsperson",
     "Wegpiraten, 22.09.2026: es gibt immer eine primäre Betreuungsperson, die der "
     "KESB gegenüber benannt ist. In der Zuordnung MA mit Rolle P markieren – "
     "ändert nichts an Timesheet oder Rechnung, legt nur fest, wer die Berichte "
     "zugeteilt bekommt.",
     "=COUNTIF('Zuordnung MA'!${Z.role_check}$3:${Z.role_check}${MAX},"
     '"fehlt")'),
    ("Hinweis", "Mehr als eine primäre Betreuungsperson auf demselben Auftrag",
     "Nur eine Zeile je Auftrag darf Rolle P tragen.",
     "=COUNTIF('Zuordnung MA'!${Z.role_check}$3:${Z.role_check}${MAX},"
     '"doppelt")'),
    ("Hinweis", "Leistungsart ohne Accordix-Zuordnung",
     "Das Blatt Leistungstypen kennt diesen code nicht als meldepflichtig und "
     "nicht als bewusst ausgeschlossen (PRIVAT, SONST, Jugendcoaching, Abklärung, "
     "med./therap. Bericht). Entweder ist der code falsch geschrieben, oder das "
     "Mapping in src/shared_modules/accordix.py fehlt noch.",
     f'=COUNTIF(Leistungstypen!$N$2:$N${ST_MAX},"kein Mapping – prüfen")'),
]


def build_pruefkatalog(wb):
    """Alle Prüfungen mit Anzahl, auch die erledigten; das Blatt Prüfungen zeigt daraus nur die offenen."""
    ws = wb.create_sheet("Prüfkatalog")
    ws.sheet_properties.tabColor = "C00000"

    ws["A1"] = "Prüfkatalog"
    ws["A1"].font = Font(name=FONT, size=14, bold=True)
    ws["A2"] = (
        "Alle Prüfungen, auch die erledigten — der Nachweis, dass sie laufen. "
        "Das Blatt »Prüfungen« zeigt daraus nur, was offen ist."
    )
    ws["A2"].font = Font(name=FONT, size=10, italic=True, color="595959")

    ws["A4"] = "Offene Fehler"
    ws["A4"].font = Font(name=FONT, size=11, bold=True)
    first, last = 7, 6 + len(CHECKS)
    ws["B4"] = f'=SUMPRODUCT(($A${first}:$A${last}="Fehler")*($D${first}:$D${last}>0))'
    ws["B4"].font = Font(name=FONT, size=11, bold=True)
    ws["C4"] = '=IF($B$4=0,"Keine offenen Fehler.","Bitte die Zeilen mit Status ""prüfen"" ansehen.")'
    ws["C4"].font = Font(name=FONT, size=11, bold=True)

    headers = ["Art", "Prüfung", "Was dahintersteckt", "Anzahl", "Status"]
    for idx, text in enumerate(headers, start=1):
        cell = ws.cell(row=6, column=idx, value=text)
        cell.font = Font(name=FONT, size=10, bold=True)
        cell.fill = PatternFill("solid", fgColor=C_TECH)
        cell.border = BORDER

    for offset, (art, titel, erklaerung, formel) in enumerate(CHECKS):
        row = first + offset
        ws.cell(row=row, column=1, value=art).font = Font(name=FONT, size=10, bold=True)
        ws.cell(row=row, column=2, value=titel).font = Font(name=FONT, size=10)
        ws.cell(row=row, column=3, value=erklaerung).font = Font(
            name=FONT, size=10, color="595959"
        )
        ws.cell(row=row, column=4, value=resolve(formel)).font = Font(name=FONT, size=10)
        ws.cell(row=row, column=5, value=f'=IF($D{row}=0,"ok","prüfen")').font = Font(
            name=FONT, size=10, bold=True
        )
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = BORDER
            ws.cell(row=row, column=col).alignment = Alignment(
                vertical="top", wrap_text=col in (2, 3)
            )

    table = Table(displayName="pruefkatalog", ref=f"A6:E{last}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight15", showRowStripes=True)
    ws.add_table(table)

    ws.conditional_formatting.add(
        f"A{first}:E{last}",
        FormulaRule(formula=[f'AND($D{first}>0,$A{first}="Fehler")'],
                    fill=PatternFill("solid", fgColor=C_BAD)),
    )
    ws.conditional_formatting.add(
        f"A{first}:E{last}",
        FormulaRule(formula=[f'AND($D{first}>0,$A{first}="Hinweis")'],
                    fill=PatternFill("solid", fgColor=C_HINT)),
    )

    ws.cell(row=6, column=6, value="lfd. offen")
    for row in range(first, last + 1):
        ws.cell(row=row, column=6, value=f'=IF($D{row}>0,N($F{row - 1})+1,N($F{row - 1}))')
    ws.column_dimensions["F"].hidden = True
    for letter, width in [("A", 10), ("B", 46), ("C", 62), ("D", 9), ("E", 10)]:
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = "A7"
    protect(ws)


def build_pruefungen(wb):
    """Nur die offenen Prüfungen, aus dem Katalog gezogen (Zeile k = k-te offene Prüfung)."""
    ws = wb.create_sheet("Prüfungen")
    ws.sheet_properties.tabColor = "C00000"
    n = len(CHECKS)
    first, last = 7, 6 + n

    ws["A1"] = "Prüfungen"
    ws["A1"].font = Font(name=FONT, size=14, bold=True)
    ws["A2"] = (
        "Rechnet sich bei jeder Änderung neu und zeigt nur, was offen ist. »Fehler« muss "
        "bereinigt werden, »Hinweis« ist zu prüfen und kann im Einzelfall richtig sein. "
        "Alle Prüfungen samt der erledigten stehen im Blatt »Prüfkatalog«."
    )
    ws["A2"].font = Font(name=FONT, size=10, italic=True, color="595959")

    ws["A4"] = "Offene Fehler"
    ws["A4"].font = Font(name=FONT, size=11, bold=True)
    ws["B4"] = (f'=SUMPRODUCT((Prüfkatalog!$A${first}:$A${last}="Fehler")'
                f'*(Prüfkatalog!$D${first}:$D${last}>0))')
    ws["B4"].font = Font(name=FONT, size=11, bold=True)
    ws["C4"] = (f'=IF($B$4=0,"Keine offenen Fehler.","")&IF(COUNTIF(Prüfkatalog!$D${first}:'
                f'$D${last},">0")=0,"",COUNTIF(Prüfkatalog!$D${first}:$D${last},">0")&" von {n} '
                f'Prüfungen sind offen.")')
    ws["C4"].font = Font(name=FONT, size=11, bold=True)

    for idx, text in enumerate(["Art", "Prüfung", "Was dahintersteckt", "Anzahl"], start=1):
        cell = ws.cell(row=6, column=idx, value=text)
        cell.font = Font(name=FONT, size=10, bold=True)
        cell.fill = PatternFill("solid", fgColor=C_TECH)
        cell.border = BORDER

    for row in range(first, last + 1):
        for col, src in ((1, "A"), (2, "B"), (3, "C"), (4, "D")):
            cell = ws.cell(row=row, column=col, value=(
                f'=IFERROR(INDEX(Prüfkatalog!${src}${first}:${src}${last},'
                f'MATCH(ROW()-{first - 1},Prüfkatalog!$F${first}:$F${last},0)),"")'))
            cell.font = Font(name=FONT, size=10, bold=col == 1,
                             color="595959" if col == 3 else "000000")
            cell.alignment = Alignment(vertical="top", wrap_text=col in (2, 3))

    ws.conditional_formatting.add(
        f"A{first}:D{last}",
        FormulaRule(formula=[f'$A{first}="Fehler"'], fill=PatternFill("solid", fgColor=C_BAD)))
    ws.conditional_formatting.add(
        f"A{first}:D{last}",
        FormulaRule(formula=[f'$A{first}="Hinweis"'], fill=PatternFill("solid", fgColor=C_HINT)))
    ws.conditional_formatting.add(
        f"A{first}:D{last}",
        FormulaRule(formula=[f'$A{first}<>""'], border=BORDER))

    for letter, width in [("A", 10), ("B", 46), ("C", 62), ("D", 9)]:
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = "A7"
    protect(ws)


# ----------------------------------------------------------------- Fehlerliste

FEHLER_BLAETTER = [("A", "Aufträge"), ("B", "Betreuungen"), ("Z", "Zuordnung MA"),
                   ("K", "Kinder"), ("F", "Familien"), ("P", "Ansprechpersonen"),
                   ("R", "Berichte")]
FEHLER_SCHLUESSEL = {"A": ["mandate_id"], "B": ["mandate_id", "person_id"],
                     "Z": ["mandate_id", "employee_id"], "K": ["person_id"],
                     "F": ["family_id"], "P": ["contact_person_id"],
                     "R": ["report_id"]}
FEHLER_ZEILEN = 200


def _bereich(pre, field):
    blatt = SHEETS[pre]
    q = f"'{blatt}'!" if " " in blatt else f"{blatt}!"
    letter = resolve("{%s.%s}" % (pre, field))
    return f"{q}${letter}${TOP}:${letter}${MAX}"


def _verteiler(bau, zeile):
    """IF-Kette über alle Blätter in FEHLER_BLAETTER; Excel rechnet nur den zutreffenden Zweig."""
    out = '""'
    for idx in range(len(FEHLER_BLAETTER), 0, -1):
        pre = FEHLER_BLAETTER[idx - 1][0]
        out = f"IF($G{zeile}={idx},{bau(pre)},{out})"
    return out


def build_fehlerliste(wb):
    """Alle Zeilenmeldungen aus allen Blättern in einer Liste.

    Ohne Makro und ohne Matrixformel: jedes Blatt nummeriert seine eigenen
    Meldungen durch (Spalte issue_run), K1:M{n} hält Anzahl und Startversatz je
    Blatt, und jede Zeile hier sucht sich daraus ihr Blatt und ihre Nummer.
    n = Anzahl FEHLER_BLAETTER; die Summe steht eine Zeile darunter.
    """
    n = len(FEHLER_BLAETTER)
    total = n + 1
    ws = wb.create_sheet("Fehlerliste")
    ws.sheet_properties.tabColor = "ED7D31"
    ws.sheet_view.showGridLines = False

    ws["A1"] = "Fehlerliste"
    ws["A1"].font = Font(name=FONT, size=14, bold=True)
    ws["A2"] = (
        f'=IF($L${total}=0,"Nichts offen – keine einzige Meldung.",'
        f'"{{}} Meldungen, davon "&COUNTIF($D$5:$D${4 + FEHLER_ZEILEN},"Fehler")'
        f'&" Fehler. Doppelklick auf das Blatt in Spalte A führt nicht hin – '
        f'die Zeilennummer daneben schon."'
        f'&IF($L${total}>{FEHLER_ZEILEN}," Angezeigt werden die ersten '
        f'{FEHLER_ZEILEN}.",""))'
    ).replace("{}", f'"&$L${total}&"')
    ws["A2"].font = Font(name=FONT, size=10, italic=True, color="595959")

    for i, (pre, blatt) in enumerate(FEHLER_BLAETTER, start=1):
        ws.cell(row=i, column=11, value=blatt)
        ws.cell(row=i, column=12, value=f"=MAX({_bereich(pre, 'issue_run')})")
        ws.cell(row=i, column=13,
                value=0 if i == 1 else f"=$M{i - 1}+$L{i - 1}")
    ws[f"L{total}"] = f"=SUM($L$1:$L${n})"
    for letter in ("K", "L", "M"):
        ws.column_dimensions[letter].hidden = True

    headers = ["Blatt", "Zeile", "Datensatz", "Art", "Meldung"]
    for idx, text in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=idx, value=text)
        cell.font = Font(name=FONT, size=10, bold=True)
        cell.fill = PatternFill("solid", fgColor=C_TECH)
        cell.border = BORDER

    def schluessel(pre):
        teile = [f'INDEX({_bereich(pre, f)},$I{{r}})&""'
                 for f in FEHLER_SCHLUESSEL[pre]]
        return '&" / "&'.join(teile)

    for r in range(5, 5 + FEHLER_ZEILEN):
        ws[f"G{r}"] = f'=IF(ROW()-4>$L${total},"",MATCH(ROW()-5,$M$1:$M${n},1))'
        ws[f"H{r}"] = f'=IF($G{r}="","",ROW()-4-INDEX($M$1:$M${n},$G{r}))'
        ws[f"I{r}"] = (
            f'=IF($H{r}="","",'
            + _verteiler(lambda pre: f'MATCH($H{r},{_bereich(pre, "issue_run")},0)', r)
            + ")")
        ws[f"A{r}"] = f'=IF($G{r}="","",INDEX($K$1:$K${n},$G{r})&"")'
        ws[f"B{r}"] = f'=IF($I{r}="","",$I{r}+{TOP - 1})'
        ws[f"C{r}"] = (f'=IF($I{r}="","",'
                       + _verteiler(lambda pre: schluessel(pre).replace("{r}", str(r)), r)
                       + ")")
        ws[f"D{r}"] = (f'=IF($I{r}="","",'
                       + _verteiler(
                           lambda pre: f'INDEX({_bereich(pre, "issue_kind")},$I{r})&""', r)
                       + ")")
        ws[f"E{r}"] = (f'=IF($I{r}="","",'
                       + _verteiler(
                           lambda pre: f'INDEX({_bereich(pre, "issue_text")},$I{r})&""', r)
                       + ")")
        for col in range(1, 6):
            cell = ws.cell(row=r, column=col)
            cell.font = Font(name=FONT, size=10)
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=col == 5)
    for letter in ("G", "H", "I"):
        ws.column_dimensions[letter].hidden = True

    last = 4 + FEHLER_ZEILEN
    table = Table(displayName="fehlerliste", ref=f"A4:E{last}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight15", showRowStripes=True)
    ws.add_table(table)

    ws.conditional_formatting.add(
        f"A5:E{last}",
        FormulaRule(formula=['$D5="Fehler"'],
                    fill=PatternFill("solid", fgColor=C_BAD), stopIfTrue=True))
    ws.conditional_formatting.add(
        f"A5:E{last}",
        FormulaRule(formula=['$D5="Hinweis"'],
                    fill=PatternFill("solid", fgColor=C_HINT)))

    for letter, width in [("A", 18), ("B", 8), ("C", 24), ("D", 10), ("E", 96)]:
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = "A5"
    protect(ws)


# ------------------------------------------------------------------- Anleitung

LISTEN_ROWS = [
    ("Aufträge", "Was hat die Behörde bewilligt?", "ein Auftrag",
     "bei Verlängerung, Kontingentänderung, Wechsel der Ansprechperson"),
    ("Betreuungen", "Welches Kind wird in welchem Auftrag betreut, und wie lange?",
     "ein Kind in einem Auftrag", "bei Eintritt und Austritt"),
    ("Zuordnung MA", "Wer betreut diesen Auftrag?", "ein Auftrag und eine Person",
     "bei Personalwechsel"),
    ("Kinder", "Wer wird betreut?", "ein Kind, ein einziges Mal",
     "selten – Umzug, Namensänderung, nachgereichte AHV-Nummer"),
    ("Familien", "Über welches Kind wird abgerechnet?", "eine Familie",
     "nur bei Geschwistern – und wenn ein jüngeres Kind dazukommt"),
    ("Ansprechpersonen", "Wer ist beim Leistungsbesteller zuständig?",
     "eine Person bei einem Besteller", "bei Wechsel der Zuständigkeit"),
]

EREIGNIS_ROWS = [
    ("Erstes Kind einer Familie, erstmals betreut", "neue Zeile", "neue Zeile", "neue Zeile"),
    ("Kind war früher schon einmal betreut", "–", "neue Zeile", "neue Zeile"),
    ("Laufendes Kind bekommt zusätzlich eine zweite Leistungsart", "–", "neue Zeile", "neue Zeile"),
    ("Geschwisterkind kommt in einen laufenden Auftrag",
     "neue Zeile, falls noch nicht erfasst",
     "Indexkind prüfen, falls das neue Kind jünger ist", "neue Zeile"),
    ("Ein Kind tritt aus, der Auftrag läuft für die Geschwister weiter",
     "–", "Indexkind bleibt stehen", "Austrittsfelder auf dieser einen Zeile"),
    ("Der ganze Auftrag endet", "–", "Bewilligung bis setzen",
     "Austrittsfelder auf allen Zeilen des Auftrags"),
    ("Verlängerung / Folgeauftrag", "–", "neue Zeile mit Vorgängerauftrag",
     "neue Zeile je weiterbetreutem Kind, Eintritt aus dem Vorgänger übernehmen"),
    ("Neugeborenes kommt dazu, Abrechnung wandert", "neue Zeile",
     "Indexkind auf das Neugeborene setzen – in jedem Auftrag der Familie",
     "neue Zeile, sobald das Neugeborene selbst betreut wird"),
    ("Familie zieht um", "Wohnort ändern", "–", "–"),
    ("AHV-Nummer wird nachgereicht", "eine Zelle", "–", "–"),
    ("Kontingent wird angepasst", "–", "Kontingent ändern", "–"),
    ("Mitarbeitende wechseln", "–", "Blatt »Zuordnung MA«", "–"),
    ("Neue Zuständige beim Sozialdienst", "–",
     "Ansprechperson wechseln", "–"),
]

OFFEN_ROWS = [
    ("Kontingent steht am Auftrag, nicht je Kind",
     "Anhang A.5 des Konzepts rechnet so. Wird pro Kind bewilligt, wandern die drei "
     "Kontingentspalten von »Aufträge« nach »Betreuungen«.",
     "Abschnitt 7, Punkt 2"),
    ("Zuweisungsgrundlage steht am Auftrag",
     "Kann bei Geschwistern je Kind abweichen. Dann gehört die Spalte zu »Betreuungen«.",
     "Abschnitt 7, Punkt 5"),
    ("Vorgängerauftrag ist bei allen Altdaten leer",
     "Aus den bisherigen Daten nicht rekonstruierbar: das Startdatum wurde bei jeder "
     "Verlängerung überschrieben. Ab jetzt bei jedem Folgeauftrag eintragen.",
     "Abschnitt 4"),
    ("AHV 756.2404.7951.71 steht bei zwei Kindern",
     "C1079 Stauffer, Caroline und C1083 Stauffer, Marlon Til. Beide haben eine eigene "
     "Kind-Nr; zusammengelegt wurde nur bei gleichem Namen. Die Prüfung meldet das "
     "weiterhin, bis die Nummer korrigiert ist.",
     "Abschnitt 7, Punkt 7"),
    ("Kein Auftrag hat heute mehr als ein Kind",
     "Ob unter den laufenden Aufträgen Geschwister sind, steht in den Altdaten nicht "
     "drin. Das lässt sich nur im Betrieb beantworten – erster Kandidat ist Nipote "
     "(C1002 / C1068).",
     "Abschnitt 7, Punkt 1"),
    ("Eintritt ist der Beginn der Betreuung, nicht der Bewilligung",
     "Bei allen 86 Altzeilen sind beide gleich, weil das alte Modell nur ein Datum "
     "hatte. Richtig ist der Eintritt in die Leistung; er kann älter sein als jeder "
     "erfasste Auftrag, weil die Aufträge der Vergangenheit nicht erfasst sind. Was "
     "Accordix in Spalte Q erwartet, ist mit Wegpiraten weiterhin offen – das Modell "
     "bedient beide Antworten.",
     "Abschnitt 7, Punkt 6"),
    ("Drei Ansprechpersonen sind widersprüchlich erfasst",
     "Bei AP015 wechselt die Anrede in den Altdaten zwischen Frau und Herr, bei AP022 "
     "und AP025 sind Vor- und Nachname vermutlich vertauscht. Die Bemerkung steht auf "
     "der jeweiligen Zeile.",
     "neu"),
]


def para(ws, row, text, size=10, bold=False, italic=False, color="000000", height=None):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(name=FONT, size=size, bold=bold, italic=italic, color=color)
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    if height:
        ws.row_dimensions[row].height = height
    return row + 1


def mini_table(ws, row, name, headers, rows):
    for idx, text in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=idx, value=text)
        cell.font = Font(name=FONT, size=10, bold=True)
        cell.fill = PatternFill("solid", fgColor=C_TECH)
        cell.border = BORDER
    for r_off, values in enumerate(rows, start=1):
        for c_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row + r_off, column=c_idx, value=value)
            cell.font = Font(name=FONT, size=10)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = BORDER
    last = row + len(rows)
    table = Table(displayName=name, ref=f"A{row}:{get_column_letter(len(headers))}{last}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(table)
    return last + 2


def build_anleitung(wb, stats):
    ws = wb.create_sheet("Anleitung", 0)
    ws.sheet_properties.tabColor = "1F4E79"
    ws.sheet_view.showGridLines = False
    for letter, width in [("A", 42), ("B", 44), ("C", 26), ("D", 34), ("E", 4), ("F", 4)]:
        ws.column_dimensions[letter].width = width

    ws["A1"] = "Stammdaten Wegpiraten: Aufträge, Betreuungen, Kinder"
    ws["A1"].font = Font(name=FONT, size=16, bold=True, color="1F4E79")
    ws.merge_cells("A1:F1")
    r = 2
    r = para(ws, r, f"Vorschlag zur Diskussion, Stand {STAND}. Grundlage: "
                    "docs/konzept_person_auftrag_leistung.md und "
                    "docs/datamodel_person_mandate_care.md", italic=True, color="595959")
    r += 1

    r = para(ws, r, "Warum jetzt mehrere Listen", size=12, bold=True)
    r = para(
        ws, r,
        "Bisher stand alles in einer Liste: das Kind, der bewilligte Auftrag und die "
        "Betreuung selbst. Das geht so lange gut, wie ein Kind genau einen Auftrag hat "
        "und ein Auftrag genau ein Kind betrifft. Beides stimmt nicht mehr. Awa Burri "
        "hat zwei Aufträge und stand deshalb zweimal in der Liste – mit zwei getrennt "
        "gepflegten Geburtsdaten, von denen eines sein Format verloren hat. Und wenn in "
        "einer Familie zwei Kinder betreut werden, läuft der Auftrag über eines davon, "
        "gemeldet werden aber beide.",
        height=62,
    )
    r += 1
    r = mini_table(
        ws, r, "howto_listen",
        ["Liste", "Beantwortet", "Eine Zeile ist", "Ändert sich"],
        LISTEN_ROWS,
    )
    r = para(
        ws, r,
        "Die Blätter stehen in der Reihenfolge, in der sie angefasst werden: was oft "
        "geändert wird, steht links. Die Betreuungsliste wirkt zunächst überflüssig. "
        "Sie ist es nicht: jede Zeile darin ist genau eine Zeile der Accordix-Meldung. "
        "Wer wissen will, wie diese Liste aussieht, legt die letzte Meldedatei daneben – "
        "dieselben Fälle, dieselbe Anzahl, dieselben Ein- und Austrittsdaten.",
        height=48,
    )
    r += 1

    r = para(ws, r, "Nummern", size=12, bold=True)
    r = para(
        ws, r,
        "C… ist ein Kind, A… ein Auftrag, AP… eine Ansprechperson. Die Auftragsnummer "
        "besteht aus A, dem zweistelligen Startjahr und einem dreistelligen Jahreszähler: "
        "A26001 ist der erste Auftrag mit Beginn 2026. Bei der Umstellung wurde der "
        "Zähler nach Bewilligungsbeginn vergeben, bei gleichem Datum nach der bisherigen "
        "Klientennummer. Diese steht in den Notizen des Auftrags. In archivierten "
        "Erfassungsbögen (Zelle G8) und in älteren Rechnungen meint eine C-Nummer "
        "weiterhin den Auftrag. Neue Nummern werden von Hand vergeben: nächster freier "
        "Zähler des Startjahrs.",
        height=90,
    )
    r += 1

    r = para(ws, r, "Wohin gehört eine Angabe?", size=12, bold=True)
    r = para(ws, r, "Drei Fragen, in dieser Reihenfolge:")
    r = para(ws, r, "1.  Gilt sie für das Kind, egal welcher Auftrag läuft?  →  Kinder")
    r = para(ws, r, "2.  Gilt sie für den Auftrag, egal welches Kind darin betreut wird?  →  Aufträge")
    r = para(ws, r, "3.  Braucht man beides, um sie zu bestimmen?  →  Betreuungen")
    r = para(
        ws, r,
        "Probe: Das Geburtsdatum ändert sich nicht, wenn Awa Burri einen zweiten Auftrag "
        "bekommt – Frage 1. Der Kostenträger ist bei ihren beiden Aufträgen verschieden – "
        "Frage 2. Ein Austrittsdatum lässt sich ohne beides nicht bestimmen: Paul tritt "
        "aus, aber nur aus diesem einen Auftrag – Frage 3.",
        height=48,
    )
    r += 1

    r = para(ws, r, "Familie, Betreuungskind, Indexkind", size=12, bold=True)
    r = para(
        ws, r,
        "Jedes Kind gehört zu einer Familie. Die Familie trägt das Indexkind – "
        "in der Regel das jüngste. Der Auftrag erbt es über die Kinder, die in ihm "
        "betreut werden; im Blatt »Aufträge« stehen Familie und Indexkind "
        "deshalb grau. Wandert die Abrechnung auf ein Neugeborenes, ändert sich eine "
        "Zelle im Blatt »Familien«, und alle Aufträge der Familie ziehen nach.",
        height=62,
    )
    r = para(
        ws, r,
        "Aus den Altdaten liess sich keine Familie ableiten. Nachname und Wohnort "
        "reichen nicht: der Wohnort ist eine Gemeinde, und C1002 Luan und C1068 Yarrah "
        "Nipote aus Meiringen sind zwei Familien, kein Geschwisterpaar. Deshalb hat "
        "jedes Kind zunächst eine eigene Familie bekommen. Geschwister werden von Hand "
        "zusammengelegt: bei beiden Kindern dieselbe Familien-Nr eintragen und in der "
        "Familie das jüngere Kind als Indexkind setzen. Die übrig gebliebene "
        "Familie meldet sich dann als »Familie ohne Kinder«.",
        height=78,
    )
    r += 1
    r = para(ws, r, "Betreuungskind und Indexkind sind zweierlei", size=12, bold=True)
    r = para(
        ws, r,
        "Das Betreuungskind steht in den Betreuungen: wer in diesem Auftrag Leistung "
        "bekommt. Jede solche Zeile ist eine Zeile der Accordix-Meldung. Das "
        "Indexkind steht im Auftrag: das jüngste Kind der Familie, über das die "
        "Rechnung läuft. Meist ist es dasselbe Kind – nötig ist das nicht.",
        height=48,
    )
    r = para(
        ws, r,
        "Ein Beispiel, das es geben kann: die Familie hat Anna (4) und Paul (9). Pauls "
        "SPF läuft weiter, Annas Abklärung ist ausgelaufen. Abgerechnet wird trotzdem "
        "über Anna, weil sie das jüngste Kind ist. In Pauls Auftrag steht als "
        "Indexkind also Anna, obwohl Anna dort keine Betreuungszeile hat – und "
        "sie bekommt auch keine, denn gemeldet wird nur, wer betreut wird.",
        height=62,
    )
    r = para(
        ws, r,
        "Die Prüfspalte »Indexkind plausibel?« meldet »hier nicht betreut«, wenn "
        "genau dieser Fall vorliegt. Bei einem Auftrag über ein einzelnes Kind ist das "
        "ein Vertipper, bei Geschwistern kann es richtig sein. »jüngeres Kind betreut« "
        "heisst dagegen: im Auftrag wird ein Kind betreut, das jünger ist als das "
        "eingetragene Indexkind – dann wandert die Abrechnung vermutlich noch.",
        height=62,
    )
    r += 1

    r = para(ws, r, "Was wann zu pflegen ist", size=12, bold=True)
    r = mini_table(
        ws, r, "howto_ereignisse",
        ["Ereignis", "Kinder", "Aufträge", "Betreuungen"],
        EREIGNIS_ROWS,
    )

    r = para(ws, r, "Reihenfolge beim Erfassen", size=12, bold=True)
    r = para(
        ws, r,
        "Von hinten nach vorne, weil jede Zeile auf die vorige zeigt: erst das Kind "
        "(Blatt »Kinder«), dann – falls die zuständige Person noch fehlt – die "
        "Ansprechperson, dann der Auftrag, dann die Betreuung, zuletzt die "
        "Mitarbeiterzuordnung. Eine Familie braucht es nur bei Geschwistern.",
        height=48,
    )
    r = para(
        ws, r,
        "Ein neuer Auftrag für ein bekanntes Kind sind drei Zeilen auf drei Blättern: "
        "Aufträge, Betreuungen, Zuordnung MA. Danach steht im Blatt »Fehlerliste«, was "
        "noch fehlt.",
        height=32,
    )
    r += 1

    r = para(ws, r, "Wie die Blätter zu lesen sind", size=12, bold=True)
    r = para(
        ws, r,
        "Zeile 1 sagt in einem Satz, wozu das Blatt da ist; wen das stört, blendet die "
        "Zeile aus. Zeile 2 trägt die deutsche Beschriftung, Zeile 3 den technischen "
        "Feldnamen für den Import. Die Daten beginnen in Zeile 4.",
        height=32,
    )
    r = para(
        ws, r,
        "Links wird erfasst, rechts wird gerechnet. Alle Eingabespalten stehen "
        "lückenlos vorne, dahinter kommen die grauen ▸-Spalten. Die Grenze ist die "
        "Stelle, an der die weissen Zellen aufhören.",
        height=32,
    )
    r = para(ws, r, "Weisse Zellen:  hier wird eingetragen.")
    r = para(
        ws, r,
        "Graue Zellen mit ▸:  rechnen sich selbst aus – nicht überschreiben. Es gibt "
        "keinen Blattschutz, damit Sortieren und Filtern funktionieren; eine "
        "überschriebene Formel zeigt sich in der Fehlerliste erst, wenn der Wert nicht "
        "mehr passt.",
        height=48,
    )
    r = para(
        ws, r,
        "Felder mit Auswahlliste:  Pfeil am rechten Zellrand anklicken. Die Listen der "
        "Kind-, Auftrags- und AP-Nummern wachsen automatisch mit; ein neu angelegtes "
        "Kind steht sofort zur Auswahl.",
        height=32,
    )
    r = para(
        ws, r,
        "Neue Zeile:  in die erste freie Zeile unter der Tabelle schreiben, die Tabelle "
        "wächst mit. Zeilen nicht dazwischenschieben. Vor dem Löschen einer Zeile ins "
        "Blatt »Prüfungen« sehen, ob eine andere Liste noch darauf verweist. Wer lieber "
        "Feld für Feld erfasst: eine Zelle in der Tabelle anklicken und "
        "Daten → Formular öffnen – das schreibt direkt in die Liste, mit denselben "
        "Auswahllisten.",
        height=48,
    )
    r = para(
        ws, r,
        "Rot hinterlegte Zelle:  die Angabe verweist ins Leere oder widerspricht einer "
        "anderen Liste. Gelb hinterlegt: für Accordix unvollständig oder nachzusehen.",
        height=32,
    )
    r = para(
        ws, r,
        "Schreibweise:  Accordix vergleicht buchstabengetreu. »Keine weitere Leistung« "
        "wird abgewiesen, richtig ist »keine weitere Leistung«. Deshalb die Auswahlliste "
        "benutzen und nicht abtippen – 14 Werte aus dem Altbestand sind aus genau diesem "
        "Grund rot markiert.",
        height=48,
    )
    r = para(
        ws, r,
        "Blatt »Fehlerliste«:  sammelt alle Meldungen aus allen Blättern in einer "
        "Liste, mit Blatt, Zeilennummer und Datensatz. Von dort aus lässt sich der Reihe "
        "nach abarbeiten, statt von Blatt zu Blatt zu suchen. Über den Filter in der "
        "Spalte »Art« bleiben nur die Fehler stehen.",
        height=48,
    )
    r = para(
        ws, r,
        "Blatt »Prüfungen«:  dieselben Sachverhalte gezählt statt aufgezählt — es zeigt nur die offenen, alle stehen im »Prüfkatalog« — mit einer "
        "Erklärung je Prüfung. »Fehler« muss bereinigt werden, »Hinweis« kann im "
        "Einzelfall richtig sein.",
        height=32,
    )
    r += 1

    r = para(ws, r, "Leistungsarten haben eine Gültigkeit", size=12, bold=True)
    r = para(
        ws, r,
        "Im Blatt »Leistungstypen« steht neben from_date jetzt to_date. Die Auswahlliste "
        "im Auftrag bietet nur an, was heute gilt – ST01_alt und ST02_alt sind zum "
        "31.12.2025 geschlossen und verschwinden damit aus der Liste, ohne dass ein "
        "Schlüssel umbenannt werden musste. Ändert sich ein Ansatz, wird die alte Zeile "
        "mit to_date geschlossen und eine neue angelegt; bestehende Aufträge bleiben, "
        "wo sie sind, und melden sich als »Leistungsart ausgelaufen«.",
        height=78,
    )
    r += 1

    r = para(ws, r, "Noch mit Wegpiraten zu klären", size=12, bold=True)
    r = para(
        ws, r,
        "Diese Punkte sind entschieden worden, damit die Datei benutzbar ist – nicht, "
        "weil die Antwort feststeht.", italic=True, color="595959",
    )
    r = mini_table(
        ws, r, "howto_offen",
        ["Angenommen", "Begründung und was sich bei anderer Antwort ändert", "Konzept"],
        OFFEN_ROWS,
    )

    r = para(ws, r, "Was aus den Altdaten geworden ist", size=12, bold=True)
    r = para(
        ws, r,
        f"Aus {stats['rows']} Klientenzeilen wurden {stats['persons']} Kinder, "
        f"{stats['mandates']} Aufträge, {stats['cares']} Betreuungen und "
        f"{stats['contacts']} Ansprechpersonen. Vier Kinder standen doppelt in der Liste "
        "und sind zusammengelegt: "
        + ", ".join(f"{pid} aus {' und '.join(cids)}"
                    for pid, cids in sorted(stats["merged"].items()))
        + ".",
        height=48,
    )
    r = para(
        ws, r,
        "Das Kurzzeichen ist vom Auftrag zum Kind gewandert – es beschreibt den Namen "
        "des Kindes, nicht die Bewilligung. Ein Kind mit zwei Aufträgen hat damit "
        "dasselbe Kurzzeichen auf beiden; der Dateiname des Erfassungsbogens bleibt "
        "trotzdem eindeutig, weil die Auftragsnummer darin steht. Drei Kinder heissen "
        "in der Rohform MaSt: Stoller behält MaSt, Stähli hatte schon MaSt2, Stauffer "
        "hat MaSt3 bekommen.",
        height=62,
    )
    r = para(
        ws, r,
        f"Die Ansprechpersonen standen bisher als Anrede, Vorname und Nachname in jeder "
        f"Auftragszeile. Aus {stats['mandates']} Auftragszeilen sind "
        f"{stats['contacts']} Personen geworden. Dabei sind "
        f"{stats['contact_conflicts']} Widersprüche sichtbar geworden, die vorher in den "
        "Wiederholungen untergegangen sind – sie stehen als Bemerkung auf der jeweiligen "
        "Zeile im Blatt »Ansprechpersonen«.",
        height=62,
    )
    r = para(
        ws, r,
        f"Ein Austrittsdatum wurde nur dort übernommen, wo auch Austrittsangaben erfasst "
        f"waren – bei {stats['with_leave']} von {stats['cares']} Betreuungen. Das alte "
        "Feld end_date war in allen übrigen Fällen das Bewilligungsende und steht jetzt "
        "beim Auftrag. Genau diese Unterscheidung musste für die Meldung vom 29.08.2026 "
        "von Hand getroffen werden.",
        height=62,
    )
    r = para(
        ws, r,
        "Die alte Klientenliste liegt unverändert als ausgeblendetes Blatt "
        "»Klienten (alt)« bei.",
        height=32,
    )
    r += 1

    r = para(ws, r, "Technische Notiz", size=12, bold=True)
    r = para(
        ws, r,
        "Die Excel-Tabellen heissen person, mandate, mandate_person, "
        "masterdata_contact_person und relation_mandate_emp. Der Stammdaten-Import "
        "erwartet heute noch masterdata_client und relation_client_emp und wird "
        "nachgezogen; bis dahin läuft »python -m cli import-master« mit dieser Datei "
        "nicht. Die Felder sr_ap_gender, sr_ap_first_name und sr_ap_last_name stehen "
        "weiter am Auftrag – jetzt als Formel aus dem Blatt »Ansprechpersonen«, damit "
        "die Rechnungsanrede ohne Codeänderung weiterläuft.",
        height=78,
    )
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A3"
    protect(ws)


# ------------------------------------------------- Namen, Gültigkeiten, Regeln

def _rng(sheet, col, first, last):
    """Dynamischer Bereich: wächst mit den Einträgen, ohne Leerzeilen anzubieten.

    Ohne führendes Gleichheitszeichen: ein definedName ist in OOXML eine Formel,
    kein Zellinhalt. Excel entfernt den Namen kommentarlos, wenn dort "=" steht —
    LibreOffice nimmt beides, weshalb es erst in Excel auffällt.
    """
    q = f"'{sheet}'" if " " in sheet else sheet
    return (
        f"OFFSET({q}!${col}${first},0,0,"
        f"MAX(1,COUNTA({q}!${col}${first}:${col}${last})),1)"
    )


def define_names(wb):
    for name in list(wb.defined_names.keys()):
        if name.startswith(("accordix_", "liste_")):
            del wb.defined_names[name]

    names = {
        "liste_kind": _rng("Kinder", resolve("{K.person_id}"), TOP, MAX),
        "liste_auftrag": _rng("Aufträge", resolve("{A.mandate_id}"), TOP, MAX),
        "liste_ansprechperson": _rng(
            "Ansprechpersonen", resolve("{P.contact_person_id}"), TOP, MAX),
        "liste_familie": _rng("Familien", resolve("{F.family_id}"), TOP, MAX),
        # Anzeigespalte, gezählt über die Nummernspalte: COUNTA würde die 2000
        # Formelzellen darunter mitzählen, weil "" für COUNTA nicht leer ist.
        "liste_kind_namen": (
            f'OFFSET(Kinder!${resolve("{K.display_name}")}${TOP},0,0,'
            f'MAX(1,COUNTA(Kinder!${resolve("{K.person_id}")}${TOP}:'
            f'${resolve("{K.person_id}")}${MAX})),1)'),
        # Dieselbe Idee für den Vorgängerauftrag: die Anzeigespalte statt der
        # blossen Nummer, gezählt über mandate_id.
        "liste_auftrag_namen": (
            f'OFFSET(Aufträge!${resolve("{A.mandate_display}")}${TOP},0,0,'
            f'MAX(1,COUNTA(Aufträge!${resolve("{A.mandate_id}")}${TOP}:'
            f'${resolve("{A.mandate_id}")}${MAX})),1)'),
        # Nur die heute gültigen Leistungsarten: Spalte M zählt sie lückenlos
        # auf, Spalte L sagt, wie viele es sind.
        "liste_leistungsart": (
            f"OFFSET(Leistungstypen!$M$2,0,0,"
            f"MAX(1,MAX(Leistungstypen!$L$2:$L${ST_MAX})),1)"),
        "liste_besteller": _rng("Leistungsbesteller", "B", 3, 200),
        "liste_kostentraeger": _rng("Kostenträger", "B", 3, 200),
        "liste_buero": _rng("Büros", "A", 2, 200),
        "liste_mitarbeiter": _rng("Mitarbeiter", "B", 3, 200),
    }
    for idx, (tech, _label, _values) in enumerate(WERTELISTEN):
        letter = get_column_letter(1 + 2 * idx)
        key = "liste_ja_nein" if tech == "ja_nein" else f"accordix_{tech}"
        if tech == "anrede":
            key = "liste_anrede"
        if tech == "rolle":
            key = "liste_rolle"
        if tech in ("berichtsrhythmus", "berichtsstatus", "berichtsform"):
            key = f"liste_{tech}"
        names[key] = _rng("Wertelisten", letter, 3, 100)

    for name, ref in names.items():
        wb.defined_names[name] = DefinedName(name, attr_text=ref)


def apply_validations(wb):
    unique = "Diese Nummer ist schon vergeben. Jede Nummer darf nur einmal vorkommen."
    datum = "Bitte ein Datum eingeben, zum Beispiel 01.03.2026."

    k = wb["Kinder"]
    add_dv(k, "{K.person_id}", "custom",
           'COUNTIF($'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},'
           '$'"{K.person_id}"'3)=1', "Kind-Nr", unique)
    add_dv(k, "{K.social_security_number}", "custom",
           'OR($'"{K.social_security_number}"'3="",'
           '$'"{K.social_security_number}"'3="Privat",'
           'AND(LEN($'"{K.social_security_number}"'3)=16,'
           'LEFT($'"{K.social_security_number}"'3,4)="756."))', "AHV-Nummer",
           'Format 756.1234.5678.90. Wo keine Nummer vorliegt, bleibt das Feld leer '
           'oder erhält den Eintrag "Privat".')
    add_dv(k, "{K.family_id}", "list", "liste_familie", "Familie",
           "Leer lassen, solange das Kind allein steht – dann ist es selbst das "
           "Indexkind. Geschwister tragen dieselbe Familien-Nr.")
    add_dv(k, "{K.date_of_birth}", "date", "DATE(1990,1,1)", "Geburtsdatum",
           "Datum zwischen 1990 und heute.", formula2="TODAY()", operator="between")
    add_dv(k, "{K.gender}", "list", "accordix_gender", "Geschlecht", "m, w oder d.")
    add_dv(k, "{K.uma_umf}", "list", "accordix_uma_umf", "UMA/UMF",
           "Ja, Nein oder Unbekannt.")
    add_dv(k, "{K.spoken_language}", "list", "accordix_spoken_language",
           "Hauptsprache", "DE oder FR.")
    add_dv(k, "{K.canton_of_residence}", "list", "accordix_canton_of_residence",
           "Wohnkanton", "Kantonskürzel oder Ausland.")

    a = wb["Aufträge"]
    add_dv(a, "{A.mandate_id}", "custom",
           'COUNTIF($'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},'
           '$'"{A.mandate_id}"'3)=1', "Auftrag-Nr", unique)
    add_dv(a, "{A.service_type_id}", "list", "liste_leistungsart", "Leistungsart",
           "Auswahl aus dem Blatt Leistungstypen.")
    add_dv(a, "{A.service_requester_id}", "list", "liste_besteller",
           "Leistungsbesteller", "Auswahl aus dem Blatt Leistungsbesteller.")
    add_dv(a, "{A.contact_person_id}", "list", "liste_ansprechperson",
           "Ansprechperson",
           "AP-Nr aus dem Blatt Ansprechpersonen. Sie muss zum Leistungsbesteller "
           "dieses Auftrags gehören – die Prüfung meldet es sonst.")
    add_dv(a, "{A.payer_id}", "list", "liste_kostentraeger", "Kostenträger",
           "Auswahl aus dem Blatt Kostenträger.")
    add_dv(a, "{A.tenant_id}", "list", "liste_buero", "Standort",
           "Auswahl aus dem Blatt Büros.")
    for token in ("{A.start_date}", "{A.end_date}"):
        add_dv(a, token, "date", "DATE(2000,1,1)", "Bewilligungszeitraum", datum,
               formula2="DATE(2100,12,31)", operator="between")
    for token in ("{A.allowed_travel_time}", "{A.allowed_direct_effort}",
                  "{A.allowed_indirect_effort}"):
        add_dv(a, token, "decimal", "0", "Kontingent",
               "Stunden pro Monat, null oder mehr.", formula2="10000",
               operator="between")
    add_dv(a, "{A.allocation}", "list", "accordix_allocation", "Zuweisungsgrundlage",
           "Auswahl aus der Accordix-Werteliste.")
    add_dv(a, "{A.predecessor_choice}", "list", "liste_auftrag_namen",
           "Vorgängerauftrag",
           "Auswahl aus diesem Blatt: Auftrag, Indexkind, Leistungsart, Bewilligung "
           "bis. Gespeichert wird die Nummer vor dem Gedankenstrich; eine von Hand "
           "getippte Nummer bleibt gültig. Die Liste ist noch nicht auf dasselbe "
           "Kind/dieselbe Familie und Leistungsart gefiltert – bitte selbst "
           "abgleichen. Der Nachfolgeauftrag daneben rechnet sich daraus.")

    b = wb["Betreuungen"]
    add_dv(b, "{B.mandate_id}", "list", "liste_auftrag", "Auftrag-Nr",
           "Auftrag-Nr aus dem Blatt Aufträge.")
    add_dv(b, "{B.person_id}", "list", "liste_kind", "Kind-Nr",
           "Kind-Nr aus dem Blatt Kinder.")
    for token in ("{B.start_date}", "{B.end_date}"):
        add_dv(b, token, "date", "DATE(2000,1,1)", "Ein- und Austritt", datum,
               formula2="DATE(2100,12,31)", operator="between")
    add_dv(b, "{B.is_leaving_reason_planned}", "list", "liste_ja_nein",
           "War der Austritt geplant?", "Ja oder Nein.")
    add_dv(b, "{B.leaving_reason}", "list", "accordix_leaving_reason",
           "Austrittsgrund",
           "Auswahl aus der Accordix-Werteliste. Für »Anderer« die Spalte daneben füllen.")
    add_dv(b, "{B.after_leave_situation}", "list", "accordix_after_leave_situation",
           "Situation nach Austritt",
           "Auswahl aus der Accordix-Werteliste. Für »andere« die Spalte daneben füllen.")
    add_dv(b, "{B.is_consultative_adolescent_psychiatric_care}", "list",
           "liste_ja_nein", "IBF: konsiliarische Versorgung",
           "Ja oder Nein. Nur bei der Leistungsart IBF zu füllen.")
    add_dv(b, "{B.number_of_care_days_per_week}", "whole", "0",
           "SPT: Betreuungstage pro Woche",
           "Null bis sieben. Nur bei der Leistungsart SPT zu füllen.",
           formula2="7", operator="between")

    p = wb["Ansprechpersonen"]
    add_dv(p, "{P.contact_person_id}", "custom",
           'COUNTIF($'"{P.contact_person_id}"'$3:$'"{P.contact_person_id}"'${MAX},'
           '$'"{P.contact_person_id}"'3)=1', "AP-Nr", unique)
    add_dv(p, "{P.service_requester_id}", "list", "liste_besteller",
           "Leistungsbesteller", "Auswahl aus dem Blatt Leistungsbesteller.")
    add_dv(p, "{P.gender}", "list", "liste_anrede", "Anrede", "Frau oder Herr.")

    f = wb["Familien"]
    add_dv(f, "{F.family_id}", "custom",
           'COUNTIF($'"{F.family_id}"'$3:$'"{F.family_id}"'${MAX},'
           '$'"{F.family_id}"'3)=1', "Familien-Nr", unique)
    add_dv(f, "{F.index_person}", "list", "liste_kind_namen", "Indexkind",
           "Auswahl aus dem Blatt Kinder – das jüngste Kind dieser Familie. "
           "Gespeichert wird die Nummer vor dem Gedankenstrich.")

    z = wb["Zuordnung MA"]
    add_dv(z, "{Z.mandate_id}", "list", "liste_auftrag", "Auftrag-Nr",
           "Auftrag-Nr aus dem Blatt Aufträge.")
    add_dv(z, "{Z.employee_id}", "list", "liste_mitarbeiter", "Mitarbeiter-Nr",
           "Mitarbeiter-Nr aus dem Blatt Mitarbeiter.")
    add_dv(z, "{Z.role}", "list", "liste_rolle", "Rolle",
           "P = primäre Betreuungsperson, der KESB gegenüber benannt. "
           "S = unterstützend. Ändert nichts an Timesheet oder Rechnung.")

    r = wb["Berichte"]
    add_dv(r, "{R.mandate_choice}", "list", "liste_auftrag_namen", "Auftrag",
           "Auswahl aus dem Blatt Aufträge. Gespeichert wird die Nummer vor dem "
           "Gedankenstrich.")
    add_dv(r, "{R.report_form}", "list", "liste_berichtsform", "Berichtsform",
           "Bericht, Zwischenbericht oder Abschlussbericht. Wo der Unterschied zwischen "
           "Bericht und Zwischenbericht liegt, ist mit Wegpiraten noch nicht geklärt.")
    add_dv(wb["Aufträge"], "{A.report_cadence}", "list", "liste_berichtsrhythmus",
           "Berichtsrhythmus",
           "einmalig, periodisch oder ereignisbezogen (z.B. nach jedem Besuch).")
    add_dv(r, "{R.status}", "list", "liste_berichtsstatus", "Status",
           "offen, erledigt oder entfällt.")


def _rule(formula, color):
    return FormulaRule(formula=[resolve(formula)], fill=PatternFill("solid", fgColor=color))


def _range(prefix, name):
    letter = resolve("{%s.%s}" % (prefix, name))
    return f"{letter}{TOP}:{letter}{MAX}"


def apply_conditional_formatting(wb):
    k = wb["Kinder"]
    k.conditional_formatting.add(
        _range("K", "social_security_number"),
        _rule('AND($'"{K.social_security_number}"'3<>"",'
              '$'"{K.social_security_number}"'3<>"Privat",'
              'COUNTIF($'"{K.social_security_number}"'$3:'
              '$'"{K.social_security_number}"'${MAX},'
              '$'"{K.social_security_number}"'3)>1)', C_BAD),
    )
    k.conditional_formatting.add(
        _range("K", "short_code"),
        _rule('AND($'"{K.short_code}"'3<>"",'
              'COUNTIF($'"{K.short_code}"'$3:$'"{K.short_code}"'${MAX},'
              '$'"{K.short_code}"'3)>1)', C_BAD),
    )
    betreut = ('AND($'"{K.person_id}"'3<>"",'
               'COUNTIF(Betreuungen!$'"{B.person_id}"'$3:$'"{B.person_id}"'${MAX},'
               '$'"{K.person_id}"'3)>0,')
    for name in ("date_of_birth", "gender", "uma_umf", "canton_of_residence"):
        k.conditional_formatting.add(
            _range("K", name),
            _rule(betreut + "${K." + name + "}3=\"\")", C_HINT),
        )

    a = wb["Aufträge"]
    a.conditional_formatting.add(
        _range("A", "index_person_id"),
        _rule('AND($'"{A.mandate_id}"'3<>"",$'"{A.index_person_id}"'3="")', C_BAD),
    )
    k.conditional_formatting.add(
        _range("K", "family_id"),
        _rule('AND($'"{K.family_id}"'3<>"",'
              'COUNTIF(Familien!$'"{F.family_id}"'$3:$'"{F.family_id}"'${MAX},'
              '$'"{K.family_id}"'3)=0)', C_BAD),
    )
    a.conditional_formatting.add(
        _range("A", "contact_person_id"),
        _rule('AND($'"{A.contact_person_id}"'3<>"",'
              'COUNTIFS(Ansprechpersonen!$'"{P.contact_person_id}"'$3:'
              '$'"{P.contact_person_id}"'${MAX},$'"{A.contact_person_id}"'3,'
              'Ansprechpersonen!$'"{P.service_requester_id}"'$3:'
              '$'"{P.service_requester_id}"'${MAX},'
              '$'"{A.service_requester_id}"'3)=0)', C_BAD),
    )
    a.conditional_formatting.add(
        _range("A", "predecessor_choice"),
        _rule('AND($'"{A.predecessor_mandate_id}"'3<>"",'
              'COUNTIF($'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},'
              '$'"{A.predecessor_mandate_id}"'3)=0)', C_BAD),
    )

    b = wb["Betreuungen"]
    b.conditional_formatting.add(
        _range("B", "mandate_id"),
        _rule('AND($'"{B.mandate_id}"'3<>"",'
              'COUNTIF(Aufträge!$'"{A.mandate_id}"'$3:$'"{A.mandate_id}"'${MAX},'
              '$'"{B.mandate_id}"'3)=0)', C_BAD),
    )
    b.conditional_formatting.add(
        _range("B", "person_id"),
        _rule('AND($'"{B.person_id}"'3<>"",'
              'COUNTIF(Kinder!$'"{K.person_id}"'$3:$'"{K.person_id}"'${MAX},'
              '$'"{B.person_id}"'3)=0)', C_BAD),
    )
    b.conditional_formatting.add(
        _range("B", "leaving_reason"),
        _rule('AND($'"{B.end_date}"'3<>"",$'"{B.leaving_reason}"'3="")', C_HINT),
    )

    # Erfasste Codewerte gegen die Wertelisten: fängt Altbestand und Tippfehler.
    for sheet, prefix, name, listname in [
        ("Kinder", "K", "gender", "accordix_gender"),
        ("Kinder", "K", "uma_umf", "accordix_uma_umf"),
        ("Kinder", "K", "spoken_language", "accordix_spoken_language"),
        ("Kinder", "K", "canton_of_residence", "accordix_canton_of_residence"),
        ("Aufträge", "A", "allocation", "accordix_allocation"),
        ("Betreuungen", "B", "leaving_reason", "accordix_leaving_reason"),
        ("Betreuungen", "B", "after_leave_situation", "accordix_after_leave_situation"),
    ]:
        token = "$" + resolve("{%s.%s}" % (prefix, name))
        wb[sheet].conditional_formatting.add(
            _range(prefix, name),
            _rule(f'AND({token}3<>"",SUMPRODUCT(--EXACT({listname},{token}3))=0)', C_BAD),
        )


# ------------------------------------------------------------------------ Main

SHEET_ORDER = [
    "Anleitung", "Prüfungen", "Prüfkatalog",
    "Aufträge", "Betreuungen", "Zuordnung MA", "Kinder", "Familien",
    "Ansprechpersonen", "Berichte", "Fehlerliste",
    "Leistungstypen", "Leistungsbesteller", "Kostenträger", "Mitarbeiter", "Büros",
    "Wertelisten", "Hilfsdaten", "Klienten (alt)",
]


def freeze_old_clients(wb):
    """Altbestand als stille Referenz behalten, aber Tabelle und Regeln lösen.

    Die Formeln dort greifen auf die Tabelle masterdata_client zu; ohne sie ergäben
    sie #NV. Das Blatt ist eine Momentaufnahme, also werden die zuletzt berechneten
    Werte festgeschrieben.
    """
    old = wb["Klienten"]
    cached = openpyxl.load_workbook(SRC, data_only=True, keep_links=False)["Klienten"]
    for row in old.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.value = cached[cell.coordinate].value
    for tname in list(old.tables.keys()):
        del old.tables[tname]
    old.data_validations.dataValidation = []
    old.title = "Klienten (alt)"
    old.sheet_state = "hidden"
    old.sheet_properties.tabColor = "BFBFBF"


def verify_excel_strict(wb):
    """Was Excel beim Öffnen kommentarlos repariert, LibreOffice aber schluckt.

    Der Anlass: alle 18 benannten Bereiche trugen ein führendes "=" und wurden von
    Excel entfernt — sämtliche Auswahllisten waren dort tot, während hier alles
    grün aussah, weil geprüft wurde, was LibreOffice rechnet.
    """
    from openpyxl.utils.cell import range_boundaries

    fehler = []
    for name, dn in wb.defined_names.items():
        if str(dn.value).startswith("="):
            fehler.append(f"benannter Bereich {name} beginnt mit '='")
    if getattr(wb, "_external_links", None):
        fehler.append(f"{len(wb._external_links)} externe Verknüpfung(en) übrig")

    for pre, cols in MODEL.items():
        for col in cols:
            if not col.get("auto"):
                continue
            f = col["formula"]
            if "INDEX(" in f and '&"")' not in f and 'IF(INDEX' not in f:
                fehler.append(f"{pre}.{col['name']}: INDEX ohne Leerzellen-Schutz")

    for ws in wb.worksheets:
        for table in ws.tables.values():
            if not re.match(r"^[A-Za-z_\\][A-Za-z0-9_.]*$", table.displayName):
                fehler.append(f"{ws.title}: Tabellenname {table.displayName!r}")
            min_col, min_row, max_col, _ = range_boundaries(table.ref)
            kopf = [ws.cell(row=min_row, column=c).value
                    for c in range(min_col, max_col + 1)]
            if any(v in (None, "") for v in kopf):
                fehler.append(f"{ws.title}/{table.displayName}: leere Kopfzelle")
            if len(set(kopf)) != len(kopf):
                fehler.append(f"{ws.title}/{table.displayName}: doppelte Kopfnamen")
        for dv in ws.data_validations.dataValidation:
            for f in (dv.formula1, dv.formula2):
                if f and str(f).startswith("="):
                    fehler.append(f"{ws.title} {dv.sqref}: Gültigkeit mit '='")
        for ref, regeln in ws.conditional_formatting._cf_rules.items():
            for regel in regeln:
                for f in regel.formula or []:
                    if str(f).startswith("="):
                        fehler.append(f"{ws.title} {ref}: bedingte Formatierung mit '='")

    if fehler:
        raise SystemExit("Excel würde reparieren:\n  " + "\n  ".join(fehler))
    return len(wb.defined_names)


def carry_over_handwork(persons, relations):
    """Familien, Rollen und Berichte aus der vorhandenen Zieldatei übernehmen.

    Alles andere entsteht aus migration_v2.json und wird beim Bauen neu geschrieben.
    Familien, die Rolle in Zuordnung MA und alle Berichte sind die Ausnahme: sie
    entstehen nur von Hand, weil migration_v2.json sie nicht kennt. Ohne diesen
    Schritt wäre jeder Neubau ein Datenverlust – `relations` wird dabei in place
    um `role` ergänzt.
    """
    if not HAND.exists():
        return [], []
    alt = openpyxl.load_workbook(HAND, data_only=True)
    if "Familien" not in alt.sheetnames:
        return [], []

    def kopfzeile(ws):
        """Die vorhandene Datei kann noch die alte Zeilenaufteilung tragen."""
        for r in (TOP - 1, 2, 3, 1):
            if ws.cell(row=r, column=1).value in (
                    "family_id", "person_id", "mandate_id", "report_id"):
                return r
        raise SystemExit(f"{ws.title}: Feldnamenzeile nicht gefunden")

    def spalten(ws, kopf):
        return {ws.cell(row=kopf, column=i).value: i
                for i in range(1, ws.max_column + 1)}

    def wert(ws, row, sp, name):
        return ws.cell(row=row, column=sp[name]).value if name in sp else None

    fs = alt["Familien"]
    kopf = kopfzeile(fs)
    sp = spalten(fs, kopf)
    anzeige = {p["person_id"]: f'{p["person_id"]} — {p["last_name"]}, {p["first_name"]}'
               for p in persons}
    families = []
    for row in range(kopf + 1, MAX + 1):
        fid = fs.cell(row=row, column=sp["family_id"]).value
        if not fid:
            continue
        # Die vorhandene Datei kann die blosse Nummer tragen oder schon die Auswahl
        # mit Namen; gespeichert wird beides Mal auf die Anzeigeform normalisiert.
        wahl = wert(fs, row, sp, "index_person") \
            or wert(fs, row, sp, "index_person_id") \
            or wert(fs, row, sp, "billing_person") \
            or wert(fs, row, sp, "billing_person_id")
        if wahl:
            wahl = anzeige.get(str(wahl).split(" ")[0], wahl)
        if not CARRY_FAMILIES:
            continue
        families.append({
            "family_id": fid,
            "index_person": wahl,
            "notes": wert(fs, row, sp, "notes"),
        })

    ks = alt["Kinder"]
    kopf = kopfzeile(ks)
    sp = spalten(ks, kopf)
    zuordnung = {}
    for row in range(kopf + 1, MAX + 1):
        pid = ks.cell(row=row, column=sp["person_id"]).value
        if not pid:
            continue
        fid = wert(ks, row, sp, "family_id")
        if fid and CARRY_FAMILIES:
            zuordnung[pid] = fid
    for p in persons:
        if p["person_id"] in zuordnung:
            p["family_id"] = zuordnung[p["person_id"]]

    rollen = {}
    if "Zuordnung MA" in alt.sheetnames:
        zs = alt["Zuordnung MA"]
        kopf = kopfzeile(zs)
        sp = spalten(zs, kopf)
        for row in range(kopf + 1, MAX + 1):
            mid = wert(zs, row, sp, "mandate_id")
            if not mid:
                continue
            role = wert(zs, row, sp, "role")
            if role:
                rollen[(mid, wert(zs, row, sp, "employee_id"))] = role
        for r in relations:
            key = (r["mandate_id"], r.get("employee_id"))
            if key in rollen:
                r["role"] = rollen[key]

    berichte = []
    if "Berichte" in alt.sheetnames:
        rs = alt["Berichte"]
        kopf = kopfzeile(rs)
        sp = spalten(rs, kopf)
        for row in range(kopf + 1, MAX + 1):
            rid = wert(rs, row, sp, "report_id")
            if not rid:
                continue
            berichte.append({
                "report_id": rid,
                "mandate_choice": wert(rs, row, sp, "mandate_choice")
                or wert(rs, row, sp, "mandate_id"),
                "due_date": wert(rs, row, sp, "due_date"),
                "report_form": wert(rs, row, sp, "report_form"),
                "status": wert(rs, row, sp, "status"),
                "completed_date": wert(rs, row, sp, "completed_date"),
                "notes": wert(rs, row, sp, "notes"),
            })

    if families or zuordnung or rollen or berichte:
        print(f"übernommen aus der vorhandenen Datei: {len(families)} Familien, "
              f"{len(zuordnung)} Kind-Familie-Zuordnungen, {len(rollen)} Rollen, "
              f"{len(berichte)} Berichte")
    return families, berichte


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    # keep_links=False wirft die externe Verknüpfung der Quelldatei weg: sie zeigt auf
    # eine Proton-Drive-Konfliktkopie derselben Datei auf einem fremden Rechner.
    data["families"], data["reports"] = carry_over_handwork(
        data["persons"], data["relations"])

    single = collections.Counter(r["mandate_id"] for r in data["relations"])
    # Bei mehreren Mitarbeitenden wird die Rolle von Hand entschieden; übernommene
    # Rollen aus der alten Sandbox (weitgehend pauschal P) werden hier verworfen.
    for r in data["relations"]:
        if not r.get("role"):
            r["role"] = "P" if single[r["mandate_id"]] == 1 else None
    if not data["reports"] and REPORTS_SEED.exists():
        data["reports"] = json.loads(REPORTS_SEED.read_text(encoding="utf-8"))
        print(f"Berichte aus {REPORTS_SEED.name} angelegt: {len(data['reports'])}")

    wb = openpyxl.load_workbook(SRC, keep_links=False)

    # Externe Verweise und Altverbindungen entfernen, sonst bleiben tote Links.
    for name in list(wb.defined_names.keys()):
        if name.startswith("_xlcn.") or name == "accordix7":
            del wb.defined_names[name]

    # Streublatt aus einem alten Versuch.
    if "Tabelle1" in wb.sheetnames:
        del wb["Tabelle1"]

    freeze_old_clients(wb)
    if "Relation Klient-MA" in wb.sheetnames:
        del wb["Relation Klient-MA"]

    sheets = [
        ("Aufträge", "mandate", AUFTRAEGE, data["mandates"], f"B{TOP}"),
        ("Betreuungen", "mandate_person", BETREUUNGEN, data["cares"], f"C{TOP}"),
        ("Zuordnung MA", "relation_mandate_emp", ZUORDNUNG, data["relations"], f"A{TOP}"),
        ("Kinder", "person", KINDER, data["persons"], f"C{TOP}"),
        ("Ansprechpersonen", "masterdata_contact_person", ANSPRECHPERSONEN,
         data["contacts"], f"B{TOP}"),
        ("Familien", "masterdata_family", FAMILIEN, data["families"], f"B{TOP}"),
        ("Berichte", "report", BERICHTE, data["reports"], f"B{TOP}"),
    ]
    for title, table_name, columns, records, freeze in sheets:
        ws = wb.create_sheet(title)
        write_intro(ws, columns, INTRO[title])
        style_header(ws, columns)
        last = write_rows(ws, columns, records)
        add_table(ws, table_name, columns, last)
        ws.freeze_panes = freeze
        ws.sheet_properties.tabColor = "1F4E79"
        colour_status_columns(ws, columns)
        protect(ws, columns)

    extend_leistungstypen(wb)
    build_wertelisten(wb)
    build_fehlerliste(wb)
    build_pruefkatalog(wb)
    build_pruefungen(wb)
    build_anleitung(wb, data["stats"])

    define_names(wb)
    apply_validations(wb)
    apply_conditional_formatting(wb)

    wb._sheets = [wb[name] for name in SHEET_ORDER if name in wb.sheetnames] + [
        ws for ws in wb.worksheets if ws.title not in SHEET_ORDER
    ]
    wb.active = 0
    namen = verify_excel_strict(wb)
    wb.save(DST)
    print(f"geschrieben: {DST}")
    print(f"Excel-Strengeprüfung bestanden ({namen} benannte Bereiche, keine externen Links)")
    print("Blätter:", [ws.title for ws in wb.worksheets])


if __name__ == "__main__":
    main()
