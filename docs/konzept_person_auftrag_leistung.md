# Konzept: Kinder, Aufträge und Betreuungen

Stand 25.09.2026. Zusammenfassung der neuen Datenstruktur und dessen, was sie leistet.
Die Felder und Prüfregeln stehen in [datamodel_person_mandate_care.md](datamodel_person_mandate_care.md),
was jetzt zu tun ist im [Runbook zur Umstellung](runbook_umstellung_datenmodell.md).

## Worum es geht

Bisher stand in der Klientenliste eine Zeile pro Auftrag, und in dieser Zeile steckten drei
Dinge zugleich: das Kind, die Bewilligung der Behörde und die Betreuung des Kindes in dieser
Bewilligung. Solange ein Kind genau einen Auftrag hat und ein Auftrag genau ein Kind betrifft,
geht das gut. Sobald Geschwister betreut werden, ein Kind zwei Aufträge hat oder ein Auftrag
verlängert wird, muss man Daten doppelt pflegen oder überschreiben.

Anlass war die Accordix-Meldung. Accordix verlangt eine Zeile pro Kind und Leistung, die
Abrechnung läuft aber pro Auftrag. Beide Sichten passen nicht in eine Tabelle.

## Die neue Struktur

Statt der bisherigen zwei Listen (Klienten und Zuordnung der Mitarbeitenden) gibt es sieben, die je eine
Frage beantworten. Die Berichtsliste ist ganz neu, es gab bisher keine.

| Liste | Frage | Eine Zeile ist |
|---|---|---|
| Kinder | Wer wird betreut? | ein Kind, genau einmal |
| Aufträge | Was hat die Behörde bewilligt? | ein Auftrag |
| Betreuungen | Welches Kind wird in welchem Auftrag betreut, von wann bis wann? | ein Kind in einem Auftrag |
| Familien | Welche Kinder gehören zusammen, und über wen wird abgerechnet? | eine Familie mit Geschwistern |
| Ansprechpersonen | Wer ist beim Leistungsbesteller zuständig? | eine Person bei einem Besteller |
| Zuordnung MA | Wer arbeitet auf welchem Auftrag? | eine Mitarbeitende an einem Auftrag |
| Berichte | Welche Berichte sind wann fällig? | ein Bericht zu einem Auftrag |

Die Betreuungsliste wirkt zuerst wie ein Umweg. Sie ist es nicht: Jede Zeile darin ist genau
eine Zeile der Accordix-Meldung. Wer wissen will, wie sie aussieht, legt die Meldedatei
daneben.

## Wofür die Struktur geeignet ist

**Für Accordix.** Jede Betreuung ist eine Meldezeile, mit dem Eintritt und Austritt dieses
Kindes. Die Bewilligung «bis» und der Austritt sind zwei verschiedene Angaben in zwei Listen,
die Sonderregel für die Meldung vom August entfällt. Ein Geschwisterkind kann nicht mehr
lautlos fehlen, sobald es eine Betreuungszeile hat. Der Eintritt wird von Hand erfasst, weil
er älter sein kann als jeder erfasste Auftrag.

**Für Geschwister.** Bei mehreren Kindern läuft der Auftrag über das jüngste Kind, das
Indexkind. Die Familie hält das fest, an einer einzigen Stelle. Die Rechnung entsteht einmal,
die Accordix-Meldung enthält trotzdem beide Kinder. Das Kontingent steht einmal am Auftrag und
wird einmal geprüft.

**Für Folgeaufträge.** Eine Verlängerung ist ein neuer Auftrag mit Verweis auf den
vorherigen. So entsteht eine Kette, in der man sieht, was früher bewilligt war, mit welchem
Kontingent und bei wem. Bisher wurde bei einer Verlängerung das Enddatum überschrieben, und
das alte Kontingent war weg. Shanice Richards ist das Lehrbeispiel: Der erste Auftrag lief
mit 30 Stunden bis August 2026, der Folgeauftrag mit 20 Stunden bis Februar 2027. In der alten
Liste stand nur noch der zweite. Kommt ein Kind zur Welt, endet der laufende Auftrag und ein
neuer beginnt, für die ganze Familie. Das ist auch dann so, wenn das Neugeborene selbst nicht
betreut wird.

**Für wechselnde Mitarbeitende.** Die Mitarbeitenden hängen am Auftrag, nicht am Kind. Wer
eine Vertretung wegen Krankheit oder Ferien einsetzt, ergänzt eine Zeile in der Zuordnung und
nimmt sie danach wieder heraus. Aus der Zuordnung entstehen die Erfassungsbögen, für jede
zugeordnete Person einer. Auf Rechnung und Kontingent hat das keinen Einfluss. Eine Person
pro Auftrag gilt als primäre Betreuungsperson (die der KESB benannte), die anderen als
unterstützend. Diese Rolle zählt nur für die Berichtspflichten: Sie bestimmt, wer die Berichte
bekommt, nicht wer Erfassungsbögen erhält oder abrechnet.

**Für die Rechnung.** Die Rechnungsnummer läuft über die Auftragsnummer und ist damit
eindeutig, auch wenn ein Kind zwei Aufträge zugleich hat. Bei Perren, Burri, Levic und Zwinggi
Challco trifft das schon heute zu.

**Für saubere Personendaten.** Ein Kind steht genau einmal da. Ein Geburtsdatum, das einmal
als Datum und einmal als Zahl erfasst ist (Burri), kann nicht mehr entstehen. Eine
nachgereichte AHV-Nummer wird an einer Stelle eingetragen.

**Für die Berichte.** Berichte hängen am Auftrag, berichtet wird über die Familie. Die Liste
kennt Bericht, Zwischenbericht und Abschlussbericht. Zuständig ist automatisch die primäre
Betreuungsperson. Ein Bericht ohne erkennbare zuständige Person wird markiert.

**Für die Kontrolle der Daten.** Das Workbook prüft sich selbst: fehlende Pflichtangaben,
Verweise ins Leere, doppelte AHV-Nummern, abgelaufene Bewilligungen mit offener Betreuung,
Geschäftsnummern, die nicht zur Notation des Kantonalen Jugendamts passen. Das Blatt
«Prüfungen» zeigt nur, was offen ist.

## Was entschieden ist

- Das Kontingent gilt je Auftrag und kann sich bei einem Folgeauftrag ändern.
- Ein Auftrag gilt für die ganze Familie. Ändert sich die Zuweisungsgrundlage oder kommt ein
  Neugeborenes dazu, gibt es einen neuen Auftrag.
- Auftragsnummern haben die Form A + Jahr + Zähler (A26001) und ändern sich nach der Vergabe
  nie mehr.
- Die Geschäftsnummer des Kantonalen Jugendamts (Kostenträger P1000) hat die Form
  yymmddnnn, mit dem Datum des Auftrags. Bei allen anderen Kostenträgern ist es Freitext, fehlen
  darf sie nie.
- Berichte werden je Auftrag geführt und betreffen die Familie.
- Die Zeiterfassung und die Rechnungen ändern sich für die Mitarbeitenden nicht.

## Was offen ist

- Worin sich Bericht und Zwischenbericht unterscheiden, und ob jeder Auftrag einer Kette einen
  Abschlussbericht bekommt.
- Ob es Berichtsrhythmen gibt, die zum Leistungsbesteller gehören statt zum Auftrag.
- Wie die KESB-Nummern (meist yyyy-nnnn) künftig behandelt werden sollen.
- Woher der Erledigt-Stand der vergangenen Berichte kommt.
- Die Verlängerungen bei zwei Kindern (Duarte Torres, Loosli): Wann endete der alte Auftrag?
- Die AHV-Nummer bei Caroline und Marlon Til Stauffer.

## Was das Konzept nicht löst

Die Sorgeberechtigten sind nicht erfasst. Die Ansprechperson gehört zum Leistungsbesteller,
nicht zur Familie. Geschwister erkennt das System deshalb nicht selbst. Wer ein Geschwisterkind
nie erfasst, dessen Fehlen sieht keine Prüfung. Bei jeder Auftragserfassung gehört deshalb die
Frage dazu, ob im selben Haushalt weitere Kinder betreut werden.
