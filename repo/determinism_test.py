import numpy as np
import sys
import os
import shutil
from pathlib import Path

# Ensure core and gpu modules are importable
sys.path.insert(0, os.getcwd())

from core.engine import SheratanEngine

class MockConfig:
    WINDOW_SIZE = 10
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 0.9
    max_active_states = 100

def run_simulation(log_path):
    # Clear previous logs
    if Path(log_path).exists():
        os.remove(log_path)
        
    engine = SheratanEngine(MockConfig)
    
    # Sample events: (id, value, ts, ch)
    events = [
        (1, 0.5, 10, 1),
        (2, 0.5, 12, 1),
        (3, 1.0, 20, 2),
    ]
    
    # Run 3 cycles with same events
    results = []
    for i in range(3):
        res = engine.process_events(events)
        results.append(res)
        
    states = engine.get_state_snapshot()
    engine.shutdown()
    
    # Read resonance log
    with open(log_path, "r") as f:
        log_content = f.read()
        
    return results, states, log_content

def test_determinism():
    print("Testing system determinism...")
    
    log1 = "logs/determinism_1.csv"
    log2 = "logs/determinism_2.csv"
    
    # Set log paths in observe.py or environment if needed, 
    # for now we'll just run twice and compare the default log if we can't redirect easily.
    # Actually, let's just compare two consecutive runs results.
    
    r1, s1, l1 = run_simulation("logs/resonance_log.csv")
    # Move log
    if os.path.exists("logs/resonance_log.csv"):
        shutil.move("logs/resonance_log.csv", log1)
        
    r2, s2, l2 = run_simulation("logs/resonance_log.csv")
    if os.path.exists("logs/resonance_log.csv"):
        shutil.move("logs/resonance_log.csv", log2)

    # Compare results
    assert str(r1) == str(r2), "Cycle results differ between runs"
    assert len(s1) == len(s2), "State counts differ between runs"
    for i in range(len(s1)):
        assert s1[i]["segment"] == s2[i]["segment"]
        assert np.isclose(s1[i]["value"], s2[i]["value"])
    
    # Compare logs
    with open(log1, "r") as f1, open(log2, "r") as f2:
        assert f1.read() == f2.read(), "Resonance logs differ between runs"
        
    print("[OK] Determinism verification passed.")

if __name__ == "__main__":
    try:
        test_determinism()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
