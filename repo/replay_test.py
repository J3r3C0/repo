import numpy as np
import sys
import os
from pathlib import Path

# Ensure core and gpu modules are importable
sys.path.insert(0, os.getcwd())

from core.engine import SheratanEngine

class MockConfig:
    WINDOW_SIZE = 10
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 0.9
    max_active_states = 100
    MAX_SEGMENT_AGE = 50

def test_replay_cycle():
    print("Testing Replay Cycle Determinism...")
    log_path = "logs/replay_source.csv"
    
    # 1. First Run (Live)
    engine_live = SheratanEngine(MockConfig)
    events = [(1, 0.7, 100, 1), (2, 0.8, 100, 1)]
    engine_live.process_events(events)
    engine_live.process_events(events)
    live_states = engine_live.get_state_snapshot()
    engine_live.shutdown()
    
    # 2. Second Run (Replay)
    engine_replay = SheratanEngine(MockConfig)
    reconstructed = engine_replay.replay_from_log("logs/resonance_log.csv")
    replay_states = engine_replay.get_state_snapshot()
    engine_replay.shutdown()
    
    print(f"Reconstructed {reconstructed} logic cycles.")
    
    # 3. Compare
    assert len(live_states) == len(replay_states), f"State count mismatch: {len(live_states)} vs {len(replay_states)}"
    
    for ls in live_states:
        match = next((rs for rs in replay_states if rs["segment"] == ls["segment"]), None)
        assert match is not None, f"Segment {ls['segment']} missing in replay"
        assert np.isclose(match["value"], ls["value"]), f"Value mismatch for segment {ls['segment']}"
        assert match["last_seen"] == ls["last_seen"], f"Cycle mismatch for segment {ls['segment']}"

    print("[OK] Replay verification passed.")

if __name__ == "__main__":
    try:
        test_replay_cycle()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
