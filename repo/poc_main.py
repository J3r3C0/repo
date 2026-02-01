import csv
import os
import numpy as np
from core.events import create_event_buffer, Event
from core.engine import SheratanEngine
from scenario import generate_meaningful_scenario
from config import CONFIG

def run_research_skeleton(num_cycles=100):
    print(f"--- Sheratan Research Skeleton (Phase 8 - B4 Alignment) ---")
    cfg = CONFIG
    
    # 1. Initialize Deterministic Engine
    engine = SheratanEngine(cfg)
    
    # 2. Scenario Simulation
    scenario = generate_meaningful_scenario(num_cycles=num_cycles, num_channels=20)

    log_file = "research_run.csv"
    with open(log_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cycle", "state_id", "value"])
        writer.writeheader()

        for i in range(num_cycles):
            events = scenario[i]
            
            # Aggregate resonance for cycle status print
            cycle_resonance = 0.0
            
            # Process discrete events through the perception core
            for raw_event in events:
                # Wrap raw event data into an Event object for the engine
                event = Event(data=raw_event, t=float(raw_event["t"]))
                
                state, resonance = engine.process_event(event)
                cycle_resonance += resonance
                
                # Log if it reflects significant perception
                if resonance > cfg.resonance_threshold:
                    writer.writerow({
                        "cycle": i, 
                        "state_id": state.state_id[:8], 
                        "value": float(resonance)
                    })

            if i % 20 == 0 or i == num_cycles - 1:
                print(f"Cycle {i:03d} | Net Resonance: {cycle_resonance:.4f} | Active States: {len(engine.states)}")

    print(f"\n[DONE] Research run saved to {log_file}")
    print(f"Next: python tools/visualizer.py {log_file}")

if __name__ == "__main__":
    run_research_skeleton(100)
