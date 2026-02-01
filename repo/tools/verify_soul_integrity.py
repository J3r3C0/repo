# repo/tools/verify_soul_integrity.py
import json
import sys
from pathlib import Path

MANIFEST = Path("soul.manifest.json")
REPORT = Path("build/reports/soul_verify_report.json")

def main():
    print("[SOUL_VERIFY] Starting semantic audit...")
    
    if not MANIFEST.exists():
        print(f"[SOUL_VERIFY] ERROR: Missing manifest at {MANIFEST}")
        sys.exit(1)

    try:
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[SOUL_VERIFY] ERROR: Failed to parse manifest: {e}")
        sys.exit(1)

    repo_root = Path(".")
    core_dir = repo_root / "core"
    
    missing = []
    found_count = 0
    total_required = 0

    components = m.get("soul_components", {})
    for group_name, spec in components.items():
        files = spec.get("files", [])
        required = spec.get("required", False)
        
        if required:
            total_required += len(files)
            
        for f in files:
            # Check core first (legacy behavior), then repo root
            p_core = core_dir / f
            p_root = repo_root / f
            
            if p_core.exists() or p_root.exists():
                found_count += 1
            else:
                if required:
                    missing.append(f"{group_name}/{f}")

    # Integrity Rules
    rules = m.get("rules", {})
    min_files = rules.get("min_soul_files", 0)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "ok": len(missing) == 0 and found_count >= min_files,
        "found_count": found_count,
        "missing_required": missing,
        "min_files_rule": min_files,
        "total_required": total_required
    }
    
    REPORT.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    if missing:
        print(f"[SOUL_VERIFY] FAIL: {len(missing)} required semantic files missing!")
        for m_file in missing:
            print(f"  - MISSING: {m_file}")
        sys.exit(1)

    if found_count < min_files:
        print(f"[SOUL_VERIFY] FAIL: Found {found_count} files, but manifest requires {min_files}.")
        sys.exit(1)

    print(f"[SOUL_VERIFY] PASS: {found_count} soul modules verified (Required: {total_required}).")
    print(f"[SOUL_VERIFY] Report written to {REPORT}")

if __name__ == "__main__":
    main()
