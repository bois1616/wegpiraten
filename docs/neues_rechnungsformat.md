Mit dem nächsten KJA-FS-Release werden neue Funktionen eingeführt, welche die Massenerfassung von Rechnungen ermöglichen. Da wir davon ausgehen, dass Anpassungen an Ihren IT-Systemen notwendig sind, um die neuen Funktionen vollumfänglich nutzen zu können, informieren wir Sie frühzeitig darüber. Untenstehend finden Sie eine Beschreibung der neuen Funktionen sowie die Voraussetzungen und die Zeitplanung.

1. Erklärung der neuen Funktionen

Damit das Erfassen von vielen Rechnungen neu mit weniger Aufwand verbunden ist, werden drei neue Funktionen entwickelt. Die Nutzung dieser Funktionen ist freiwillig. Gerne können die Rechnungen auch wie bis anhin eingereicht werden.

1.1. Mehrere Rechnungen gleichzeitig erfassen
Aktuell können im KJA-FS nur einzelne Rechnungen eingereicht werden. Zukünftig können mehrere Rechnungen (max. 50 PDF-Dateien) gleichzeitig hochgeladen werden. Die Pflichtfelder und Validierungen bleiben unverändert.

1.2. Automatisches Abfüllen von Rechnungsinformationen anhand des PDF-Dateinamen
Beim Upload von Rechnungen müssen mehrere Pflichtfelder befüllt werden. Die Pflichtfelder sind:

-   Rechnung als PDF
-   Antrags-Nr. vom KJA-FS
-   Rechnungs-Nr. des Leistungserbringenden (max. 20 Zeichen, darf keine Unterstriche enthalten)
-   Beginn der Rechnungsperiode
-   Ende der Rechnungsperiode
-   Standort (siehe Funktion 1.3.)

An den Pflichtfeldern ändert sich nichts, jedoch kann KJA-FS die Felder zukünftig selbstständig befüllen, sofern die PDF-Rechnung nach einem definierten Format benannt ist. Das Format lautet:

-   Format: {Rechnungsnummer}_{RechnungsperiodeVon:yyyymmdd}_{RechnungsperiodeBis:yyyyymmdd}_{Antragsnummer}_{Freitext:optional}
-   Beispiel: RE-14598_20260401_20260430_260417009_Behandlung-Müller.pdf

Liegt eine hochgeladene Datei vor, die dieser Namenskonvention entspricht, werden die enthaltenen Informationen ausgelesen und automatisch den entsprechenden Feldern zugeordnet. Wichtig ist dabei, dass das Format exakt eingehalten wird (Vollständigkeit, keine zusätzlichen Leerschläge, Einhaltung der Reihenfolge, Einhaltung der Datumsformate, keine Unterstriche in der Rechnungs-Nr.). Damit die Rechnungen eingereicht werden können, müssen alle Eingaben gültig sein. Die Validierung der Eingaben bleibt unverändert.

1.3. Favorit-Standort festlegen
Beim Erfassen von Rechnungen muss jeweils auch der Standort des Leistungserbringenden ausgewählt werden, an welchem die Leistung erbracht wurde (sofern mehr als ein Standort vorhanden ist). Zukünftig kann pro User ein «Favorit-Standort» definiert werden. Dieser Favorit-Standort wird beim Erfassen von Rechnungen dann vorausgefüllt. Wenn der gleiche User für mehrere Standorte Rechnungen einreicht, dann kann der Favorit-Standort auch jederzeit selbstständig geändert werden.

2. Voraussetzungen

Damit die neuen Funktionen vollumfänglich genutzt werden können und die erhoffte Entlastung bringen, müssen Ihre IT-Systeme gewisse Voraussetzungen erfüllen. Diese werden nachstehend erläutert.

-   Die Namenskonvention der PDF-Dateien muss eingehalten werden. Damit der Prozess weniger aufwändig wird, ist es sinnvoll, wenn das IT-System das PDF selbstständig korrekt benennt. Die Antrags-Nr. aus KJA-FS ist zwingender Bestandteil der Namenskonvention und muss daher gepflegt werden. Zukünftig werden die LE per E-Mail benachrichtigt, wenn im KJA-FS ein Antrag genehmigt wird.
-   Bereits heute kann KJA-FS die Zahlungsinformationen der QR-Rechnungen selbstständig auslesen. Damit die Rechnungen effizienter eingereicht werden können, muss es sich um QR-Rechnungen handeln, sonst müssen die Zahlungsinformationen manuell abgefüllt werden.

-   Es muss ein Favorit-Standort im KJA-FS gesetzt werden. Der Favorit-Standort kann auch selbstständig geändert werden.
