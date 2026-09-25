# Runbook: Umstellung auf Kinder, Aufträge und Betreuungen

Stand 25.09.2026. Was sich geändert hat, was einmalig zu tun ist und was künftig bei welchem
Ereignis gepflegt wird. Den Hintergrund erklärt das [Konzept](konzept_person_auftrag_leistung.md),
die Felder und Regeln stehen im [Datenmodell](datamodel_person_mandate_care.md). Der
monatliche Abrechnungslauf bleibt wie im [Betriebs-Runbook](runbook_betriebsablauf.md), bis die
Programme auf das neue Modell umgestellt sind.

Arbeitsdatei ist vorerst `sandbox/wegpiraten_datenbank_neu.xlsx`. Sie ist ein Testbuild aus
der Klientenliste vom 24.09.2026, keine Produktivdatei.

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

## Einmalig zu tun

Die Reihenfolge ist absichtlich so gewählt: Fehler zuerst, dann Fachfragen, dann die Ergänzungen.

1. **Blatt «Prüfungen» öffnen.** Es zeigt nur, was offen ist. «Fehler» sind zu bereinigen,
   «Hinweis» ist zu prüfen. Wer die Zeilen sucht, findet sie in der «Fehlerliste» oder über
   den Filter «prüfen» im «Prüfkatalog».
2. **Geschäftsnummern beim Kostenträger P1000 (KJA) korrigieren.** Verbindlich ist
   yymmddnnn, zum Beispiel 260819008 für den achten Auftrag vom 19.08.2026. Das Datum ist das des Auftrags, nicht der Bewilligung.
   Aktuell weichen 14 Aufträge ab (Text wie «beendet» oder «on hold» statt Nummer), einer hat keine. Ob eine
   Bewilligung abgelaufen ist, sieht man am Feld «Bewilligung bis», nicht in der Geschäftsnummer.
3. **Rollen in «Zuordnung MA» prüfen.** Sie bestimmen nur, wer die Berichte erstellen muss. Pro Auftrag genau eine Person mit P. Bei Aufträgen mit
   nur einer Person setzt der Aufbau P selbst. Wer vertritt, wer dauerhaft betreut, entscheidet Wegpiraten.
4. **Familien erfassen**, wo Geschwister betreut werden. Im Blatt «Kinder» bei jedem der Geschwister
   dasselbe Wort in «Familie» eintragen, zum Beispiel «Muster Interlaken». Das jüngste Kind ist das Indexkind,
   dafür braucht jedes Kind der Familie ein Geburtsdatum (sonst ein Fehler). Ohne Familie gilt das
   Kind selbst als Indexkind. Eine Familie mit nur einem Kind meldet sich als Hinweis, meist ein Tippfehler.
5. **Folgeaufträge nachtragen**, wo die Klientenliste eine Verlängerung überschrieben hat.
   Erledigt für Yahia, Nipote (Yarrah Orion) und Gorlov. Offen für Duarte Torres und Loosli:
   Wegpiraten nennt das Ende des alten und den Beginn des neuen Auftrags.
6. **Berichte durchsehen.** Die Liste ist aus der Klientenübersicht befüllt. Bei roten Zellen
   ohne Datum gilt der 15. des Monats. Was von den Mitarbeiterblättern abweicht, steht in
   `sandbox/klaerung_berichte_2026-09-25.md`. Für vergangene Berichte fehlt der Status.
7. **Die offenen Fachfragen beantworten** (siehe Konzept, Abschnitt «Was offen ist»).

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
| Vertretung, Krankheit, Ferien                |                                                    |                                                    |                                                     | Zeile in «Zuordnung MA» ergänzen, danach entfernen                                      |
| Dauerhafter Wechsel der Betreuung            |                                                    |                                                    |                                                     | Zuordnung anpassen, Rolle P neu setzen, damit die richtige Person die Berichte erstellt |
| Kontingent ändert sich                       |                                                    | neuer Auftrag (Folgeauftrag)                       |                                                     |                                                                                         |
| Umzug der Familie                            | Wohnort ändern                                     |                                                    |                                                     |                                                                                         |
| AHV-Nummer wird nachgereicht                 | eine Zelle                                         |                                                    |                                                     |                                                                                         |
| Bericht erledigt                             |                                                    |                                                    |                                                     | Status «erledigt», «Erledigt am» eintragen                                              |

Bei einer Vertretung bleibt die Rolle P auf der Stammperson, sie erstellt weiterhin die Berichte. Die Erfassungsbögen
entstehen für jede Zeile der Zuordnung, deshalb die Vertretung nach dem Einsatz wieder
entfernen, sonst entsteht ein Bogen ohne Stunden.

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
   bekommt die Rolle P.
5. Blatt «Berichte»: die fälligen Berichte eintragen (Auftrag, Berichtsform, Fällig am).
   Bei regelmässigen Berichten den Rhythmus am Auftrag ergänzen.

**Verlängerung erfassen** (bestehenden Auftrag kopieren)

1. Im Blatt «Aufträge» die Zeile des bisherigen Auftrags kopieren und darunter einfügen. Die
   alte Zeile bleibt unverändert, auch «Bewilligung bis».
2. In der Kopie ändern: Auftrag-Nr, «Bewilligung von» (Tag nach dem alten Ende), «Bewilligung
   bis», Geschäftsnummer, wenn nötig Kontingent und Ansprechperson, dazu «Vorgängerauftrag»
   (Auswahl, der alte Auftrag) und die Bemerkung. Wer die Auftrag-Nr vergisst, sieht «Auftrag-Nr
   doppelt». Wer beim KJA die Geschäftsnummer vergisst, sieht «kommt mehrfach vor».
3. Im Blatt «Betreuungen» die Zeilen des alten Auftrags kopieren und nur die Auftrag-Nr
   ändern. Der Eintritt bleibt gleich, der Austritt leer.
4. Im Blatt «Zuordnung MA» die Zeilen kopieren und die Auftrag-Nr ändern. Die Rollen bleiben.
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
3. Die Zeilen in «Zuordnung MA» entfernen, sonst entstehen weiter Erfassungsbögen.

**Vertretung**

Zeile in «Zuordnung MA» mit Rolle S ergänzen, nach dem Einsatz wieder entfernen.

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

## Für die Umsetzung in den Programmen

Erst nach der Annahme des Modells durch Stephan, vorher bleiben `src/` und die Datenbank unberührt.

1. Import: `import-master` liest die neuen Blätter (Kinder, Aufträge, Betreuungen,
   Ansprechpersonen, Zuordnung MA, Berichte) statt der Klientenliste. Die Zuordnung der
   Blätter zu den Tabellen steht in `DEFAULT_TABLE_MAPPINGS`.
2. Rechnung und Zeiterfassung: die Verbindung `JOIN clients` in `invoice_processor.py` und
   `client_data.py` wird zur Verbindung auf `mandate`. Die Buchungsdaten bleiben.
3. Nummern: `service_data.client_id` von `C…` auf die neue Auftragsnummer umstellen. Archivierte
   Erfassungsbögen tragen die alte Nummer in Zelle G8, dort muss der Import beide Formen kennen.
   Auch bestehende Rechnungsnummern ändern sich, weil die Rechnungsnummer aus der
   Auftragsnummer entsteht.
4. Danach die monatliche Aufgabenliste je Mitarbeitende aus der Berichtsliste. Sie soll am
   Monatsanfang zusammen mit den Erfassungsbögen entstehen. Ob im selben Lauf oder als eigenes
   Programm daneben, ist noch zu entscheiden.
5. Bereinigung der Altdaten nach der Migration der echten Daten. Was die Prüfungen dabei
   aufdecken, gehört zum Zweck der Übung.
