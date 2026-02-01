import os
import shutil
import numpy as np
from core.engine import SheratanEngine

class MockConfig:
    WINDOW_SIZE = 1000
    WINDOW_STRIDE = 1000
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 0.95
    MAX_SEGMENT_AGE = 100
    max_active_states = 1000
    RESONANCE_LOG = "logs/test_replay_log.csv"

def test_replay_consistency():
    # 1. Setup
    config = MockConfig()
    if os.path.exists(config.RESONANCE_LOG):
        os.remove(config.RESONANCE_LOG)
        
    engine = SheratanEngine(config)
    
    # 2. Run Live session
    # (id, value, ts, ch)
    events = [
        (1, 0.8, 100, 0),
        (2, 0.4, 200, 0),
        (3, 0.9, 1100, 1),
    ]
    engine.process_events(events)
    live_hash = engine.memory.get_state_hash()
    live_states = engine.get_state_snapshot()
    engine.shutdown()
    
    # 3. Replay session
    replay_config = MockConfig()
    # Use a DIFFERENT log path for the replay engine so it doesn't overwrite
    replay_config.RESONANCE_LOG = "logs/replayed_temp.csv"
    engine_r = SheratanEngine(replay_config)
    
    engine_r.replay_from_log(config.RESONANCE_LOG)
    replay_hash = engine_r.memory.get_state_hash()
    
    print(f"Live Hash:   {live_hash}")
    print(f"Replay Hash: {replay_hash}")
    
    assert live_hash == replay_hash
    print("Replay consistency verified!")

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    test_replay_consistency()
