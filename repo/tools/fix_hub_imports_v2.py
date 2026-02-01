import os
import re

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
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            new_content = content
            
            # Pattern 1: from core import a, b, c
            # This is tricky because some might stay in core (config, engine, identity, etc.)
            def replace_from_core(match):
                prefix = match.group(1)
                names = [n.strip() for n in match.group(2).split(',')]
                
                core_names = []
                hub_names = []
                
                for name in names:
                    clean_name = name.split('as')[0].strip()
                    if clean_name in relocated:
                        hub_names.append(name)
                    else:
                        core_names.append(name)
                
                res = []
                if core_names:
                    res.append(f"from core import {', '.join(core_names)}")
                if hub_names:
                    res.append(f"from hub import {', '.join(hub_names)}")
                
                return "\n".join(res)

            new_content = re.sub(r"from core import (.*)", replace_from_core, new_content)

            # Pattern 2: from core.module import name
            for mod in relocated:
                new_content = new_content.replace(f"from core.{mod}", f"from hub.{mod}")
                new_content = new_content.replace(f"import core.{mod}", f"import hub.{mod}")

            if new_content != content:
                print(f"Repaired: {os.path.relpath(path, hub_root)}")
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(new_content)

if __name__ == "__main__":
    fix_imports()
