import pytest
import os
import csv
import numpy as np
from core.memory import init_memory
from core.replay import replay_resonance_log

def test_replay_determinism(tmp_path):
    # 1. Create a dummy log
    log_file = tmp_path / "resonance.csv"
    with open(log_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cycle", "state_id", "value"])
        writer.writeheader()
        writer.writerow({"cycle": 1, "state_id": 0, "value": 0.8}) # Trigger
        writer.writerow({"cycle": 2, "state_id": 0, "value": 0.2}) # No Trigger
        writer.writerow({"cycle": 3, "state_id": 1, "value": 0.9}) # Trigger
        
    # 2. Replay
    # Manual expectation calculation:
    # state 0: 
    #   cycle 1: val=0.8. aggregated = (0 + 0.8*1.0) * 0.95 = 0.76. last_seen=1
    #   cycle 2: val=0.2. no trigger. aggregated = 0.76 * 0.95 = 0.722. last_seen=2
    # state 1:
    #   cycle 3: val=0.9. aggregated = (0 + 0.9*1.0) * 0.95 = 0.855. last_seen=3
    
    memory = replay_resonance_log(str(log_file))
    
    assert memory[0]["aggregated_value"] == pytest.approx(0.722)
    assert memory[0]["last_seen"] == 2
    assert memory[1]["aggregated_value"] == pytest.approx(0.855)
    assert memory[1]["last_seen"] == 3
