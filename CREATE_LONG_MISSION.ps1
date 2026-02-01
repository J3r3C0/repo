param (
    [string]$Title = "New Autonomous Mission",
    [string]$Description = "Analyze the codebase and provide a summary of the core logic.",
    [string]$CoreUrl = "http://localhost:8001"
)

$ErrorActionPreference = "Stop"

try {
    # 1. Create Mission
    Write-Host "--- Step 1: Creating Mission ---" -ForegroundColor Cyan
    $missionBody = @{
        title = $Title
        description = $Description
        status = "active"
    }
    $mission = Invoke-RestMethod -Method Post -Uri "$CoreUrl/api/missions" -Body ($missionBody | ConvertTo-Json) -ContentType "application/json"
    $missionId = $mission.id
    Write-Host "Mission created: $missionId" -ForegroundColor Green

    # 2. Create agent_plan Task
    Write-Host "`n--- Step 2: Creating Planning Task ---" -ForegroundColor Cyan
    $taskId = "content_test_$(Get-Date -UFormat %s)"
    $taskBody = @{
        name = "Autonomous Planning"
        kind = "agent_plan"
        params = @{
            user_prompt = $Description
            chain_id = $taskId
        }
    }
    $task = Invoke-RestMethod -Method Post -Uri "$CoreUrl/api/missions/$missionId/tasks" -Body ($taskBody | ConvertTo-Json) -ContentType "application/json"
    $taskId = $task.id
    Write-Host "Task created: $taskId" -ForegroundColor Green

    # 3. Create initial agent_plan Job
    Write-Host "`n--- Step 3: Enqueueing Initial Job ---" -ForegroundColor Cyan
    $jobPayload = @{
        payload = @{
            kind = "agent_plan"
            params = @{
                user_request = $Description
                iteration = 1
            }
            task = @{
                kind = "agent_plan"
                params = @{
                    user_prompt = $Description
                }
            }
        }
    }
    $job = Invoke-RestMethod -Method Post -Uri "$CoreUrl/api/tasks/$taskId/jobs" -Body ($jobPayload | ConvertTo-Json) -ContentType "application/json"
    Write-Host "Job enqueued: $($job.id)" -ForegroundColor Green

    Write-Host "`nMission successfully started! 🚀" -ForegroundColor Yellow
    Write-Host "Monitor it at: $CoreUrl/api/missions/$missionId"
} catch {
    Write-Host "`nFailed to create mission: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $resp = $reader.ReadToEnd()
        Write-Host "Server response: $resp" -ForegroundColor Red
    }
}
