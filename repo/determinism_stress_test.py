import os
import numpy as np
from core.engine import SheratanEngine

class MockConfig:
    WINDOW_SIZE = 1000
    WINDOW_STRIDE = 500
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 0.95
    MAX_SEGMENT_AGE = 100
    max_active_states = 1000
    RESONANCE_LOG = "logs/stress_log.csv"

def run_once(events):
    if os.path.exists(MockConfig.RESONANCE_LOG):
        os.remove(MockConfig.RESONANCE_LOG)
    engine = SheratanEngine(MockConfig())
    engine.process_events(events)
    h = engine.memory.get_state_hash()
    engine.shutdown()
    return h

def test_determinism_stress():
    events = [
        (i, np.random.rand(), i * 10, i % 5) for i in range(500)
    ]
    
    print("Running determinism stress test (100 runs)...")
    hashes = []
    for i in range(100):
        h = run_once(events)
        hashes.append(h)
        if i % 20 == 0:
            print(f"Run {i}...")

    unique_hashes = set(hashes)
    print(f"Found {len(unique_hashes)} unique hash(es) out of 100 runs.")
    
    assert len(unique_hashes) == 1
    print("Determinism Stress Test PASSED: 100% hash match.")

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    test_determinism_stress()
