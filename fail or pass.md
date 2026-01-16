Für den **abschließenden “Anfang”** (also: *jetzt wirklich stabil produktiv starten und nicht wieder in Drift/Chaos landen*) fehlt typischerweise nicht mehr viel Code – sondern **ein sauberer Release-/Runbook-Block + ein letzter End-to-End Gate-Test**.

Hier ist die **kompakte Abschluss-Checkliste** (in sinnvoller Reihenfolge):

## 1) Release-Anker setzen

* **Version/Tag** (neben Track-Tags):

  * `baseline-v2.9` *(oder `v2.9.0` wenn SemVer sinn mach)*
* **Changelog/Release Note**: 10 Zeilen reichen (A1–A4, B1–B3, PoW scripts, DB migrations).

**Warum:** Damit du später nie wieder “welcher Stand war stabil?” suchen musst.

## 2) Startpfad vereinheitlichen

Es muss **eine** “goldene” Startmethode geben (nicht 3).

* Entweder:

  * `python -u core/main.py`
* oder:

  * `uvicorn core.main:app ...`

Aber nicht beides im Alltag.

**Plus:** Port-Kollision prophylaktisch:

* Script `scripts/stop_ports.ps1` (8001/3001/8787/8788) oder zumindest doc snippet.

## 3) One-shot Smoke “Production Acceptance”

Du hast schon Smoke-Skripte – jetzt brauchst du **ein einziges** “I’m safe”-Script, das alles abprüft:

**`scripts/acceptance.ps1`** (Wrapper)

* A1 Token rotation sanity (optional)
* A2 attestation signal sanity
* A3 policy warn/quarantine sanity
* A4 identity signature sanity
* B1 backpressure counters non-negative + gates respond
* B2 idempotency (call verify)
* B3 integrity (call verify)
* `/api/system/metrics` muss **legacy + new keys** liefern

Am Ende: **PASS/FAIL + exit code**

## 4) Operational Defaults fixieren

Ein `.env.example` / Config Block mit “production defaults”, die du *nie* wieder raten willst:

* `MAX_QUEUE_DEPTH`
* `MAX_INFLIGHT`
* `LEASE_TIMEOUT`
* idempotency TTL (wenn ihr B2.1 später macht)
* audit/alerts Pfade
* health state start (PAUSED/OPERATIONAL) klar definiert

## 5) Log Hygiene & Rotation (klein, aber wichtig)

Wenn ihr 24/7 lauft:

* `hub_security_audit.jsonl` / `alerts.jsonl` / decision_trace → **rotieren** oder “tail window”
* Diagnose-Bundle Script (habt ihr teils) als Standard

## 6) Final E2E “Real Life” Test (5 Minuten)

Kein Unit-Test, sondern echte Sequenz:

1. Core starten (golden path)
2. Worker/Node heartbeat mit Signatur (A4)
3. bewusst drift senden → A2+ A3 WARN
4. spoof flip-flop → A2 + A3 QUARANTINE
5. Job Create mit `idempotency_key` (B2)
6. Result tamper test (B3) → 403 + audit + metric

Wenn das durchläuft, ist das **der abschließende Anfang**.

---

### Was ich als *nächstes Track* empfehlen würde

Wenn du „ready“ bist für den nächsten großen Stabilitätshebel:

**B4: Retention/Eviction + Replay determinism**

* TTL für idempotency/result cache
* deterministisches Replay (gleicher Input → gleicher Hash)
* verhindert DB-Wachstum + macht Debugging “wissenschaftlich”

---

 **eine konkrete `scripts/acceptance.ps1` Struktur** (Wrapper, exit codes, Reihenfolge, minimal output), die eure vorhandenen `verify_b2`/`verify_b3` direkt einhängt.




Alles klar — hier ist ein **konkretes Skeleton für `scripts/acceptance.ps1`**, als “ein Kommando = PASS/FAIL”. Es hängt eure vorhandenen Verify-Skripte ein, prüft Ports, Core-Health/Metrics und gibt einen harten Exit-Code zurück.

> Annahmen: Repo-Root ist `C:\sauber_main`, Skripte liegen in `.\scripts\`, Core läuft auf `http://localhost:8001`.

```powershell
# scripts/acceptance.ps1
# Sheratan Production Acceptance - One Shot PASS/FAIL
# Exit codes:
#   0 = PASS
#   1 = FAIL (generic)
#   2 = FAIL (core not reachable)
#   3 = FAIL (verify scripts failed)
#   4 = FAIL (metrics mismatch)

param(
  [string]$BaseUrl = "http://localhost:8001",
  [switch]$SkipPortCheck,
  [switch]$SkipB2,
  [switch]$SkipB3
)

$ErrorActionPreference = "Stop"

function Write-Section($t) {
  Write-Host ""
  Write-Host "=== $t ==="
}

function Fail($msg, [int]$code = 1) {
  Write-Host ""
  Write-Host "[FAIL] $msg"
  exit $code
}

function Pass($msg) {
  Write-Host "[PASS] $msg"
}

function Try-InvokeJson($url) {
  try {
    return Invoke-RestMethod -Method GET -Uri $url -TimeoutSec 5
  } catch {
    return $null
  }
}

function Test-PortInUse($port) {
  $hits = netstat -ano | Select-String -Pattern "[:.]$port\s"
  return ($hits -ne $null)
}

# --- A) Preflight ---
Write-Section "A) Preflight"

$root = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $root
Pass "Repo root: $root"

if (-not $SkipPortCheck) {
  Write-Section "A1) Port checks"
  if (Test-PortInUse 8001) {
    Pass "Port 8001 appears in use (Core may already be running)."
  } else {
    Write-Host "[WARN] Port 8001 not in use. If Core isn't running, the next step will fail."
  }
}

# --- B) Core reachability ---
Write-Section "B) Core Reachability"

$metrics = Try-InvokeJson "$BaseUrl/api/system/metrics"
if ($null -eq $metrics) {
  Fail "Core not reachable at $BaseUrl (try starting core first)" 2
}
Pass "Core reachable: $BaseUrl"

# --- C) Metrics contract ---
Write-Section "C) Metrics Contract"

# Required legacy keys (UI compatibility)
$legacyKeys = @("queueLength", "errorRate", "uptime")
# Required new keys (B1/B2/B3)
$newKeys = @("queue_depth", "inflight", "ready_to_dispatch", "error_rate")

foreach ($k in $legacyKeys) {
  if (-not ($metrics.PSObject.Properties.Name -contains $k)) {
    Fail "Missing legacy metrics key: $k" 4
  }
}
Pass "Legacy metrics keys present"

foreach ($k in $newKeys) {
  if (-not ($metrics.PSObject.Properties.Name -contains $k)) {
    Fail "Missing new metrics key: $k" 4
  }
}
Pass "New metrics keys present (B1)"

# Optional: B2/B3 counters, if you expose them in /api/system/metrics
$optionalKeys = @("idempotent_hits_1m", "idempotent_collisions_1m", "integrity_fail_1m")
foreach ($k in $optionalKeys) {
  if ($metrics.PSObject.Properties.Name -contains $k) {
    Pass "Optional metric present: $k"
  } else {
    Write-Host "[WARN] Optional metric not present in /api/system/metrics: $k (ok if tracked elsewhere)"
  }
}

# --- D) Run verify scripts ---
Write-Section "D) Verification Scripts"

if (-not $SkipB2) {
  $b2 = Join-Path $root "scripts\verify_b2_idempotency.ps1"
  if (-not (Test-Path $b2)) { Fail "Missing script: $b2" 3 }
  Write-Host "Running: $b2"
  & $b2
  if ($LASTEXITCODE -ne 0) { Fail "verify_b2_idempotency.ps1 failed (exit $LASTEXITCODE)" 3 }
  Pass "B2 verify passed"
} else {
  Write-Host "[SKIP] B2 verify"
}

if (-not $SkipB3) {
  $b3 = Join-Path $root "scripts\verify_b3_result_integrity.ps1"
  if (-not (Test-Path $b3)) { Fail "Missing script: $b3" 3 }
  Write-Host "Running: $b3"
  & $b3
  if ($LASTEXITCODE -ne 0) { Fail "verify_b3_result_integrity.ps1 failed (exit $LASTEXITCODE)" 3 }
  Pass "B3 verify passed"
} else {
  Write-Host "[SKIP] B3 verify"
}

# --- E) Final pass ---
Write-Section "E) Final"

Pass "PRODUCTION ACCEPTANCE: ALL CHECKS GREEN"
exit 0
```

## Nutzung

Von Repo-Root:

```powershell
.\scripts\acceptance.ps1
```

Wenn Core nicht läuft, erst starten (euer golden path), dann nochmal.

Optionen:

```powershell
.\scripts\acceptance.ps1 -SkipPortCheck
.\scripts\acceptance.ps1 -SkipB2
.\scripts\acceptance.ps1 -SkipB3
.\scripts\acceptance.ps1 -BaseUrl "http://127.0.0.1:8001"
```

---

ich gebe dir als nächsten Mini-Schritt noch:

* `scripts/start_core.ps1` (golden path + Port kill optional)
* `scripts/stop_ports.ps1` (8001/8787/8788/3001 sauber freiräumen)
* und ein kurzes `docs/ACCEPTANCE.md` (wie man’s im Alltag nutzt)




```powershell
# scripts/stop_ports.ps1
# Kills processes bound to the given TCP ports (Windows).
param(
  [int[]]$Ports = @(8001, 8787, 8788, 3001),
  [switch]$WhatIf
)

$ErrorActionPreference = "SilentlyContinue"

function Get-PidsForPort([int]$port) {
  $lines = netstat -ano | Select-String -Pattern "[:.]$port\s"
  if (-not $lines) { return @() }

  $pids = @()
  foreach ($l in $lines) {
    $parts = ($l.ToString() -split "\s+") | Where-Object { $_ -ne "" }
    # typical: TCP 0.0.0.0:8001 ... LISTENING 12345
    $pid = $parts[-1]
    if ($pid -match "^\d+$") { $pids += [int]$pid }
  }
  return $pids | Sort-Object -Unique
}

Write-Host "=== stop_ports.ps1 ==="
foreach ($p in $Ports) {
  $pids = Get-PidsForPort $p
  if ($pids.Count -eq 0) {
    Write-Host "[OK] Port $p: no listeners found"
    continue
  }

  foreach ($pid in $pids) {
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    $name = if ($proc) { $proc.ProcessName } else { "unknown" }
    if ($WhatIf) {
      Write-Host "[WHATIF] Would kill PID $pid ($name) on port $p"
    } else {
      Write-Host "[KILL] Port $p -> PID $pid ($name)"
      Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
  }
}
Write-Host "Done."
```

```powershell
# scripts/start_core.ps1
# Golden path starter for Sheratan Core v2 (Windows PowerShell).
param(
  [string]$Host = "0.0.0.0",
  [int]$Port = 8001,
  [switch]$KillPort,
  [switch]$UseUvicorn,          # default is python -u core/main.py
  [string]$BaseDir = ""         # optional explicit repo root
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  if ($BaseDir -and (Test-Path $BaseDir)) { return (Resolve-Path $BaseDir).Path }
  return (Resolve-Path "$PSScriptRoot\..").Path
}

$root = Resolve-RepoRoot
Set-Location $root

Write-Host "=== start_core.ps1 ==="
Write-Host "Repo: $root"
Write-Host "Host: $Host  Port: $Port"

if ($KillPort) {
  $stop = Join-Path $root "scripts\stop_ports.ps1"
  if (Test-Path $stop) {
    & $stop -Ports @($Port)
  } else {
    Write-Host "[WARN] scripts/stop_ports.ps1 not found, using netstat fallback"
    $hits = netstat -ano | Select-String -Pattern "[:.]$Port\s"
    if ($hits) { Write-Host "[WARN] Port $Port appears in use; consider freeing it manually." }
  }
}

if ($UseUvicorn) {
  # Uvicorn path
  $env:PYTHONPATH = $root
  Write-Host "[RUN] python -m uvicorn core.main:app --host $Host --port $Port"
  python -m uvicorn core.main:app --host $Host --port $Port
} else {
  # Direct run path (recommended if your core/main.py already boots uvicorn internally)
  Write-Host "[RUN] python -u core/main.py"
  python -u core/main.py
}
```

````markdown
<!-- docs/ACCEPTANCE.md -->
# Sheratan Production Acceptance

This repository includes a one-command acceptance gate that proves the baseline is healthy.

## Prerequisites
- Core runs on `http://localhost:8001` (default)
- PowerShell execution policy allows running local scripts (if needed):
  - `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Golden Path: Start Core
Recommended:
```powershell
.\scripts\start_core.ps1 -KillPort
````

Alternative (explicit uvicorn):

```powershell
.\scripts\start_core.ps1 -UseUvicorn -KillPort
```

## Stop Ports (Emergency / Cleanup)

```powershell
.\scripts\stop_ports.ps1
```

Preview (no killing):

```powershell
.\scripts\stop_ports.ps1 -WhatIf
```

## Acceptance Gate (PASS/FAIL)

Run the acceptance wrapper:

```powershell
.\scripts\acceptance.ps1
```

Options:

```powershell
.\scripts\acceptance.ps1 -SkipPortCheck
.\scripts\acceptance.ps1 -SkipB2
.\scripts\acceptance.ps1 -SkipB3
.\scripts\acceptance.ps1 -BaseUrl "http://127.0.0.1:8001"
```

### Exit Codes

* `0` = PASS
* `2` = Core not reachable
* `3` = Verify scripts failed
* `4` = Metrics contract mismatch

## What "PASS" proves

* Core reachable and responding
* Metrics contract provides legacy + new keys
* Track B2 idempotency verification is green
* Track B3 result integrity (tamper detect + soft migrate) verification is green

```

Wenn du willst, sag mir nur kurz, ob dein Repo den Ordner `docs/` schon nutzt oder `data/docs/` o.ä. — ansonsten passt `docs/ACCEPTANCE.md` als Standard.
::contentReference[oaicite:0]{index=0}
```
