#!/usr/bin/env python3
"""
verify_ports.py
Warns if runtime env ports differ from documented defaults.
Exit code:
  0 = ok / only warnings allowed
  2 = hard mismatch if --strict
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass

@dataclass(frozen=True)
class PortDef:
    env: str
    default: int
    label: str

PORTS = [
    PortDef("SHERATAN_CORE_PORT",        8001, "Core API (FastAPI)"),
    PortDef("SHERATAN_WEBRELAY_PORT",    3000, "WebRelay (HTTP)"),
    PortDef("SHERATAN_DASHBOARD_PORT",   3001, "Dashboard (static)"),
    PortDef("SHERATAN_MESH_BROKER_PORT", 9000, "Mesh Broker"),
    PortDef("SHERATAN_MESH_HOST_A_PORT", 8081, "Mesh Host A"),
    PortDef("SHERATAN_MESH_HOST_B_PORT", 8082, "Mesh Host B"),
    PortDef("SHERATAN_JOURNAL_SYNC_PORT", 8100, "Journal Sync API"),
]

def _parse_int(v: str | None) -> int | None:
    if v is None or v.strip() == "":
        return None
    try:
        return int(v.strip())
    except ValueError:
        return None

def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    print("[verify_ports] Checking port env vars vs documented defaults...\n")

    mismatches = 0
    invalid = 0

    for p in PORTS:
        raw = os.getenv(p.env)
        val = _parse_int(raw)
        if raw is None:
            print(f"  - {p.label}: {p.env} not set → using default {p.default}")
            continue
        if val is None:
            invalid += 1
            print(f"  ! {p.label}: {p.env}='{raw}' is not an int")
            continue
        if val != p.default:
            mismatches += 1
            print(f"  ! {p.label}: {p.env}={val} (doc default {p.default})")
        else:
            print(f"  ✓ {p.label}: {p.env}={val}")

    print("\n[verify_ports] Summary:")
    print(f"  mismatches: {mismatches}")
    print(f"  invalid:    {invalid}")

    if strict and (mismatches > 0 or invalid > 0):
        print("\n[verify_ports] STRICT mode → failing.")
        return 2

    # non-strict: just warn
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
