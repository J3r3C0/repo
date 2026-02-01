import os
import pytest
from core.engine import SheratanEngine

class MockConfig:
    WINDOW_SIZE = 1000
    WINDOW_STRIDE = 1000
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 0.95
    MAX_SEGMENT_AGE = 100
    max_active_states = 1000
    RESONANCE_LOG = "logs/test_replay_log_perm.csv"

def test_replay_consistency():
    config = MockConfig()
    os.makedirs("logs", exist_ok=True)
    if os.path.exists(config.RESONANCE_LOG):
        os.remove(config.RESONANCE_LOG)
        
    engine = SheratanEngine(config)
    events = [
        (1, 0.8, 100, 0),
        (2, 0.4, 200, 0),
        (3, 0.9, 1100, 1),
    ]
    engine.process_events(events)
    live_hash = engine.memory.get_state_hash()
    engine.shutdown()
    
    replay_config = MockConfig()
    replay_config.RESONANCE_LOG = "logs/replayed_temp_perm.csv"
    engine_r = SheratanEngine(replay_config)
    engine_r.replay_from_log(config.RESONANCE_LOG)
    replay_hash = engine_r.memory.get_state_hash()
    
    assert live_hash == replay_hash
