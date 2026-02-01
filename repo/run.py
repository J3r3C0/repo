import time
import random
from core.events import Event
from core.engine import SheratanEngine
from config import CONFIG
from replay.recorder import Recorder
from viz.timeline import plot_timeline
from viz.resonance_plot import plot_resonance
from viz.state_space import plot_state_space

def run_research():
    print(f"--- Sheratan Substantial Core Execution (Phase 7) ---")
    
    engine = SheratanEngine(CONFIG)
    rec = Recorder()
    
    # 1. Generate interesting event sequence
    # We use some varying data to see state consolidation
    sources = ["user", "system", "network"]
    data_templates = [
        {"type": "login", "success": True},
        {"type": "error", "code": 404},
        {"type": "message", "body": "hello"},
        {"type": "message", "body": "repeat"}, # Persistent pattern
        {"type": "message", "body": "repeat"},
        {"type": "heartbeat"},
    ]

    print(f"Processing 50 cycles...")
    for i in range(50):
        # Create patterned data
        if i % 3 == 0:
            data = {"type": "message", "body": "repeat"} # Pattern
        else:
            data = random.choice(data_templates)
            data["v"] = random.random() # Add variance
            
        e = Event(time.time(), random.choice(sources), data)
        state, res = engine.process_event(e)
        rec.record(e, res, state.state_id)
        
        if i % 10 == 0:
            print(f"  Step {i:03d} | Active States: {len(engine.states)} | Latest Res: {res:.4f}")

    # 2. Output & Viz
    rec.save("run_recording.json")
    
    print("\nGenerating Visualizations...")
    plot_timeline(rec.events)
    plot_resonance(rec.events, threshold=CONFIG.resonance_threshold)
    plot_state_space(engine)
    
    print("\n[DONE] Research Skeleton finalized.")

if __name__ == "__main__":
    run_research()
