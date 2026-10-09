# Umsetzungslog: Umstellung auf Kinder, Aufträge und Betreuungen

Begleitet das [Backlog](backlog_umstellung_datenmodell.md). Muster wie
[umsetzungslog.md](../../umsetzungslog.md): neueste Einträge zuerst, ein Abschnitt je Tag.

## Übergabe

Diesen Abschnitt liest jedes Modell zuerst und überschreibt ihn am Ende jeder Sitzung. Er ist der
einzige Ort, der den aktuellen Stand trägt; die Einträge darunter sind die Begründung dafür.

- **Branch:** `feature/datamodel-v2` (lokal, von `e960512`, noch nicht gepusht); Rückweg: Tag `pre-datamodel-v2` (lokal)
- **Zuletzt erledigt:** Plan erstellt (Backlog, dieses Log)
- **In Arbeit:** nichts
- **Frist:** Ende Oktober 2026 neues Workbook bereit, Unklarheiten und Datenfehler behoben (DM-02, DM-04–06, DM-60)
- **Nächster Schritt:** DM-02 und DM-04 `[Opus]`, parallel DM-10 `[Haiku]`; DM-00 wartet auf Freigabe
- **Wartet auf Stephan:** DM-00 (Merge, Tag, Push), DM-01 (AGENTS.md-Ausnahme), Fachfragen aus DM-02
- **Entwürfe ohne Opus-Review:** keine
- **Prüfstand:** `nox` zuletzt nicht gelaufen (keine Codeänderung)

## Eintragsvorlage

```markdown
- **DM-nn Kurztitel** `[Modell]` (Status: erledigt | Teil erledigt | Entwurf, Opus-Review offen | abgebrochen):
  Was geändert wurde, mit Dateien. Entscheidungen und warum. Prüfung: Befehl und Ergebnis
  (z.B. `nox`: 0 Fehler, `pytest`: 14/14). Offen: was der Nächste wissen muss.
```

Regeln:

- Das Modell steht in jedem Eintrag, damit sichtbar ist, welche Stufe eine Entscheidung getroffen hat.
- Spezifikationen aus `[Opus]`-Aufgaben stehen vollständig im Eintrag oder als eigene Datei unter
  `docs/dev/`, auf die der Eintrag verweist. Eine Spezifikation, die nur im Chat stand, gibt es nicht.
- Prüfergebnisse werden zusammengefasst (Anzahl bestanden, Namen der Fehlschläge), keine
  Rohausgaben.
- Keine Personendaten im Log. Aufträge und Kinder mit Nummer nennen, Namen nur, wo das Konzept
  sie schon als Beispiel führt.

## 2026-10-09

- **Alte Stammdatei eingefroren** `[Opus]` (Status: erledigt): Stephan hat `wegpiraten_datenbank.xlsx`
  aus der Kundenablage verschoben; Wegpiraten bearbeitet sie nicht mehr. Quelle für den finalen
  Build ist damit `sandbox/wegpiraten_datenbank.xlsx` (Stand 09.10.), sie ändert sich nicht mehr.
  Nächste Stammdatenänderung Ende Oktober, bis dahin müssen Unklarheiten und Datenfehler behoben
  sein. Backlog: Abschnitt «Termin» ergänzt, DM-60 nach P0 mit Frist, DM-04 auf die eingefrorene
  Quelle angepasst. Offen: mit welchen Programmen der Oktober-Lauf fakturiert.

- **Plan für die finale Umstellung** `[Opus]` (Status: erledigt): Backlog
  `docs/dev/backlog_umstellung_datenmodell.md` mit 36 Aufgaben in sechs Phasen plus P1/P2 und
  Modellzuordnung angelegt, dieses Log eingerichtet. Grundlage: Konzept, Datenmodell und
  Umstellungs-Runbook (Stand 25.09.2026), Kunde hat das Modell bestätigt.
  Befunde, die in den Plan eingeflossen sind:
  (1) `main` (`50ffaa5`) liegt 16 Commits hinter `fix/sa-sentinel-client`; der Produktivstand ist
  der Branch, nicht `main`.
  (2) Zwei Workbooks mit getrenntem Inhalt: `sandbox/wegpiraten_datenbank.xlsx` (alte Struktur,
  laufend gepflegt, Stand 09.10.) und `sandbox/wegpiraten_datenbank_neu.xlsx` (neue Struktur mit
  Handarbeit, Stand 30.09.). Die Sandbox-Skripte lesen noch `wegpiraten_datenbank(1).xlsx`, die
  nicht mehr existiert (DM-04).
  (3) `service_data` wird bei jedem Bogen-Import neu befüllt (heute nur Juni 2026, 243 Zeilen);
  die eigentliche Altlast sind die archivierten Bögen mit `C…` in G8 (DM-22), nicht die Datenbank.
  (4) 19 Module unter `src/` lesen `clients` oder `client_id`; die Rechnungsvorlage braucht
  keine Änderung, wenn die Kontextfelder ihre Namen behalten (DM-30).
  (5) Die Umstellung widerspricht AGENTS.md «Betriebsstabilität» (keine destruktiven
  Schemaänderungen, alte Importformate bleiben); Ausnahme braucht Stephans Freigabe (DM-01).
  Lokal angelegt: Tag `pre-datamodel-v2` auf `e960512`, Branch `feature/datamodel-v2` davon, Plan dort committet,
  nicht gepusht. Prüfung: keine Codeänderung, `nox` nicht gelaufen.
  Offen: Freigabe DM-00 und DM-01 durch Stephan.
