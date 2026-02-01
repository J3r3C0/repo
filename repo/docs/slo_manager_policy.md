# SLOManager Policy

## Goal
Provide a clear, safe mode switch for the `SLOManager` that can be used in production without risking accidental shutdowns or data loss.

## Modes (environment variable `SLO_MODE`)
| Mode | Description | Effect on System |
|------|-------------|-------------------|
| `off` | SLOManager disabled completely. | No metrics collected, no impact on dispatch. |
| `observe` | **Default**. Collects metrics, writes warning events, **does not** influence job dispatch or queue depth. | Safe for all environments. |
| `enforce` | Enables active throttling/gating based on SLO thresholds. | May reduce dispatch rate, activate back‑pressure gates. |

## Activation Rules
- The mode is read from `os.getenv("SLO_MODE", "observe")` at startup.
- `enforce` is only allowed when an additional safety flag is present:
  ```
  SLO_ENFORCE_TOKEN=1   # optional extra guard
  ```
- If `SLO_MODE=enforce` **and** the token is missing, the system falls back to `observe` and logs a warning.

## What `enforce` May Do (strictly limited)
- **Dispatch‑Rate Limiting** – caps the number of jobs dispatched per minute.
- **Queue‑Depth Gate** – pauses dispatch when the pending job queue exceeds `RobustnessConfig.MAX_QUEUE_DEPTH`.

## What `enforce` Must NOT Do
- Delete or modify existing job records.
- Change the status of a job retroactively.
- Terminate the Core API or other services.

## Implementation Sketch (Python)
```python
import os
from core.slo_manager import SLOManager

mode = os.getenv("SLO_MODE", "observe").lower()
enforce_token = os.getenv("SLO_ENFORCE_TOKEN")

if mode == "enforce" and enforce_token != "1":
    print("[SLO] enforce mode requested but token missing – falling back to observe")
    mode = "observe"

slo_manager = SLOManager(mode=mode)
```

## Documentation Note
> **SLOManager** is instantiated in the FastAPI lifespan. In `observe` mode it only records metrics; in `enforce` mode it may call `dispatcher.apply_backpressure()` based on configured thresholds.
