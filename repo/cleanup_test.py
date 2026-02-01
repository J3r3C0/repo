import numpy as np
import sys
import os

# Ensure core and gpu modules are importable
sys.path.insert(0, os.getcwd())

from core.engine import SheratanEngine

class MockConfig:
    WINDOW_SIZE = 10
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 1.0 # No decay to make testing easier
    max_active_states = 100
    MAX_SEGMENT_AGE = 5 # Small age for quick testing

def test_cleanup():
    print("Testing Segment Cleanup...")
    engine = SheratanEngine(MockConfig)
    
    # 1. Ingest event for Segment X at Cycle 0
    channel = 1
    ts = 100
    window_size = 10
    expected_seg = (np.uint64(channel) << 32) | np.uint64(ts // window_size)
    
    engine.process_events([(1, 1.0, ts, channel)]) # Cycle 0
    assert expected_seg in engine.memory.states
    
    # 2. Process cycles until Segment X is stale
    # process_events increments cycle_count and increments cleanup every 10 cycles (or we trigger it manually)
    # Actually process_events does it every 10. Let's force it or run 10.
    
    for i in range(1, 10):
        engine.process_events([]) # Empty cycles 
        
    # Segment 1 was seen at Cycle 0. Current Cycle is 10. Max Age is 5.
    # It should be gone after Cycle 10's cleanup.
    
    assert 1 not in engine.memory.states, "Stale segment was not cleaned up"
    print("[OK] Cleanup verification passed.")

if __name__ == "__main__":
    try:
        test_cleanup()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
