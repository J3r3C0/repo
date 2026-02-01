# v_execute.ps1 - Das Verdammungs-Modul
$root = "C:/projectroot"
$outputDir = "$root/v_mesh_output"
$archiveDir = "$root/v_mesh_archive"

if (!(Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir }
if (!(Test-Path $archiveDir)) { New-Item -ItemType Directory -Path $archiveDir }

Write-Host "Verdammungs-Modul aktiv. Warte auf Befehle in $outputDir..." -ForegroundColor Magenta

while ($true) {
    $files = Get-ChildItem -Path $outputDir -Filter *.json
    foreach ($file in $files) {
        try {
            $json = Get-Content $file.FullName | ConvertFrom-Json
            Write-Host "[!] Führe Job aus: $($json.v_metadata.job_id)" -ForegroundColor Cyan
            
            # Ausführungsebene
            if ($json.execution_layer.action -eq "FILE_SYSTEM_OPERATION") {
                $params = $json.execution_layer.params
                if ($params.mode -eq "write") {
                    $targetPath = $params.target_path -replace "C:/projektroot", $root
                    $targetDir = [System.IO.Path]::GetDirectoryName($targetPath)
                    if (!(Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force }
                    $params.payload_content | Out-File -FilePath $targetPath -Force
                    Write-Host "[OK] Datei geschrieben: $($targetPath)" -ForegroundColor Green
                }
            }

            # Archivierung zur Vermeidung von Doppel-Ausführung
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            Move-Item -Path $file.FullName -Destination "$archiveDir/executed_$timestamp.json"
        }
        catch {
            Write-Host "[ERR] Fehler bei Job-Verarbeitung: $_" -ForegroundColor Red
        }
    }
    Start-Sleep -Seconds 1
}
