# Planprüfung und Spezifikationsentwürfe, 10.10.2026

Status: Entwurf, Opus/Astra-Review offen. Autor: Codex (GPT-6; genaue Modellvariante in
dieser Sitzung nicht ausgewiesen). Keine Opus-Aufgabe wird mit diesem Dokument geschlossen;
abhängige Implementierungen sind damit noch nicht freigegeben. Die Vorschläge ändern keine
bereits von Stephan bestätigte Fachregel.

Grundlage: Übergabe und Backlog vom 09.10., DM-02 und DM-04, Konzept, Datenmodell,
Umstellungs-Runbook sowie die betroffenen Import-, Rechnungs-, Bogen- und Reportingmodule.
Der finale Build und die Alt-Neu-Abgleiche wurden hier nicht ausgeführt.

## Urteil

Die Zerlegung nach Workbook, Import, Bögen, Rechnung, Reporting und Betrieb ist sinnvoll.
Der Fallback auf den gesicherten alten Programmstand passt zum Neuaufbau der SQLite-DB.
Die technische Normalisierung und die Datenpflege sind ausdrücklich getrennt. Der Plan
ist als Arbeitsübersicht brauchbar, als vollständige Umsetzungsvorgabe noch nicht.

Vor der Umsetzung fehlen Verträge für den Umgang mit unbrauchbaren Datensätzen,
dauerhafte Alt-ID-Zuordnung, Zeilenreihenfolge und zwei berechnete Fremdschlüssel.
Die Abhängigkeiten lassen Zwischenstände zu, in denen Config und Programme nicht
zusammenpassen. Einige Abnahmekriterien widersprechen bereits bestätigten Änderungen.

## Prüfung der Opus/Astra-Aufgaben

| Aufgabe | Was jetzt möglich ist | Was für die Abnahme fehlt |
| --- | --- | --- |
| DM-02 | Bestehende Antworten sind ausreichend für Kostenträgerfilter und Datenpflegegrundsatz. Neue technische Randfälle stehen unten. | Antworten zu Q1–Q4; keine erneute Kundenbefragung zu beantworteten Fragen. |
| DM-03 | Einmaligkeit ist entschieden; Umsetzung braucht noch eine eindeutige Erkennung des Gesprächs und Zuordnung zur Rechnung. | ST99 ist laut Datenmodell PRIVAT, nicht das Gespräch; Q4. |
| DM-04 | Spezifikation grundsätzlich verwendbar; Ergänzungen zur Abnahme unten. | DM-05 muss Verlustfreiheit tatsächlich belegen. |
| DM-07 | Aufräumregeln und Reihenfolge lassen sich spezifizieren. | Dateiweises Inventar und bestätigtes externes Archiv vor Entfernen von Personendaten. |
| DM-12 | View-Vertrag lässt sich spezifizieren. | SQL/Excel-Parität auf synthetischen Fällen und finalem Workbook, Q2. |
| DM-15 | Sentinel-Vertrag lässt sich vollständig als Entwurf beschreiben. | Review und Integrationstest über alle Verbraucher. |
| DM-22 | Resolver und dauerhafte Mappingquelle lassen sich spezifizieren. | Mapping aus DM-05, Archivbogen-Test, Review. |
| DM-34 | Vergleichskriterien lassen sich jetzt festlegen. | Beide Programme, festgelegte Monatsquellen und ausgeführter Vergleich. |
| DM-40 | Felder, Kostenträgerfilter und Monatsauswahl lassen sich spezifizieren. | Q3 zur Kette, Umsetzung und DM-41. |
| DM-41 | Vergleichsmethode lässt sich beschreiben. | Neue Meldung und tatsächlicher Abgleich der August-Datei. |
| DM-43 | Stilllegung ist der passende Vorschlag. | Entfernen der CLI-/Makefile-Aufrufe und Prüfung der Verweise. |
| DM-50 | Anforderungen an Review und Generalprobe sind klar. | Fertige Befehle, Runbook und tatsächlich durchgeführte Generalprobe. |
| DM-70 | Kleiner Ausgabevertrag möglich. | Bewusst nach erster Nutzung; keine Vorziehung auf den kritischen Pfad. |

## Neue Fragen an Stephan

Diese Fragen betreffen Auswirkungen der Programme, keine Bereinigung der Kundendaten.
Die Antworten sind noch offen; keine der folgenden Optionen gilt durch Schweigen als genehmigt.

- **Q1: Unbrauchbare Rechnungsgrundlage.** Darf ein Auftrag ohne eindeutige Leistungszuordnung,
  Tarif oder berechenbaren Betrag vom Rechnungsausgang ausgeschlossen und ausdrücklich als
  nicht erstellt gemeldet werden, während der übrige Lauf weitergeht? Vorschlag: ja.
  Eine fehlende Geschäftsnummer bleibt dagegen wie entschieden eine Rechnung mit `PRÜFEN`.
- **Q2: Historisches Indexkind.** Soll eine erneut erstellte alte Rechnung das heutige Indexkind
  verwenden? `person.family_id` hat keine Historie; ein jüngeres, später erfasstes Kind ändert
  heute auch die Ableitung für Vorgängeraufträge. Vorschlag für diese Übergangslösung: heutiger
  Stammdatenstand, alte ausgestellte Rechnung und damaliges Workbook im Monatsarchiv erhalten.
  Falls das damalige Indexkind rechnerisch reproduzierbar sein muss, braucht es eine andere
  Datenhaltung; die heutige View allein reicht nicht.
- **Q3: Accordix und Folgeaufträge.** Ist eine Meldezeile pro Betreuung/Auftrag auch dann gewollt,
  wenn aufeinanderfolgende Aufträge denselben Eintritt und offene Betreuung haben? Die
  Gleichsetzung im Datenmodell ist ausdrücklich dokumentiert, aber dann können mehrere Zeilen
  desselben Kindes und derselben Leistungsart im Monatsfile stehen. Keine automatische
  Zusammenfassung einführen, bevor die gewünschte Wirkung bestätigt ist.
- **Q4: Einführungsgespräch erkennen.** Im Backlog steht ST99 für das Einführungsgespräch,
  im Datenmodell unter «Open questions», Punkt 5, dagegen für `PRIVAT`. Der Code kennt nur
  kostenfreie Leistungszeilen mit «ohne Berechnung» in der Notiz. Soll die Umsetzung eine
  solche erfasste Zeile verwenden oder automatisch eine 15-Minuten-Position erzeugen?
  Einmaligkeit ist bereits entschieden, diese Frage betrifft nur Erkennung und Erzeugung.
  Ohne Antwort darf kein allgemeiner PRIVAT-Auftrag als Einführungsgespräch behandelt werden.

## DM-12: Vertrag für `v_mandate`

1. Genau eine Zeile je `mandate_id`, einschliesslich `SA`. Alle Auftragsfelder bleiben verfügbar.
   Verbindungen auf Kontakt, Kind und Leistungstyp dürfen die Zeilen weder vervielfachen noch
   durch einen INNER JOIN verschwinden lassen. Unauflösbare Werte bleiben NULL und bekommen
   einen Befund; keine erfundenen Namen oder AHV-Nummern.
2. DM-11 speichert die Excel-Zeilennummer als technische Herkunftsspalte `source_row` für
   `person` und `mandate_person`. Sie ist kein neues editierbares Workbook-Feld. Excel wählt
   bei gleichem Geburtsdatum das erste Kind in der Kinderliste; der Auftrag nimmt die erste
   Betreuung seiner Liste (`build.py`, `K.index_person_id`, `A.index_person_id`). SQL muss
   dieselbe Reihenfolge benutzen. Ein Sortieren nach ID oder ein zufälliger SQL-Zugriff reicht
   nicht. Invariante 47 meldet den Gleichstand weiterhin.
3. Für die erste Betreuung: ohne Familie das Betreuungskind selbst; mit Familie das Kind mit
   maximalem Geburtsdatum aus **allen** Kindern dieser Familie, auch ohne Betreuung im Auftrag.
   Austritt oder abgelaufene Bewilligung begrenzen diese Kandidatenmenge nicht. Das ist die
   dokumentierte Regel; ihre historische Wirkung hängt an Q2.
4. Bei mehreren Familien, mehreren Kindern ohne Familie oder fehlendem Geburtsdatum: Excel
   kann trotzdem ein erstes Kind liefern. Zur Parität dieses Ergebnis separat vergleichen;
   der Befund muss den Auftrag erreichen, auch wenn ein Indexwert vorhanden ist. Die View darf
   einen Befund nicht durch eine erfolgreich gelieferte ID als erledigt behandeln.
5. `index_person_id`, `short_code`, `first_name`, `last_name`, `social_security_number` kommen
   vom so bestimmten Kind. `sr_ap_gender`, `sr_ap_first_name`, `sr_ap_last_name` kommen von
   `masterdata_contact_person`. Keine Namen aus der beschrifteten Dropdownauswahl parsen.
6. Budgeteinheit in SQLite bleibt **Minuten**, passend zu den bisherigen Verbrauchern.
   DM-10 setzt für die drei editierbaren Stundenfelder `multiply_by: 60` und Integer-Typ;
   die View multipliziert nicht erneut. Beispiel: 0.5 Stunden ergeben 30 Minuten.
   `allowed_hours_per_month` bleibt als bestehender Verbrauchername die Summe in Minuten.
   NULL-Budgets bleiben in den Quellfeldern erkennbar; bestehende Verbraucher können sie für
   die Anzeige als 0 behandeln, nicht als neu erteilte Bewilligung.
7. Familienvergleiche müssen Excel entsprechen. Excel MATCH ist bei Text nicht einfach
   SQLite BINARY; insbesondere Gross-/Kleinschreibung und Umlaute separat testen. Kein
   ungeprüftes `COLLATE NOCASE` als vollständige Excel-Parität behaupten. Abweichende
   Familientexte werden nicht im Kunden-Workbook korrigiert.

Abnahme DM-13: synthetisch keine Familie, betreute Geschwister, unbetreutes jüngstes Kind,
gleiche Geburtstage in umgekehrter Zeilenfolge, fehlendes Geburtsdatum, mehrere Familien,
fehlender Kontakt und 0.5-Stunden-Budget. Danach gecachte Excel-Werte des finalen Workbooks
mit der View für **alle** Aufträge vergleichen; ungültige Fälle zusätzlich als Befunde prüfen.

## DM-15: `SA`

Vorschlag: ein vom Import erzeugter Auftrag `SA`, kein Kind, keine Betreuung, keine
MA-Auftragszuordnung. `service_type_id=ST999`, Code `SONST`; Besteller, Kostenträger,
Ansprechperson, Standort, Bewilligungsdaten und Geschäftsnummer bleiben NULL. Der technische
Auftrag wird nicht im Kunden-Workbook ergänzt. Idempotente Erzeugung, genau eine Zeile.

Die Ausnahme muss alle einschlägigen Pflichtprüfungen umfassen, insbesondere 8, 13, 23 und 42,
nicht nur Invariante 8. Normale Aufträge erhalten keine solche Ausnahme. Die View liefert
für `SA` NULL als Indexkind; der bestehende interne Bogenkopf liefert die feste Beschriftung.
Budgets bleiben 1000/1000/500 Minuten. `employees.ts=1` erzeugt SA-Bögen; NULL tut das bei
SA weiterhin nicht. Die bisherigen abweichenden Defaults für normale Bögen bleiben erhalten.

Bogen-Import erlaubt `SA` unmittelbar und prüft Mitarbeiter-FK, aber keine Auftragszuordnung.
Rechnung und Accordix schliessen `SA` explizit aus; Arbeitszeitprotokoll enthält diese Zeiten.
Test: SA erzeugen, importieren, im Arbeitszeitprotokoll wiederfinden; keine Rechnung und keine
Accordix-Zeile, keine Pflichtbefunde für den technischen Auftrag.

## DM-22: Alte Nummern dauerhaft auflösen

`mandate_numbers.json` darf nicht die laufende Quelle bleiben, wenn DM-07 sie entfernt.
Vorschlag: beim finalen Build eine versionierte technische Zuordnung ohne Personendaten
nach `data/legacy_mandate_mapping.json` exportieren: alte ID, neue ID, Herkunft als
Vorgänger/Nachfolger und die damaligen Bewilligungsgrenzen. Keine AHV-Nummern oder Namen.
Der Zugriff erfolgt über Config. DM-07 archiviert erst danach die ursprüngliche Mappingdatei.
Keine automatische Ableitung aus `person_id`: zusammengeführte Kinder behalten nur eine C-ID,
alte Bögen können die andere enthalten. Bemerkungstext ist kein stabiler Primärschlüssel.

Resolver je Leistungszeile:

1. `SA` unmittelbar übernehmen. Bekannte A-ID unmittelbar übernehmen; Datum ausserhalb der
   Bewilligung als Befund melden, nicht still einem anderen Auftrag zuweisen.
2. C-ID ist im Bogen eine **alte Auftrags-ID**, niemals der neue Kinderfilter aus DM-32.
   Kandidaten ausschliesslich aus der technischen Zuordnung ermitteln.
3. Ein Kandidat: übernehmen, Datum ausserhalb seiner Bewilligung als Befund. Sonst würden
   überschriebene historische Zeiträume trotz eindeutiger Identität unimportierbar.
4. Mehrere Kandidaten: Leistungsdatum gegen die aktuellen Bewilligungsgrenzen der bekannten
   Aufträge prüfen, Grenzen inklusiv, offenes Ende unbegrenzt. Genau ein Treffer wird genommen.
   Null oder mehrere Treffer: fataler Zuordnungsfehler für **diese Datei**, mit Blatt/Zeile,
   Datum und Kandidaten. Keine Auswahl nach Kurzzeichen, Namen oder MA-Zuordnung.
5. Fehlende ID oder fehlender Kandidatenauftrag: gleicher Fehlerweg. Kein automatisches
   Wiederanlegen eines im Kunden-Workbook fehlenden Auftrags aus dem historischen Mapping.
6. Erst alle Zeilen auflösen, dann pro Datei atomar schreiben. Bei Fehler keine Leistungszeile
   dieser Datei speichern und Datei nicht nach `done` verschieben; andere Dateien können
   weiterlaufen. Die Importzusammenfassung nennt unvollständige Läufe ausdrücklich.

DM-23 muss Typ, Tarif, Standort und Budget aus dem **pro Zeile** bestimmten Auftrag beziehen.
Heute ermittelt `_read_header` diese Felder vor dem Lesen der Leistungsdaten. Ein C-Bogen,
der eine Auftragsgrenze überquert, kann deshalb nicht durch blosses Ersetzen der Header-ID
korrekt werden. Vorhandene Budgetwerte im Bogen bleiben als Herkunft erhalten; eine
Abweichung zu Folgeauftragsbudgets wird sichtbar, nicht unbemerkt übergangen.

Tests: C-ID eines zusammengeführten Kindes, Folgeauftrag an beiden Grenztagen, zwei
Aufträge innerhalb desselben Bogens mit unterschiedlichen Tarifen/Budgets, Überlappung,
Lücke, unbekannte ID, A-ID ausserhalb Bewilligung, SA, vollständiger Dateirücklauf bei Fehler.

## DM-34 und DM-41: Vergleich und Abnahme

Beide Läufe bekommen getrennte DB-, Import-, `done`- und Ausgabeordner; identische Kopien
der Leistungsbögen und expliziten MONTH-Wert. Keine Cloud-Holung oder Verschiebung der
Monatsoriginale während des Vergleichs. Quell-Workbooks, Config, Vorlagen, Mapping und
Git-Revisionen werden mit Hash im privaten Prüfpaket festgehalten. Keine Personendaten
oder tatsächlichen Rechnungskontexte ins Repo committen.

DM-34 vergleicht zuerst jede Rohleistungszeile (Quelle, Zeile, Datum, Mitarbeiter,
Minutenarten, Kilometer, Notiz), dann Rechnungen. C→A und etwaige Aufteilung auf
Folgeaufträge müssen das Zuordnungsmanifest erklären. Vor einer Rechnungssumme zählen
importierte/abgewiesene Zeilen und Gesamtsummen, damit verschwundene Rechnungen auffallen.

Gleich bleiben ohne begründete Ausnahme: Zeiten, Rundung, Positionen, Tarife, Betrag,
Kontingentbehandlung, Empfänger, Besteller, Standort, IBAN, Währung und QR-Betrag.
Rechnungsnummer, SCOR-Referenz und Dateiname dürfen sich ändern. QR-Nutzdaten sind also
**nicht vollständig gleich**: die Referenz ist ausdrücklich anders, ihre Prüfziffer muss
gültig sein. DOCX-Inhalt semantisch vergleichen, PDF-Layout stichprobenweise; ZIP/XML- oder
PDF-Dateihashes sind keine fachlichen Gleichheitskriterien.

Zulässige Unterschiede nicht pauschal freigeben: Aufteilung einer C-Rechnung in zwei
Folgeaufträge, abweichendes Kontingent, ST99 und neueres Indexkind werden einzeln mit
Quelle/Fachregel und finanzieller Wirkung erklärt. DM-02-B-Befunde rechtfertigen nicht
automatisch jede Abweichung. Die eingefrorene Oktober-Stammdatei bildet nicht zwingend
den damaligen Septemberstand ab. Falls das Monatsarchiv fehlt, den Test ausdrücklich als
Programmvergleich mit heutigem Datenstand kennzeichnen.

DM-41 vergleicht August als Multimenge, nicht als Menge: doppelte Meldezeilen dürfen nicht
verschwinden. Internes Manifest mit Auftrag, Betreuungskind, Ausgabereihe, Ausschlussgrund.
P1000-Filter und getrennte Austrittsdaten sind erlaubte Regeländerungen; zusätzliche
Geschwister sind nur mit tatsächlich erfasster Betreuung zulässig, im initialen Build
ohne Familien nicht vorauszusetzen. Die manuell erstellte August-Datei ist eine Referenz,
keine automatische Wahrheit; jede Abweichung braucht eine konkrete Erklärung.

## DM-40: Accordix-Vertrag

Nur Aufträge mit meldepflichtigem Kostenträger aus einer validierten Config-Liste
(initial `P1000`). SA ausschliessen. Personendaten vom **Betreuungskind**, niemals vom
Indexkind; Leistungsart über `service_types.code` und `SERVICE_TYPE_MAP`, Zuweisung vom
Auftrag, Eintritt/Austritt und Austrittsfelder von `mandate_person`.

Vorschlag Monatsauswahl: sowohl Auftrag als auch Betreuung überlappen den Meldemonat,
inklusive Grenzen. Das ist nötig, weil bei Verlängerungen Eintritt gleich und Austritt
offen bleiben: allein der Betreuungszeitraum würde alle alten Aufträge weiter melden.
Bewilligungsende begrenzt die Auswahl, wird aber **nie als Austritt exportiert**.
Q3 bleibt insbesondere für den Wechsel innerhalb eines Monats offen.

Fehlende Pflichtwerte, unbekannte Leistungsmappings und ungültige Codewerte nicht durch
Defaults ersetzen. Bestehendes Überspringen solcher Zeilen braucht eine vollständige
Begleitliste mit Betreuungsschlüssel und Grund sowie Zählung von Kandidaten, geschriebenen
und ausgeschlossenen Zeilen. Gewünschter Umgang bei 0 gültigen Zeilen explizit testen.
Format und Spalten der Accordix-Vorlage bleiben erhalten, kein internes ID-Feld ergänzen.

## DM-07, DM-43 und DM-70

**DM-07:** Nach DM-06 und DM-41 sowie Sicherung des DM-34/51-Prüfpakets jede Datei
inventarisieren. Excel-Strukturprüfer und Windows-Prüfskript bei Bedarf nach `tools/`
übernehmen, ohne Import von `build.py` oder JSON-Migrationsdaten. Dateien mit Personendaten
verschiebt Stephan extern; erst nach bestätigter Sicherung löschen. Alte Workbook-Versionen
behalten ihren Beweiswert. Vor DM-07 muss DM-22 eine unabhängige Mappingquelle haben.
Historische Dokumentverweise als solche kennzeichnen, ausführbare Pfade entfernen.

**DM-43:** `extend_masterdata_accordix.py` für das neue Workbook stilllegen; es sucht
`masterdata_client` und dient nicht als Strukturpflege für die neuen Tabellen. Auch
CLI-Befehl `extend-master`, Makefile-Target, Hilfe und Betriebsanleitung anpassen. Keine
Ersatzfunktion zum Umbau eines Kunden-Workbooks nebenbei einführen; alte Funktion bleibt
im Fallback-Branch erreichbar.

**DM-70:** eigenes Make-Target mit MONTH, Berichtstermine im Monat, Formen nur als Text.
`erledigt`/`entfällt` nicht als offene Aufgabe anzeigen; leerer Status gilt als offen.
Genau eine Rolle P bestimmt die zuständige Person. Keine oder mehrere P erzeugen eine
sichtbare Liste ohne eindeutige Zuständigkeit, keine willkürliche Zuweisung. Bericht-ID,
Auftrag, Fälligkeit und Bemerkung auf dem Terminzettel, ohne AHV-Nummer. Keine automatische
Terminfortschreibung oder Kundenverteilung. Umsetzung bleibt P2.

## Erforderliche Ergänzungen am Plan

- **DM-10/11:** `mandate.predecessor_mandate_id` und `report.mandate_id` sind fachliche
  Verweise trotz grauer Formelspalte. Import entweder aus geprüftem Cache oder durch
  festgelegte Extraktion aus `predecessor_choice`/`mandate_choice`; nicht weglassen.
  Cachefehler von erlaubtem Leerwert unterscheiden. Gemeinsame Schlüsselnamen und
  Excel-Tabellennamen vor Config-Änderung festlegen.
- **DM-11/16:** Selbst-FK von Vorgängeraufträgen braucht alle Aufträge vor FK-Prüfung;
  die Excel-Reihenfolge garantiert keinen Vorgänger zuerst. Erst sammeln, dann prüfen.
  Technische Unlesbarkeit muss fehlschlagen: der heutige Import fängt Lesefehler ab und
  liefert teils 0 Zeilen zurück. Q1 und ein Vertrag für verwaiste Referenzen/ungültige
  Typen fehlen. Rohbefunde aufbewahren; kein stiller Verlust durch PK/FK-Verwerfen.
- **DM-05:** Feldweiser Verlustvergleich muss auch Konflikte innerhalb zusammengeführter
  Kinder und Ansprechpersonen abdecken. Eine Mehrheitsanrede ist eine echte Entscheidung
  über Werte; widersprüchliche Originalwerte dürfen nicht unsichtbar verschwinden.
  Nachweise mit Personendaten ins private Prüfpaket, im Git-Log nur IDs und Zählungen.
- **DM-03/30:** Einmaligkeit allein spezifiziert keine Rechnung. ST99 steht im Datenmodell
  für PRIVAT, die Zuordnung im Backlog ist daher nicht belastbar. Der heutige Code erkennt
  «ohne Berechnung» in Notizen, keine ST99-Automatik. Erkennung, Position, Kostenfreiheit
  und Verhalten ohne Leistungszeilen sowie bei mehreren Aufträgen im Eintrittsmonat
  explizit festlegen; keinesfalls auf jedem Auftrag dieselben 15 Minuten hinzufügen.
- **DM-20:** Monatsüberlappung von Bewilligung (`start <= Monatsende`, Ende leer oder
  `end >= Monatsanfang`) spezifizieren. Der alte Code prüft nur Ende. Entscheiden und
  testen, ob vollständig beendete Betreuungen ohne beendeten Auftrag noch Bögen erzeugen.
- **DM-16/61:** Der Pflichtumfang der Import-Invarianten ist widersprüchlich: DM-16 nennt
  Invarianten generell, DM-61 verschiebt Hinweise auf P1. Für P0 wenigstens alle Befunde
  prüfen, die Rechnungsidentität, Tarif, Zuordnung und Meldeausgabe beeinflussen.
- **Stabile Schritte:** DM-10 darf die alte Config nicht in einem isolierten Commit entfernen,
  solange alle Verbraucher noch `client` brauchen. Config, Import und Verbraucherkontrakte
  als zusammengehörige Umstellung behandeln oder Vorbereitung noch ohne Umschalten committen.
- **Abhängigkeiten:** Spezifikationen DM-12/15/22/34/40 vor abhängiger Implementierung;
  DM-14 vor Integrationstests; DM-22-Mapping vor DM-07. DM-50 vor DM-51 beibehalten.
  DM-41 im Diagramm nur dann Voraussetzung für Merge/Oktober-Lauf, wenn Accordix zuvor
  fällig ist, passend zum Text bei DM-53. Fälligkeit als konkretes Betriebsgate festhalten.
- **Dokumentstand:** Konzept und Umstellungs-Runbook enthalten noch beantwortete Fragen
  und alte Bereinigungsanweisungen. In DM-50 als überholt markieren und auf DM-02 verweisen.
  Kein Wiedereröffnen dieser Entscheidungen. Neue Spezifikationen gelten erst nach Review.
