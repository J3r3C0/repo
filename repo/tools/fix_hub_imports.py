import os

def fix_imports():
    hub_dir = r"c:\neuer ordner für allgemein github pulls\sheratan-core\hub"
    files = [f for f in os.listdir(hub_dir) if f.endswith('.py')]
    relocated_mods = [f[:-3] for f in files]
    # Also add standard modules that might be nested or have different naming
    relocated_mods.extend(['scoring', 'mcts_light', 'candidate_schema', 'determinism', 'database', 'models', 'storage'])
    relocated_mods = list(set(relocated_mods))

    for f in files:
        path = os.path.join(hub_dir, f)
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        new_content = content
        for mod in relocated_mods:
            # Replace common import patterns
            new_content = new_content.replace(f"from core import {mod}", f"from hub import {mod}")
            new_content = new_content.replace(f"import core.{mod}", f"import hub.{mod}")
            new_content = new_content.replace(f"from core.{mod}", f"from hub.{mod}")
        
        # Special case: some files might import from core.observability.decision_trace
        # if decision_trace is now in hub/decision_trace.py
        new_content = new_content.replace("from core.observability.decision_trace", "from hub.decision_trace")
        
        if new_content != content:
            print(f"Fixed imports in {f}")
            with open(path, 'w', encoding='utf-8') as file:
                file.write(new_content)

if __name__ == "__main__":
    fix_imports()
