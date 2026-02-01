import numpy as np
import sys
import os

# Ensure core and gpu modules are importable
sys.path.insert(0, os.getcwd())

from core.engine import SheratanEngine

class MockConfig:
    WINDOW_SIZE = 10
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 1.0 # No decay for boundary test prediction
    MAX_SEGMENT_AGE = 1000
    max_active_states = 5 

def test_memory_boundaries():
    print(f"Testing memory boundaries (limit={MockConfig.max_active_states})...")
    engine = SheratanEngine(MockConfig)
    
    # 1. Ingest 10 different segments
    # Each segment with different value to check pruning priority
    events = []
    for i in range(10):
        # (id, value, ts, ch)
        events.append((i, float(i+1)*0.1, 100 + i*10, 1))
    
    # Process events in one batch (or multiple)
    # Pruning happens every 10 cycles, so we need to run 10 cycles or force it
    
    # We'll run 11 cycles (0 to 10)
    # Cleanup runs at cycle 0 and cycle 10
    for i in range(11):
        # reuse some segments or send empty ones
        ev = [events[i % 10]]
        engine.process_events(ev)
        
    states = engine.get_state_snapshot()
    print(f"Active states after 10 cycles: {len(states)}")
    
    # Verify limit
    assert len(states) <= MockConfig.max_active_states, f"Memory exceeded limit: {len(states)}"
    
    # Verify that we kept the HIGHEST values
    # Segments were 1..10 with values 0.1..1.0
    # Expected kept values: 0.6, 0.7, 0.8, 0.9, 1.0 (if limit is 5)
    values = [s["value"] for s in states]
    print(f"Kept values: {sorted(values)}")
    assert min(values) >= 0.6, f"Pruning logic fail: kept low value {min(values)}"
    
    print("[OK] Boundary verification passed.")

if __name__ == "__main__":
    try:
        test_memory_boundaries()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
