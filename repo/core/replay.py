import csv
import os
from core.memory import init_memory
from config import defaults

def replay_resonance_log(csv_path, initial_memory=None, run_id=None):
    """
    Replays a resonance log (cycle, state_id, value) from a CSV file.
    Updates the provided memory (or initializes a new one) CPU-side.
    """
    if run_id:
        print(f"[REPLAY] Loading Run: {run_id}")

    # Simple discovery of max state_id if memory is not provided
    max_id = 0
    rows = []
    
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            max_id = max(max_id, int(row["state_id"]))
            
    if initial_memory is None:
        memory = init_memory(max_id + 1)
        # Default weights/decay for PoC from config
        memory["weight"] = 1.0
        memory["decay"] = defaults.CONFIG.state_decay
    else:
        memory = initial_memory

    last_cycle = -1
    for row in rows:
        cycle = int(row["cycle"])
        state_id = int(row["state_id"])
        value = float(row["value"])
        
        # Apply decay for skipped cycles/new cycles
        if cycle != last_cycle:
            if last_cycle != -1:
                memory["aggregated_value"] *= memory["decay"]
            last_cycle = cycle

        # 1. Update State (using threshold from config)
        if value > defaults.CONFIG.resonance_threshold:
            memory[state_id]["aggregated_value"] += value * memory[state_id]["weight"]
        
        # 2. Update Persistence
        memory[state_id]["last_seen"] = cycle
        
    return memory
