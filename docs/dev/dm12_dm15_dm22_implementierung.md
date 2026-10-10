# Auftrags-View, SA und alte Nummern: implementierter Vertrag

Stand 10.10.2026. Stephan hat die Umsetzung und den September-Vergleich beauftragt.
Die vorherigen Entwürfe sind durch den folgenden implementierten und getesteten Vertrag
konkretisiert. Technisches Review und Implementierung: Codex/GPT-6, genaue Variante nicht
angegeben; kein unabhängiges Opus/Astra-Review behauptet.

## DM-12/13: `v_mandate`

Eine Zeile je Auftrag, zusätzlich der technische Auftrag SA. Kinder, Betreuungen und Kontakte
werden mit LEFT JOIN verbunden; ein ungültiger Verweis verschluckt keinen Auftrag.
Das erste Betreuungskind nach `source_row` bestimmt die Familie. Ohne Familie ist es das
Indexkind; sonst gewinnt das jüngste Kind aller Kinder dieser Familie, auch unbetreute Kinder.
Bei gleichen Geburtstagen entscheidet die Herkunftszeile wie im Workbook. Familienvergleiche
verwenden einen aus dem Originaltext abgeleiteten Unicode-Casefold-Schlüssel; der Originaltext
bleibt erhalten. Historie wird nicht rekonstruiert: es gilt das heutige Indexkind.

Budgetwerte werden beim Import einmal von Stunden in Minuten umgerechnet. Die View
multipliziert nicht nochmals. Kontakte liefern die drei `sr_ap_*`-Felder. `client_id` und
`service_type` bleiben ausschliesslich View-Aliase für vorhandene Bogen-/Template-Schnittstellen;
physische Tabellen `clients` und `relation_client_emp` gibt es nicht mehr.

Verifikation: synthetische Geschwister, unbetreutes jüngstes Kind, Reihenfolge bei gleichen
Geburtstagen, fehlender Kontakt, 0,5 Stunden = 30 Minuten. Alle 94 Indexkind-Zuordnungen des
finalen Workbooks werden im September-Prüfpaket mit der View abgeglichen.

## DM-15: SA

Der Import legt SA in `mandate` an, ohne Kind, Betreuung oder MA-Zuordnung. Leistungsart ST999,
Code SONST, Budget 1000/1000/500 Minuten. Kein Kostenträger, kein Besteller, keine Geschäftsnummer.
SA wird nicht fakturiert und nicht an Accordix gemeldet, bleibt aber im Arbeitszeitprotokoll.
Normale Pflichtprüfungen für Auftrag/Indexkind gelten hier nicht. Interne Bögen entstehen wie
bisher ausschliesslich für Mitarbeitende mit TS=WAHR; normale Bögen behalten ihren bisherigen
Default bei leerem TS.

## DM-22/23: Legacy-Zuordnung

Quelle: `resources/legacy_mandate_mapping.json`, exportiert aus den eingefrorenen Nummern,
ohne Namen/AHV-Nummern. Der Pfad steht in `DatabaseConfig.legacy_mandate_mapping` und kann in
YAML überschrieben werden. Keine Abhängigkeit von der später aufzulösenden Sandbox.

Bekannte A-ID/SA: unmittelbar. C-ID: alte Auftrags-ID, nicht Kinderfilter. Ein Kandidat wird
verwendet; Leistungen ausserhalb der Bewilligung werden gewarnt. Bei mehreren Kandidaten
entscheidet das Leistungsdatum inklusive Grenzen gegen die aktuellen Bewilligungszeiträume.
Null oder mehrere Treffer, unbekannte Nummer oder fehlender Kandidat: betroffene Datei bleibt
im Import, keine ihrer Zeilen wird gespeichert. Andere Dateien laufen weiter. Jeder DB-Fehler
rollt die ganze Datei zurück. Typ, Tarif, Standort und Budget kommen je Zeile vom bestimmten
Auftrag. Abweichende Bogenbudgets werden gewarnt; massgeblich ist das aktuelle Auftragskontingent.

Verifikation: beide Grenztage eines Folgeauftrags, ein Bogen über die Grenze, unterschiedliche
Budgets, Überlappung, unbekannte Nummer, SA und Datei-Rollback. Neue Bögen können ausgefüllt und
mit denselben konfigurierten Kopfzellen wieder importiert werden.

## Importbefunde

Technisch fehlende Tabellen/Spalten schlagen vor dem Import fehl. Nicht verwendbare Zeilen
werden mit Warnung ausgelassen; doppelte Schlüssel behalten die erste Zeile. Fachlich ungültige
FKs bleiben zur Nacharbeit erhalten und werden diagnostiziert, statt ganze Batches zu verlieren.
Bewusst keine physischen FK-Constraints auf den Stammdaten; `service_data` behält seine FKs.
Selbstverweise/Forks, fehlendes Indexkind, KJA-Nummern (Format/Datum/Duplikat), fehlende
Geschäftsnummer und übernommene Prüfnotizen werden diagnostiziert. Eine Ansprechperson mit
widersprüchlicher Anrede wird ebenfalls zur Kundenprüfung markiert. Das ist der P0-Umfang;
DM-61 ergänzt die restlichen Workbook-Hinweise.

Nicht berechenbare Rechnungen werden mit Warnung ausgelassen. Erstellbare Rechnungen mit
Befunden bekommen `PRÜFEN` im Dateinamen und eine entsprechende Spalte in der Übersicht.
`Ohne Berechnung` bleibt eine sichtbare Position mit Betrag 0 CHF; keine automatisch erzeugten
Minuten, keine ST99-Ableitung. Leere Datumscaches (`NaT`) und fehlende Textwerte (`NaN`) werden
nicht als erfundene Datums- oder AHV-Texte ausgegeben.

## Accordix und Arbeitszeit

Accordix meldet nur konfigurierte Kostenträger (initial P1000). Eintritt und Austritt kommen
von der Betreuung, niemals vom Bewilligungsende. Fortlaufende Betreuung desselben Kindes über
eine Kette mit gleicher Leistungsart und gleichem Eintritt wird einmal gemeldet. Für den
Monat passende Folgeauftragszeilen werden nicht doppelt ausgegeben; unverbundene Aufträge und
andere Leistungen bleiben getrennt. Ungültige Meldezeilen werden gewarnt und ausgelassen.
Die Austrittsfelder werden aus dem Workbook übernommen. Tests decken Wechsel im Monat und
Austrittsdatum ab. Der August-Abgleich DM-41 ist noch offen.

Arbeitszeit zeigt Auftragsnummer und Indexkind, einschliesslich SA. Der alte `extend-master`-
Befehl samt Skript ist entfernt; die Felder gehören bereits zum neuen Workbook.
