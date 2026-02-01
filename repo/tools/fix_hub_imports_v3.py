import os

def fix_imports():
    hub_root = r"c:\neuer ordner für allgemein github pulls\sheratan-core\hub"
    
    relocated = [
        "storage", "models", "database", "idempotency", "result_integrity", 
        "metrics_client", "health", "state_machine", "governance", 
        "ledger_journal", "performance_baseline", "anomaly_detector", 
        "attestation", "candidate_schema", "chain_index", "chain_runner", 
        "context_updaters", "core_heartbeat", "envelope", "gateway_middleware", 
        "heartbeat_monitor", "job_chain_manager", "lcp_actions", "mcts_light", 
        "orchestrator", "replay_engine", "result_ref", "robust_parser", 
        "scoring", "sdk_client", "self_diagnostics", "template_resolver", 
        "webrelay_bridge", "webrelay_http_client", "webrelay_llm_client", 
        "why_api", "why_reader", "decision_trace", "dispatcher"
    ]

    for root, dirs, files in os.walk(hub_root):
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
            except Exception:
                continue
            
            new_lines = []
            changed = False
            for line in lines:
                if line.strip().startswith("from core import "):
                    # Extract names
                    parts = line.strip()[len("from core import "):].split(",")
                    core_n = []
                    hub_n = []
                    for p in parts:
                        p = p.strip()
                        if not p: continue
                        clean_p = p.split(" as ")[0].strip()
                        if clean_p in relocated:
                            hub_n.append(p)
                        else:
                            core_n.append(p)
                    
                    if hub_n:
                        changed = True
                        if core_n:
                            new_lines.append(f"from core import {', '.join(core_n)}\n")
                        new_lines.append(f"from hub import {', '.join(hub_n)}\n")
                    else:
                        new_lines.append(line)
                elif line.strip().startswith("import core."):
                    mod = line.strip()[len("import core."):].split()[0].split(".")[0]
                    if mod in relocated:
                        new_lines.append(line.replace("core.", "hub."))
                        changed = True
                    else:
                        new_lines.append(line)
                elif line.strip().startswith("from core."):
                    mod = line.strip()[len("from core."):].split()[0].split(".")[0]
                    if mod in relocated:
                        new_lines.append(line.replace("core.", "hub."))
                        changed = True
                    else:
                        new_lines.append(line)
                else:
                    new_line = line
                    # General replacement for inline core. references
                    for mod in relocated:
                        if f"core.{mod}" in new_line:
                            new_line = new_line.replace(f"core.{mod}", f"hub.{mod}")
                            changed = True
                    new_lines.append(new_line)

            if changed:
                print(f"Repaired: {os.path.relpath(path, hub_root)}")
                with open(path, 'w', encoding='utf-8') as file:
                    file.writelines(new_lines)

if __name__ == "__main__":
    fix_imports()
