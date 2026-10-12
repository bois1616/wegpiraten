# Runbook: Umstellung auf Kinder, Aufträge und Betreuungen

Stand 11.10.2026. Dieses Runbook beschreibt die kundenseitige Datenpflege. Den Hintergrund
erklärt das [Konzept](konzept_person_auftrag_leistung.md), die Felder und Regeln stehen im
[Datenmodell](datamodel_person_mandate_care.md). Für den CLI-Monatslauf gilt das
[Betriebs-Runbook](runbook_betriebsablauf.md).

Nach der Windows-Excel-Prüfung und Übergabe wird das finale Workbook die gemeinsame
Arbeitsgrundlage. Der Kunde pflegt dieses Workbook; die SQLite-Datenbank wird daraus und
aus den ausgefüllten Bögen neu aufgebaut. Befunde werden fachlich im Workbook korrigiert.

## Was sich geändert hat

| Vorher                                                                                                  | Jetzt                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Zwei Tabellen: «Klienten» (eine Zeile pro Auftrag, Kind und Auftrag vermischt) und «Relation Klient-MA» | Sechs Blätter: Kinder, Aufträge, Betreuungen, Ansprechpersonen, Zuordnung MA, Berichte                                                  |
| Klientennummer C1002                                                                                    | Kind behält C1002, der Auftrag heisst A-Jahr-Zähler, z.B. A26001. Die alte Nummer steht in der Bemerkung des Auftrags                   |
| Verlängerung überschreibt das Enddatum                                                                  | Verlängerung ist ein neuer Auftrag mit Vorgänger                                                                                        |
| Geschwister sind nicht darstellbar                                                                      | Geschwister tragen bei «Kinder» denselben Familientext, das jüngste Kind ist das Indexkind                                              |
| Mitarbeitende hängen am Klienten («Relation Klient-MA»)                                                 | Mitarbeitende hängen am Auftrag. Die Rolle P (primär) oder S (unterstützend) gilt nur für die Berichtspflichten                         |
| Berichte gab es in der Datenbank nicht                                                                  | Neu: Blatt «Berichte» mit Fälligkeit, Berichtsform, Status. Die Erstbefüllung stammt aus der Klientenübersicht (Farben im Monatsraster) |
| Kontrolle von Hand                                                                                      | Blätter «Prüfungen» (offene Punkte) und «Fehlerliste» (zeilenweise)                                                                     |

## Formeln nicht bearbeiten: hier keine Daten hineinkopieren

Nur Eingabefelder ändern. Berechnete und ausgeblendete Spalten nicht überschreiben,
leeren oder mit Daten aus anderen Dateien füllen. Auch «Nur Werte einfügen» zerstört
eine Formel, wenn der Zielbereich eine Formelzelle enthält. Die Blätter «Prüfungen»
und «Fehlerliste» sind berechnete Ansichten; dort keine Stammdaten eintragen.

Für den aktuellen Spaltenstand gilt:

| Blatt | Hier dürfen Daten eingegeben oder als Werte eingefügt werden | Nicht bearbeiten / nicht hineinkopieren |
| --- | --- | --- |
| Kinder | A:Q, einschliesslich Wohnort/Kontakt Kind | R:AG, berechnete Anzeigen und Prüfungen |
| Aufträge | A:Q | R:AP, berechnete Anzeigen, Verweise und Prüfungen |
| Betreuungen | A:L | M:AD, berechnete Anzeigen und Prüfungen |
| Zuordnung MA | A:E, einschliesslich Gültig ab / Gültig bis | F:Q, berechnete Anzeigen und Prüfungen |
| Ansprechpersonen | A:H, einschliesslich Telefon/E-Mail | I:P, berechnete Anzeigen und Prüfungen |
| Berichte | A:G | **H** (berechnete Auftrag-Nr) sowie I:T |
| Kostenträger | B:I, einschliesslich E-Mail Rechnung | Technische Überschriften nicht verändern |
| Bezugspersonen | A:I | J:N, Prüfungen |
| Kind-Bezugsperson | A:F | G:M, Anzeigen und Prüfungen |
| Platzierungen | A:K | L:Q, Prüfungen |
| Prüfkatalog | G:H (Kommentar/Bearbeitung) | A:F und I:J, fester Katalog und Berechnungen |

Bei «Berichte» wird der Auftrag in **B** ausgewählt. **H muss seine Formel behalten**;
der Import liest die berechnete Nummer aus H. Ein sichtbarer Auftrag in B genügt
nicht, wenn die Formel in H fehlt. Nach dem Anlegen einer Zeile kontrollieren, dass
Auftrag und berechnete Anzeigen erscheinen. Fehlt etwas, die Datei zur technischen
Prüfung an Stephan geben; keine Ersatzwerte in die Formelspalten schreiben.

Neue Datensätze innerhalb der jeweiligen Excel-Tabelle anlegen und nur die
Eingabefelder füllen. Beim Übernehmen eines bestehenden Datensatzes nur die oben
genannten Eingabefelder als Werte kopieren, keine ganze Zeile und keinen ganzen
Blattbereich. In «Berichte» nur A:G kopieren, damit H erhalten bleibt.
Neue Nummern selbst vergeben und auf Eindeutigkeit prüfen.

**Keine ganzen Blattzeilen ausschneiden oder verschieben.** Einen Auftrag oder eine Betreuung fachlich über die vorgesehenen
Enddaten beenden. Muss ein irrtümlicher Datensatz oder eine Vertretungszuordnung
entfernt werden, vorher eine Dateikopie sichern und die Entfernung mit Stephan
abstimmen. Danach Formeln und Fehlerliste prüfen. Datensätze nur über die jeweilige
Excel-Tabelle entfernen; nach Strukturänderungen vor dem Import neu berechnen und prüfen.

Beim Kundenstand vom 11.10.2026 enthalten die versteckten Zählspalten **Aufträge AP**,
**Betreuungen AD** und **Berichte T** insgesamt 15 defekte Formeln. Sie verursachen
die Bezugsfehler in der «Fehlerliste». Solange dort **#BEZUG! / #REF!** steht, ist
die Fehlerliste unbrauchbar; das bedeutet nicht, dass die Daten fehlerfrei sind.
Datei sichern und Stephan informieren. Den Fehler weder mit Leerwerten noch mit
einer Formel unterdrücken. Reparatur und vollständige Neuberechnung in Excel sind
in der separat vorbereiteten Kundenkopie vom 12.10.2026 erfolgt. Die ursprüngliche
Datei unter import/ bleibt unverändert. Die Abnahme mit Windows Excel steht noch aus,
siehe [DM-80 im Backlog](dev/backlog_umstellung_datenmodell.md#plan-2026-10-11-customer-workbook-review-and-requested-additions).

Kommentare werden in der vorbereiteten Kundenkopie im **Prüfkatalog, Spalte G**
bei der festen Prüfung-ID gepflegt. Spalte H nimmt Bearbeitungsnotizen auf.
«Prüfungen», Spalte G, zeigt den Kommentar automatisch an; dort nicht hineinkopieren.
Die sechs bisherigen Kundenkommentare wurden den festen Prüfungen zugeordnet.
Die Fehlerliste verlinkt die betroffenen Eingabezeilen. Bei Rückmeldungen immer
Prüfung-ID und Datensatznummer nennen.

### Bezugspersonen, Wohnorte und datierte Zuordnung MA

Eine erwachsene Person einmal in «Bezugspersonen» erfassen, mit eigener eindeutiger
Nummer, Namen, Wohnadresse, Telefon und E-Mail. In «Kind-Bezugsperson» wird diese
Nummer mit einem Kind verknüpft. Rolle und Sorgeberechtigung gelten je Verknüpfung;
dieselbe Person kann für mehrere Kinder unterschiedliche Rollen haben. Unbekannte
Sorgeberechtigung als «Unbekannt» erfassen. Das Feld «Familie» in «Kinder» bleibt
die bisherige Geschwisterkennung; eine gemeinsame Bezugsperson erzeugt keine Familie.

Die aktuelle Wohnadresse des Kindes steht in «Kinder», N:Q. Ein Aufenthalt in
einer Einrichtung oder Pflegefamilie kann zusätzlich in «Platzierungen» erfasst
werden. Bekannte Zeiträume eintragen; fehlende alte Angaben bleiben leer. Wohnadresse
der Bezugsperson und Wohnadresse des Kindes sind getrennte Angaben.

In «Zuordnung MA» je Auftrag, Mitarbeiter, Rolle und Zeitraum eine eigene Zeile
anlegen. Datumsgrenzen stehen in D:E. Beginn und Ende gelten einschliesslich. Für Berichte zählt die Fälligkeit:
ein am 31.07. endender P-Zeitraum ist für diesen Tag zuständig, der ab 01.08. beginnende
für spätere Fälligkeiten. P-Zeiträume dürfen sich nicht überschneiden. Ein leeres Ende
bedeutet fortlaufend; ein leerer Beginn bleibt unbekannt und begrenzt den Zeitraum
nicht nach hinten. Bisherige undatierte Zeilen gelten weiter und sind ausdrücklich
als historisch unbekannt gekennzeichnet. Beim ersten Wechsel auch die alte Zeile
mit einem Enddatum begrenzen. Historische Rollen und Zeilen nicht überschreiben
oder löschen. Die gemeinsame Tabelle dient Betreuung und Reporting.

Erfassungsbögen werden für alle Zuordnungen erzeugt, die den Leistungsmonat berühren,
je Auftrag und Mitarbeiter einmal. Bei einem Wechsel innerhalb des Monats können
beide Mitarbeitenden einen Bogen erhalten. Vergangene oder erst künftig beginnende
Zuordnungen ausserhalb des Monats erzeugen keinen Bogen.

Das Berichtsintervall erzeugt **keine** Berichtseinträge. Fälligkeiten müssen in
«Berichte» ausdrücklich eingetragen werden. Import und Reporting schreiben weder
Termine noch Zuständigkeiten in die Stammdatei zurück. Terminliste und Klientenübersicht
werden aus der aktuellen Stammdatei neu erzeugt; den Übersichtsreport nicht parallel
als zweite Datenquelle pflegen.

## Einmalig zu tun

Die Reihenfolge ist absichtlich so gewählt: Fehler zuerst, dann Fachfragen, dann die Ergänzungen.

1. **Blatt «Prüfungen» öffnen.** Es zeigt nur, was offen ist. «Fehler» sind zu bereinigen,
   «Hinweis» ist zu prüfen. Wer die Zeilen sucht, findet sie in der «Fehlerliste» oder über
   den Katalog rechts im Blatt «Prüfungen». Bei Bezugsfehlern zuerst den Abschnitt
   [Formeln nicht bearbeiten](#formeln-nicht-bearbeiten-hier-keine-daten-hineinkopieren)
   beachten.
2. **Geschäftsnummern beim Kostenträger P1000 (KJA) korrigieren.** Verbindlich ist
   yymmddnnn, zum Beispiel 260819008 für den achten Auftrag vom 19.08.2026. Das Datum ist das des Auftrags, nicht der Bewilligung.
   Aktuell weichen 14 Aufträge ab (Text wie «beendet» oder «on hold» statt Nummer), einer hat keine. Ob eine
   Bewilligung abgelaufen ist, sieht man am Feld «Bewilligung bis», nicht in der Geschäftsnummer.
3. **Rollen in «Zuordnung MA» prüfen.** Sie bestimmen, wer die Berichte erstellen muss. Pro Auftrag und Fälligkeitstag genau eine Person mit P. Bei Aufträgen mit
   nur einer Person setzt der Aufbau P selbst. Wer vertritt, wer dauerhaft betreut, entscheidet Wegpiraten.
4. **Familien erfassen**, wo Geschwister betreut werden. Im Blatt «Kinder» bei jedem der Geschwister
   dasselbe Wort in «Familie» eintragen, zum Beispiel «Muster Interlaken». Das jüngste Kind ist das Indexkind,
   dafür braucht jedes Kind der Familie ein Geburtsdatum (sonst ein Fehler). Ohne Familie gilt das
   Kind selbst als Indexkind. Eine Familie mit nur einem Kind meldet sich als Hinweis, meist ein Tippfehler.
5. **Folgeaufträge nachtragen**, wo die Klientenliste eine Verlängerung überschrieben hat.
   Bereits überführte Folgeaufträge sind zur Prüfung markiert. Wo Zeiträume fehlen,
   nennt Wegpiraten das Ende des alten und den Beginn des neuen Auftrags.
6. **Berichte durchsehen.** Die Liste ist aus der Klientenübersicht befüllt. Bei roten Zellen
   ohne Datum gilt der 15. des Monats. Abweichungen und aus dem Testbuild übernommene
   Angaben sind in der Befundliste zur fachlichen Prüfung genannt. Für vergangene Berichte
   fehlt der Status.
7. **Die Befundliste zum finalen Workbook prüfen.** Technische Grundsatzfragen wurden
   am 10.10.2026 beantwortet; Datenkorrekturen bleiben Aufgabe von Wegpiraten.

## Bei einem Ereignis zu pflegen

Reihenfolge bei einem ganz neuen Kind mit neuem Auftrag: Kind, Ansprechperson (falls neu),
Auftrag, Betreuung, Zuordnung MA, Berichte.

| Ereignis                                     | Kinder                                             | Aufträge                                           | Betreuungen                                         | Weiteres                                                                                |
| -------------------------------------------- | -------------------------------------------------- | -------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Neues Kind, erster Auftrag                   | neue Zeile                                         | neue Zeile                                         | neue Zeile                                          | Zuordnung MA, Berichte                                                                  |
| Kind war früher schon betreut                |                                                    | neue Zeile                                         | neue Zeile                                          |                                                                                         |
| Zweite Leistung für dasselbe Kind            |                                                    | neue Zeile                                         | neue Zeile                                          |                                                                                         |
| Geschwister kommt in einen laufenden Auftrag | neue Zeile, gleicher Familientext                  |                                                    | neue Zeile                                          |                                                                                         |
| Ein Kind tritt aus, der Auftrag läuft weiter |                                                    |                                                    | Austritt und Grund auf dieser Zeile                 |                                                                                         |
| Der ganze Auftrag endet                      |                                                    | «Bewilligung bis»                                  | Austritt auf allen Zeilen                           |                                                                                         |
| Verlängerung                                 |                                                    | neuer Auftrag mit Vorgänger                        | neue Zeile je weiterbetreutem Kind, Eintritt bleibt | Zuordnung MA und Berichte übernehmen                                                    |
| Neugeborenes in der Familie                  | neue Zeile mit Geburtsdatum, gleicher Familientext | neuer Auftrag mit Vorgänger, für die ganze Familie | neue Zeile für das Neugeborene, falls betreut       | Das Indexkind wechselt von selbst zum jüngsten Kind                                     |
| Vertretung, Krankheit, Ferien                |                                                    |                                                    |                                                     | S-Zeile in «Zuordnung MA» mit Beginn/Ende ergänzen und historisch behalten                |
| Dauerhafter Wechsel der Betreuung            |                                                    |                                                    |                                                     | Zuordnung anpassen, Rolle P neu setzen, damit die richtige Person die Berichte erstellt |
| Kontingent ändert sich                       |                                                    | neuer Auftrag (Folgeauftrag)                       |                                                     |                                                                                         |
| Umzug der Familie                            | Wohnort ändern                                     |                                                    |                                                     |                                                                                         |
| AHV-Nummer wird nachgereicht                 | eine Zelle                                         |                                                    |                                                     |                                                                                         |
| Bericht erledigt                             |                                                    |                                                    |                                                     | Status «erledigt», «Erledigt am» eintragen                                              |

Bei einer Vertretung bleibt die Rolle P auf der Stammperson, sie erstellt weiterhin die Berichte. Die Erfassungsbögen
entstehen für jede Zeile der Zuordnung, deshalb die Vertretung nach dem Einsatz wieder
entfernen, sonst entsteht ein Bogen ohne Stunden.
Bis zur Formelreparatur gilt dafür das oben beschriebene Vorgehen für das Entfernen
von Zuordnungen; keine ganze Blattzeile löschen.

### Monatliche Terminlisten für Berichte

Nach Änderungen im Workbook die Arbeitsdatenbank wie im Betriebsworkflow neu aufsetzen
und die Stammdaten importieren. Danach die Terminlisten für den gewünschten Monat erstellen:

```bash
make terminliste MONTH=2026-10
```

Im konfigurierten Ausgabeverzeichnis entsteht der Ordner `Terminlisten_2026-10`, mit
`Terminliste_2026-10_<MA-ID>.xlsx` je Mitarbeitenden. Auch Mitarbeitende ohne fällige Berichte
bekommen eine Datei mit entsprechendem Hinweis. Der Timesheet-Schalter hat keinen Einfluss.
Die Erstellung läuft separat von den Zeiterfassungsbögen.

Aufgenommen werden Berichte mit «Fällig am» im gewählten Monat, ausser mit Status «erledigt»
oder «entfällt». Auch Einträge ohne Status werden aufgenommen. Die Liste zeigt Fälligkeit,
Auftrag, Indexkind, Leistungsart, Leistungsbesteller, Berichtsform, Status, Notizen und Bericht-ID,
sortiert nach Fälligkeit und Auftrag. Berichtsformen sind Text; Rhythmen erzeugen keine Termine.
Auch Berichte nach dem Ende eines Auftrags können fällig sein.

Zuständig ist die Person mit Rolle P am **Fälligkeitstag** aus «Zuordnung MA».
Ohne Datumsgrenzen bleibt die bisherige Zuordnung gültig; die Ausgabe kennzeichnet
die historische Zuständigkeit als unbekannt. Eine Lücke, Überschneidung oder ungültige
Datumsangabe führt zu einem Befund; es wird keine andere Person ersatzweise gewählt.
Fehlt eine zuständige Person, meldet das Log den
Bericht und Auftrag als Warnung; der Eintrag wird ausgelassen und der Export läuft weiter.
Dasselbe gilt bei mehreren P, einem fehlenden Auftrag oder einer fehlenden Person in den
Mitarbeiter-Stammdaten. Solche Befunde im Workbook korrigieren, die Arbeitsdatenbank neu
aufsetzen und die Listen erneut erzeugen. Ein erneuter Lauf überschreibt die Dateien dieser
Mitarbeitenden für denselben Monat.

### Zuordnung MA mit Zeiträumen pflegen

Die bestehende Excel-Tabelle **`relation_mandate_emp`** im Blatt «Zuordnung MA»
bleibt die einzige Zuordnungsquelle. Eingaben stehen in A:E: Auftrag,
Mitarbeiter, Rolle, `valid_from` und `valid_to`. Datumsfelder als echte Excel-Daten
erfassen. Offene Grenzen dürfen leer bleiben. Beide Grenzen zählen mit. P bezeichnet
die Berichtszuständigkeit, S eine Unterstützung. Zwei P-Zeiträume desselben Auftrags
dürfen sich nicht überschneiden. Wiederkehrende Mitarbeiter erhalten weitere Zeilen
mit den jeweiligen Zeiträumen. Für einen Wechsel die alte Zeile beenden und eine
neue anlegen; die alte Rolle nicht nachträglich auf S ändern.

Beispiel: M0567 ist für A26123 vom 01.01.2026 bis 31.07.2026 zuständig, M0123 vom
01.08.2026 bis 31.12.2026, M0789 ab 01.01.2027. Der im Oktober fällige Bericht
erscheint bei M0123. Eine spätere Erledigung ändert diese Zuordnung nicht.
Bei einem Folgeauftrag dessen eigene A-Nummer in den neuen Zeiträumen verwenden.

Abgeschlossene Zeiträume in der Mappe behalten. Nach jedem DB-Neuaufbau liest der
Import sie erneut ein; Terminlisten und Klientenübersicht berechnen daraus die
Zuständigkeit. Sie schreiben diese weder in die Kundenmappe zurück noch erzeugen
sie zusätzliche Berichtstermine. Alte Mappen ohne die neuen Datumsspalten bleiben
importierbar; ihre Zuordnungen gelten ohne Datumsgrenzen. Ein separates Blatt
«Zuständigkeitsverlauf» wird nicht mehr verwendet.

### Klientenübersicht neu erzeugen

```bash
make klientenuebersicht MONTH=2026-10
```

Im konfigurierten Output entsteht
`Klientenuebersichten_2026-10/Klientenuebersicht_2026-10.xlsx`. Die Mappe enthält
eine Legende vor den Mitarbeiterblättern, das Monatsraster für 2026 und 2027,
«Berichtsdetails» und «Nicht zugeordnet». Ein Sammelblatt «Übersicht» gibt es nicht.
Die mehrfachen Vor-/Nachnamensspalten der alten Datei entfallen.

Eine Zeile entspricht einem ausdrücklich genannten Auftrag mit Berichtsterminen
im Raster. Folgeaufträge und parallele Leistungen bleiben getrennt. Termine werden
nach Fälligkeit zugeordnet; alle Statuswerte bleiben sichtbar. Mehrere Termine in
einem Monat stehen einzeln mit Datum, Form, Bericht-ID und Status in der Zelle.
Rot bedeutet Bericht, Orange Zwischenbericht, Blau Abschlussbericht. Bei gemischten
Berichtsformen ist die Zelle grau. «Berichtsdetails» enthält jeden importierten
Bericht genau einmal; fehlende Zuordnungen und Termine ausserhalb des Rasters
erscheinen zusätzlich unter «Nicht zugeordnet».

G:N zeigen den aktuellen **importierten Stand des angezeigten Auftrags**:
Bewilligungsbeginn/-ende, operative MA-Zuordnung, Kontingente in Stunden pro Monat
und Leistungsart. Diese Angaben belegen keinen früheren Auftragsstand. Die heutige
MA-Zuordnung in I kann von der datierten Berichtszuständigkeit abweichen.
Die Telefonnummer kommt aus dem optionalen Feld `phone` bei Ansprechpersonen.

Die Ausgabe jeden Monat neu erzeugen. Fachliche Änderungen ausschliesslich in der
Stammdatenmappe pflegen, neu importieren und die Ausgabe erneut erstellen; keine
manuell weitergeführte Kopie als zweite Datenquelle. Vor dem nächsten Kundenimport
prüft der Agent die gesamte aktuelle Stammdatenmappe. Offene Datenfehler dürfen
diesen Import weiterhin scheitern lassen. Zeilen und Spalten sind im Export
bereits fixiert; das Monatsraster beginnt nach den Stammdaten in O.

### Typische Vorgänge

Die Tabelle oben sagt, welche Blätter betroffen sind. Hier stehen die Schritte in der
Reihenfolge, in der man sie ausführt. Nach jedem Vorgang kurz ins Blatt «Prüfungen» oder in
die «Fehlerliste» schauen.

**Neues Kind anlegen** (Blatt «Kinder»)

1. Nächste freie Kind-Nr eintragen (C und vier Ziffern).
2. Name, Geburtsdatum, Geschlecht, UMA/UMF, Wohnkanton, Sprache und AHV-Nummer erfassen.
   Für Accordix sind Geburtsdatum, Geschlecht, UMA/UMF und Wohnkanton Pflicht.
3. Kurzzeichen bilden: zwei Buchstaben vom Vornamen, zwei vom Nachnamen (MaSt). Ist es schon
   vergeben, eine Ziffer anhängen (MaSt2).
4. «Familie» nur bei Geschwistern füllen, mit demselben Text wie beim Geschwisterkind.
5. Solange das Kind keinen Auftrag hat, meldet die Prüfung «Kind ohne jede Betreuung». Das ist
   normal und verschwindet mit dem nächsten Schritt.

**Neuen Auftrag anlegen**

1. Ist das Kind schon erfasst? Sonst zuerst anlegen. Ist die Ansprechperson erfasst? Sonst
   im Blatt «Ansprechpersonen» eine Zeile beim richtigen Leistungsbesteller anlegen.
2. Blatt «Aufträge»: nächste Auftrag-Nr (A, Startjahr, nächster freier Zähler), Leistungsart,
   Leistungsbesteller, Ansprechperson, Kostenträger, Standort, Geschäftsnummer, Bewilligung von
   und bis, Kontingent, Zuweisungsgrundlage. Beim KJA (P1000) ist die Geschäftsnummer
   yymmddnnn, mit dem Datum des Auftrags.
3. Blatt «Betreuungen»: Auftrag-Nr, Kind-Nr und Eintritt, das ist der Beginn der Betreuung
   dieses Kindes. Bei Geschwistern eine Zeile je betreutem Kind.
4. Blatt «Zuordnung MA»: eine Zeile je Mitarbeitende. Die Person, die die Berichte erstellt,
   bekommt die Rolle P. Bekannten Beginn in P eintragen, Ende in Q, falls bekannt.
5. Blatt «Berichte»: die fälligen Berichte eintragen (Auftrag, Berichtsform, Fällig am).
   Bei regelmässigen Berichten den Rhythmus am Auftrag ergänzen.

**Verlängerung erfassen** (bestehenden Auftrag kopieren)

1. Im Blatt «Aufträge» eine neue Tabellenzeile anlegen und nur die Eingabefelder A:Q
   des bisherigen Auftrags als Werte übernehmen. Keine ganze Blattzeile kopieren.
   Die alte Zeile bleibt unverändert, auch «Bewilligung bis».
2. In der Kopie ändern: Auftrag-Nr, «Bewilligung von» (Tag nach dem alten Ende), «Bewilligung
   bis», Geschäftsnummer, wenn nötig Kontingent und Ansprechperson, dazu «Vorgängerauftrag»
   (Auswahl, der alte Auftrag) und die Bemerkung. Wer die Auftrag-Nr vergisst, sieht «Auftrag-Nr
   doppelt». Wer beim KJA die Geschäftsnummer vergisst, sieht «kommt mehrfach vor».
3. Im Blatt «Betreuungen» neue Tabellenzeilen anlegen und nur die Eingabefelder A:L
   der bisherigen Betreuungen als Werte übernehmen. Auftrag-Nr ändern, Eintritt
   beibehalten und Austritt leeren. Die Formelspalten bleiben erhalten.
4. Im Blatt «Zuordnung MA» neue Tabellenzeilen anlegen, nur A:C als Werte übernehmen
   und die Auftrag-Nr ändern. Die Rollen bleiben; D:E für den neuen Auftrag neu
   festlegen und keine alten Enddaten blind kopieren.
5. Im Blatt «Berichte» die Berichte des neuen Auftrags eintragen.
6. Beim alten Auftrag bleibt der Hinweis «Bewilligung abgelaufen, Betreuung noch offen» stehen,
   solange seine Betreuung keinen Austritt trägt. Bei einer Verlängerung ist das kein Fehler.

**Neugeborenes in der Familie**

1. Kind mit Geburtsdatum und demselben Familientext anlegen. Das Indexkind wechselt damit von
   selbst zum Neugeborenen.
2. Den laufenden Auftrag wie bei einer Verlängerung kopieren. Er gilt für die ganze Familie, auch
   wenn das Neugeborene nicht betreut wird. Vorgänger eintragen.
3. Betreuungen für alle betreuten Kinder kopieren, für das Neugeborene eine neue Zeile, falls es
   betreut wird.
4. Zuordnung MA und Berichte wie bei der Verlängerung.

**Auftrag oder Betreuung beenden**

1. Tritt ein Kind aus, dessen Betreuungszeile öffnen: Austritt, Grund und Situation danach eintragen.
   Der Auftrag bleibt, solange andere Kinder weiterlaufen.
2. Endet der ganze Auftrag, in «Aufträge» «Bewilligung bis» setzen und bei allen Betreuungen den
   Austritt eintragen.
3. Die Zuordnungen in «Zuordnung MA» prüfen und mit «Gültig bis» beenden. Die Zeilen
   bleiben zur historischen Zuordnung erhalten.
   Abgelaufene Bewilligungen werden bei der Bogenerzeugung bereits berücksichtigt.

**Vertretung**

Tabellenzeile in «Zuordnung MA» mit Rolle S und Beginn/Ende in D:E ergänzen.
Nach dem Einsatz das Ende vervollständigen und die Zeile behalten.

### Regeln, die man sich merken muss

- **Bewilligung bis ist nicht Austritt.** Die Bewilligung steht auf dem Papier der Behörde, der
  Austritt ist das, was passiert ist. Der Austritt gehört auf die Betreuung des Kindes.
- **Auftragsnummern ändern sich nie.** Ein neuer Auftrag bekommt A, das Startjahr und den
  nächsten freien Zähler dieses Jahres, auch wenn er früher beginnt als ein bestehender. Die
  Nummer wird von Hand vergeben.
- **Der Eintritt wird von Hand erfasst.** Er darf älter sein als der erste erfasste Auftrag und
  bleibt bei einer Verlängerung gleich.
- **Geschäftsnummer beim KJA immer yymmddnnn.** Bei anderen Kostenträgern Freitext, nie leer.
- **Bei jeder Auftragserfassung fragen,** ob im selben Haushalt weitere Kinder betreut werden.
  Ein nicht erfasstes Geschwisterkind findet keine Prüfung.
