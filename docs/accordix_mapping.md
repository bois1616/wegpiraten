# Accordix-Vokabular: Spalten-Mapping Stammdaten nach Meldedatei

Zuordnung der Spalten in `masterdata_client` (Datei `wegpiraten_datenbank.xlsx`,
Blatt "Klienten") zu den Feldern der Accordix-Meldedatei
(`templates/Import-Accordix_ambulant_Excel-Format_V1.0_DE.xlsx`, Blatt "Ambulant").

Die Spaltennamen in `masterdata_client` entsprechen jeweils dem gleichnamigen
Feld in der SQLite-Tabelle `clients`.

## Aus den Stammdaten befüllte Felder

| masterdata_client (Excel/DB) | Accordix-Feld (technisch) | Accordix-Spalte | Accordix-Bezeichnung | Werte |
|---|---|---|---|---|
| `last_name` | LastName | A | Nachname | Freitext |
| `first_name` | FirstName | B | Vorname | Freitext |
| `social_security_number` | SocialInsuranceNumber | C | AHV-Nummer | `756.XXXX.XXXX.XX`, darf leer sein |
| `date_of_birth` | DateOfBirth | D | Geburtsdatum | TT.MM.JJJJ (Pflicht) |
| `gender` | Gender | E | Geschlecht | `m` / `w` / `d` (Pflicht) |
| `uma_umf` | UmaUmfRecognition | F | UMA/UMF | `Ja` / `Nein` / `Unbekannt` (Pflicht) |
| `spoken_language` | SpokenLanguage | G | Hauptsprache | `DE` / `FR`, nur bei bilingualen LE |
| `canton_of_residence` | CantonOfResidence | I | Wohnkanton | Kantonskürzel oder `Ausland` (Pflicht) |
| `residence_legal_guardian` | ResidenceLegalGuardian | J | Wohnort (Sorgeberechtigte) | PLZ und/oder Gemeinde, nur wenn Wohnkanton BE |
| `service_type` nach `service_types.code` | ServiceTypeName | L | Leistungsart | via Mapping (siehe unten) |
| `allocation` | Allocation | M | Zuweisung | `Einvernehmlich über Sozialdienst` / `KESB (zusammen mit Gericht)` / `Jugendanwaltschaft` |
| `start_date` | StartDate | Q | Eintrittsdatum | TT.MM.JJJJ |
| `end_date` | EndDate | S | Austrittsdatum | TT.MM.JJJJ, nur wenn Ende <= Meldemonat (Achtung: Bewilligungsende ungleich Austritt, siehe Warnung im Report) |
| `is_consultative_adolescent_psychiatric_care` | IsConsultativeAdolescentPsychiatricCare | N | IBF: Konsiliarische jugendpsychiatrische Versorgung | `true`/`false`, nur für Leistungsart IBF |
| `number_of_care_days_per_week` | NumberOfCareDaysPerWeek | O | SPT: Anzahl Betreuungstage pro Woche | 3-5, nur für Leistungsart SPT |
| `is_leaving_reason_planned` | IsLeavingReasonPlanned | T | war der Austritt geplant? | `true`/`false`, nur bei Austritt |
| `leaving_reason` | LeavingReason | U | Austrittsgrund | gemäss Werteliste, nur wenn Austritt nicht geplant |
| `custom_leaving_reason` | CustomLeavingReason | V | Anderer Austrittsgrund | Freitext, nur wenn leaving_reason = "Anderer" |
| `after_leave_situation` | AfterLeaveSituation | W | Situation nach Austritt | gemäss Werteliste |
| `custom_after_leave_situation` | CustomAfterLeaveSituation | X | Andere Situation nach Austritt | Freitext, nur wenn after_leave_situation = "andere" |
| `remarks` | Remarks | Z | Bemerkungen | Freitext |

Die Dropdowns in den neuen Spalten sind mit dem Blatt "Wertelisten" in der
Masterdatei verknüpft (benannte Bereiche `accordix_*`).

## Leistungsarten-Mapping (intern nach Accordix)

| `service_types.code` | ServiceTypeName (Accordix) |
|---|---|
| `SPF` | Sozialpädagogische Familienbegleitung (SPF) |
| `UWB  (Ausübung Gruppe)` | Besuchsrecht - Begleitung bei Ausübung Besuchsrecht (Gruppensetting) |
| `UWB (Übergabe Gruppe)` | Besuchsrecht - Begleitung bei Kinderübergabe (Gruppensetting) |
| `UWB (Begleitung Individuell)` | Besuchsrecht (individuelle Begleitung) |
| `DAF L` | DAF: Begleitung von Pflegeverhältnissen Langzeitunterbringung |

Nicht zugeordnet (werden nicht gemeldet, Zeile wird mit Warnung übersprungen):
`PRIVAT`, `SONST`, `Jugendcoaching`, `Abklärung`, `med./therap. Bericht`.

Definition der Wertelisten und des Mappings: `src/shared_modules/accordix.py`.

## Offizielle JSON-Spezifikationen

Die vollständigen JSON-Formatvorlagen (ambulant und stationär) liegen lokal unter:
- `docs/Import-Accordix_ambulant_JSON-Format_V1.0.json`
- `docs/Import-Accordix_stationär_JSON-Format_V1.0.json`
- `docs/Import-Accordix_ambulant_JSON-Beispiel_V1.0.json`
- `docs/Import-Accordix_stationär_JSON-Beispiel_V1.0.json`

Quelle: <https://www.kja.dij.be.ch/de/start/foerder--und-schutzleistungen/kantonale-datenerfassung/Datenbank_Accordix/MoeglichkeitenDatenmeldung.html>
