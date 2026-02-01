# watch_mesh.ps1 - V-Mesh Single-Tasking Protocol
$root = "C:/projectroot"
$inbox = "$root/v_mesh_inbox/trigger.json"
$archive = "$root/v_mesh_archive/"

if (!(Test-Path $archive)) { New-Item -ItemType Directory -Path $archive }

Write-Host "V-Mesh Auditor-Mode aktiv. Warte auf trigger.json..." -ForegroundColor Cyan

while ($true) {
    if (Test-Path $inbox) {
        Write-Host "[!] Neuer Job erkannt. Lade Inhalt..." -ForegroundColor Yellow
        $content = Get-Content $inbox -Raw
        
        # Hier wird der Inhalt für mich ausgegeben
        Write-Host "--- INHALT START ---"
        $content
        Write-Host "--- INHALT ENDE ---"
        
        # Verschiebe in den Archiv-Ordner, um den Loop zu stoppen (WICHTIG!)
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Move-Item -Path $inbox -Destination "$archive/job_$timestamp.json"
        
        Write-Host "[OK] Job archiviert. System im Leerlauf, bis die Lösung eintrifft." -ForegroundColor Green
        break # Stoppt den Loop nach einem Job, um 1:3:9 zu verhindern
    }
    Start-Sleep -Seconds 2
}
