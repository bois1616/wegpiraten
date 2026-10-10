# Synthetisches Stammdaten-Workbook

`create_masterdata.create_workbook(path)` erzeugt eine kleine XLSX für Importtests.
Sie enthält keine Kundendaten und braucht weder Sandbox-Dateien noch `build.py`.

```python
from pathlib import Path
from tests.fixtures.create_masterdata import create_workbook

create_workbook(Path("/tmp/wegpiraten-test/masterdata.xlsx"))
```

Enthalten sind die elf Importtabellen mit den editierbaren Fachfeldern und den beiden
berechneten Fremdschlüsseln `mandate.predecessor_mandate_id` und `report.mandate_id`.
Die Auswahltexte selbst stehen ebenfalls in der Fixture. Weitere Anzeige- oder
Prüfspalten sind nicht erforderlich. Die Fixture ist formelfrei, ihre Werte sind
deshalb auch mit `data_only=True` sofort lesbar.

Fälle: zwei Geschwister mit jüngstem Indexkind, parallele Leistungsart nur beim älteren
Kind, Folgeauftrag mit unverändertem Eintritt, Betreuung mit Austritt, zwei Mitarbeitende
mit Rollen P/S und eine Person mit TS=FALSCH. Die Stundenbudgets enthalten 0,5 Stunden,
damit die Importtests die Umrechnung zu 30 Minuten prüfen können. AHV-Nummern bleiben
leer; Namen und Einrichtungen sind ausdrücklich als Testdaten bezeichnet.

`SA` steht absichtlich nicht im Workbook. Der Import muss den technischen Auftrag selbst
anlegen (DM-15); dessen Integrationstest folgt mit der Importumstellung. DM-14 erstellt
die Testgrundlage, behauptet noch keinen erfolgreichen Import mit dem neuen Schema.
