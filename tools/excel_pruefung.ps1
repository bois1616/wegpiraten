# Prüft die Arbeitsmappe in echtem Excel und schreibt einen Bericht daneben.
#
# Hintergrund: gebaut und getestet wird unter Linux mit LibreOffice, und
# LibreOffice ist an mehreren Stellen nachsichtiger als Excel. Zwei Fehler sind
# genau durch diese Lücke gefallen: benannte Bereiche mit führendem "=" (Excel
# verwirft sie kommentarlos, LibreOffice nimmt sie) und INDEX auf eine leere
# Zelle (Excel liefert 0, LibreOffice leer). Dieses Skript fragt Excel selbst.
#
# Aufruf in der Windows-Instanz:
#   powershell -ExecutionPolicy Bypass -File excel_pruefung.ps1 -Datei "...\wegpiraten_datenbank.xlsx"

param(
    [Parameter(Mandatory = $true)][string]$Datei,
    [string]$Bericht = ""
)

$ErrorActionPreference = "Stop"
$Datei = (Resolve-Path -LiteralPath $Datei).ProviderPath
if ($Bericht -eq "") { $Bericht = [IO.Path]::ChangeExtension($Datei, ".pruefung.txt") }
$zeilen = New-Object System.Collections.Generic.List[string]
function Sag($t) { $zeilen.Add($t); Write-Host $t }

# Nur neue Reparaturprotokolle betrachten; fremde Protokolle bleiben erhalten.
$tmp = [IO.Path]::GetTempPath()
$vorher = Get-Date

Sag "Datei:  $Datei"
Sag "Excel:  gestartet $(Get-Date -Format 'dd.MM.yyyy HH:mm')"
Sag ""

$excel = $null
$wb = $null
try {
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$excel.AskToUpdateLinks = $false
$wb = $excel.Workbooks.Open($Datei, 0, $true)   # ReadOnly, keine Verknüpfungen aktualisieren
if ($null -eq $wb) { throw "Excel hat keine Arbeitsmappe zurueckgegeben." }
Sag ("Geoeffnet: " + $wb.FullName)
Sag ("Arbeitsblaetter: " + $wb.Worksheets.Count)
if ($wb.Names.Count -eq 0) { throw "Keine benannten Bereiche: falsche oder unvollstaendige Stammdatei." }
# Ein fehlendes Blatt oder ein Zeichencodierungsproblem muss den Lauf abbrechen.
foreach ($name in @("Prüfungen", "Fehlerliste", "Aufträge", "Betreuungen", "Kinder", "Zuordnung MA", "Berichte", "Prüfkatalog")) {
    $null = $wb.Worksheets.Item($name)
}

# --- 1. Hat Excel repariert?
$logs = Get-ChildItem $tmp -Filter "error*.xml" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $vorher }
if ($logs) {
    Sag "REPARATUR: Excel hat beim Öffnen etwas entfernt."
    foreach ($l in $logs) { Sag ("  " + $l.FullName); Sag (Get-Content $l.FullName -Raw) }
} else {
    Sag "Reparatur: keine. Excel hat die Datei unverändert geöffnet."
}

# --- 2. Benannte Bereiche: sind sie noch da und lösen sie auf?
Sag ""
Sag ("Benannte Bereiche: " + $wb.Names.Count)
foreach ($n in $wb.Names) {
    $wert = ""
    try { $wert = $excel.Evaluate($n.Name); if ($wert -is [System.Array]) { $wert = "$($wert.Length) Zellen" } }
    catch { $wert = "LÖST NICHT AUF" }
    if ("$wert" -match "LÖST NICHT AUF|Fehler|#") { Sag ("  PROBLEM  {0,-24} {1}" -f $n.Name, $wert) }
}

# --- 3. Alles neu rechnen und Fehlerwerte einsammeln
$excel.Application.CalculateFullRebuild()
Sag ""
$gesamt = 0
foreach ($ws in $wb.Worksheets) {
    $treffer = $null
    try { $treffer = $ws.Cells.SpecialCells(-4123, 16) } catch { }   # xlFormulas, xlErrors
    if ($treffer) {
        $gesamt += $treffer.Count
        $bsp = @()
        foreach ($z in $treffer) { if ($bsp.Count -lt 5) { $bsp += ("{0}={1}" -f $z.Address($false, $false), $z.Text) } }
        Sag ("FORMELFEHLER  {0,-20} {1,4}  {2}" -f $ws.Name, $treffer.Count, ($bsp -join "  "))
    }
}
if ($gesamt -eq 0) { Sag "Formelfehler: keine." } else { Sag "Formelfehler gesamt: $gesamt" }

# --- 4. Auswahllisten stichprobenweise: hängen sie noch an einem Namen?
Sag ""
$proben = @(
    @("Aufträge", "B4", "Leistungsart"),
    @("Aufträge", "D4", "Ansprechperson"),
    @("Betreuungen", "A4", "Auftrag-Nr"),
    @("Kinder", "H4", "Geschlecht"),
    @("Zuordnung MA", "A4", "Auftrag-Nr")
)
foreach ($p in $proben) {
    $z = $wb.Worksheets.Item($p[0]).Range($p[1])
    $formel = $z.Validation.Formula1
    if ([string]::IsNullOrWhiteSpace("$formel")) { throw ("Auswahlliste fehlt: " + $p[0] + "!" + $p[1]) }
    Sag ("Gültigkeit  {0,-16} {1,-4} {2,-16} {3}" -f $p[0], $p[1], $p[2], $formel)
}

# --- 5. Was die Mappe selbst über sich sagt
Sag ""
Sag ("Prüfungen, offene Fehler:  " + $wb.Worksheets.Item("Prüfungen").Range("B4").Text)
Sag ("Fehlerliste:               " + $wb.Worksheets.Item("Fehlerliste").Range("A2").Text)
Sag ""
Sag "Fehlerliste, die ersten 40 Zeilen:"
$fl = $wb.Worksheets.Item("Fehlerliste")
for ($r = 5; $r -lt 45; $r++) {
    $blatt = $fl.Cells.Item($r, 1).Text
    if ($blatt -eq "") { break }
    Sag ("  {0,-16} Z{1,-5} {2,-22} {3,-8} {4}" -f $blatt, $fl.Cells.Item($r, 2).Text,
         $fl.Cells.Item($r, 3).Text, $fl.Cells.Item($r, 4).Text, $fl.Cells.Item($r, 5).Text)
}

Sag ""
if ($gesamt -eq 0 -and -not $logs) {
    Sag "Automatische Pruefung abgeschlossen. Manuelle Eingabe-/Sortiertests bleiben erforderlich."
} else {
    throw "Excel-Reparatur oder Formelfehler festgestellt; Datei vor Uebergabe pruefen."
}
} catch {
    Sag ("PRUEFUNG FEHLGESCHLAGEN: " + $_.Exception.Message)
    throw
} finally {
    if ($null -ne $wb) { $wb.Close($false) }
    if ($null -ne $excel) {
        $excel.Quit()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
    }
    $zeilen | Set-Content -LiteralPath $Bericht -Encoding UTF8
    Write-Host ""
    Write-Host "Bericht geschrieben: $Bericht"
}
