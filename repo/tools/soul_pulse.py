# repo/tools/soul_pulse.py
from __future__ import annotations
import os
import sys
import json
import time
import random
import importlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional, Tuple

REPORT_DIR = Path("build/reports")
OUT_JSON = REPORT_DIR / "soul_pulse_report.json"

DEFAULT_MAX_ITERS = 50
DEFAULT_IDLE_ITERS = 10
DEFAULT_MAX_SECONDS = 60
DEFAULT_SEED = 1337

@dataclass
class Probe:
    name: str
    kind: str  # "import" | "call" | "api"
    weight: int = 1
    requires_env: Optional[List[str]] = None

    def runnable(self) -> Tuple[bool, str]:
        if not self.requires_env:
            return True, ""
        missing = [k for k in self.requires_env if not os.environ.get(k)]
        if missing:
            return False, f"missing_env={missing}"
        return True, ""

def build_probes() -> List[Tuple[Probe, Callable[[], Any]]]:
    probes: List[Tuple[Probe, Callable[[], Any]]] = []
    
    # 1) Core Semantic Imports
    semantic_modules = [
        "core.policy", "core.trace", "core.attestation", 
        "core.anomaly_detector", "core.self_diagnostics",
        "core.state_machine", "core.policy_engine"
    ]
    
    for mod in semantic_modules:
        probes.append((
            Probe(name=f"import.{mod}", kind="import", weight=2),
            lambda m=mod: importlib.import_module(m)
        ))

    # 2) Call Probes (Self-Diagnostics / Health)
    def _call_health_smoke():
        try:
            from core.health import get_system_health
            return get_system_health()
        except:
            return "health_call_failed"

    probes.append((Probe(name="call.health.deep", kind="call", weight=1), _call_health_smoke))

    return probes

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    print("[SOUL_PULSE] Starting stochastic semantic activation...")

    seed = int(os.environ.get("SOUL_PULSE_SEED", str(DEFAULT_SEED)))
    max_iters = int(os.environ.get("SOUL_PULSE_MAX_ITERS", str(DEFAULT_MAX_ITERS)))
    idle_limit = int(os.environ.get("SOUL_PULSE_IDLE_ITERS", str(DEFAULT_IDLE_ITERS)))
    
    rng = random.Random(seed)
    probes = build_probes()
    
    seen_modules = set(sys.modules.keys())
    runs = []
    new_modules_global = []
    idle_streak = 0

    for i in range(max_iters):
        probe, fn = rng.choice(probes)
        runnable, _ = probe.runnable()
        if not runnable: continue

        before = set(sys.modules.keys())
        t0 = time.time()
        ok = True
        err = None
        
        try:
            fn()
        except Exception as e:
            ok = False
            err = str(e)

        dur_ms = int((time.time() - t0) * 1000)
        after = set(sys.modules.keys())
        new_mods = sorted(after - before)

        if new_mods:
            idle_streak = 0
            for m in new_mods:
                if m not in seen_modules:
                    new_modules_global.append(m)
                    seen_modules.add(m)
        else:
            idle_streak += 1

        runs.append({
            "iter": i,
            "probe": probe.name,
            "ok": ok,
            "duration_ms": dur_ms,
            "new_modules": len(new_mods)
        })

        if idle_streak >= idle_limit:
            break

    report = {
        "iters_ran": len(runs),
        "new_modules_total": len(new_modules_global),
        "runs": runs
    }
    
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[SOUL_PULSE] COMPLETED: {len(runs)} iters, {len(new_modules_global)} new modules activated.")
    print(f"[SOUL_PULSE] Report at {OUT_JSON}")

if __name__ == "__main__":
    main()
