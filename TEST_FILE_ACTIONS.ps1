$jobId = [guid]::NewGuid().ToString()
$missionId = [guid]::NewGuid().ToString()
$taskId = [guid]::NewGuid().ToString()

# 1. Create Mission
$mission = @{
    id = $missionId
    title = "Test File Actions"
    description = "Verifying write_file and append_file"
}
$mResp = Invoke-RestMethod -Uri "http://localhost:8001/api/missions" -Method Post -Body ($mission | ConvertTo-Json) -ContentType "application/json"
Write-Host "Created Mission: $($mResp.id)"

# 2. Create Task
$task = @{
    id = $taskId
    name = "Append Test"
    kind = "action_phase"
}
$tResp = Invoke-RestMethod -Uri "http://localhost:8001/api/missions/$($mResp.id)/tasks" -Method Post -Body ($task | ConvertTo-Json) -ContentType "application/json"
Write-Host "Created Task: $($tResp.id)"

# 3. Create initial file
$writeJob = @{
    id = [guid]::NewGuid().ToString()
    payload = @{
        kind = "write_file"
        params = @{
            path = "DEBUG_FILE_ACTION.txt"
            content = "Initial Line.`n"
        }
        provenance = @{ source_zone = "narrative" }
    }
}
$j1Resp = Invoke-RestMethod -Uri "http://localhost:8001/api/tasks/$($tResp.id)/jobs" -Method Post -Body ($writeJob | ConvertTo-Json) -ContentType "application/json"
Write-Host "Created Job 1: $($j1Resp.id)"

# 4. Wait a bit
Start-Sleep -Seconds 5

# 5. Append to file
$appendJob = @{
    id = [guid]::NewGuid().ToString()
    payload = @{
        kind = "append_file"
        params = @{
            path = "DEBUG_FILE_ACTION.txt"
            content = "Appended Line.`n"
        }
        provenance = @{ source_zone = "narrative" }
    }
}
$j2Resp = Invoke-RestMethod -Uri "http://localhost:8001/api/tasks/$($tResp.id)/jobs" -Method Post -Body ($appendJob | ConvertTo-Json) -ContentType "application/json"
Write-Host "Created Job 2: $($j2Resp.id)"

Write-Host "Jobs submitted successfully. Check DEBUG_FILE_ACTION.txt in a few seconds."
