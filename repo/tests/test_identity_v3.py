import numpy as np
import pytest
from core.identity import select_top_states

def test_identity_v3_persistence():
    # Mock memory states
    states = [
        {"segment": 1, "value": 0.4, "weight": 1.0, "last_seen": 10}, # Below threshold (0.5)
        {"segment": 2, "value": 0.6, "weight": 1.0, "last_seen": 10}, # Above threshold
    ]
    
    # Run without persistence
    selected = select_top_states(states, threshold=0.5, current_cycle=10)
    assert len(selected) == 1
    assert int(selected[0]["segment"]) == 2
    
    # Run WITH persistence (segment 1 was previously selected)
    selected_p = select_top_states(
        states, 
        threshold=0.5, 
        current_cycle=10, 
        last_selected_segments={1}
    )
    assert len(selected_p) == 2
    assert int(selected_p[0]["segment"]) == 2
    assert int(selected_p[1]["segment"]) == 1

def test_identity_v3_ranking_age():
    states_old = [
        {"segment": 1, "value": 0.9, "weight": 1.0, "last_seen": 0}, # Very old (age 100)
        {"segment": 2, "value": 0.2, "weight": 1.0, "last_seen": 100}, # New
    ]
    selected_old = select_top_states(states_old, threshold=0.1, current_cycle=100)
    # Seg 1 score: 0.9 * (1.0 - 1.0) = 0.0
    # Seg 2 score: 0.2 * 1.0 = 0.2
    assert int(selected_old[0]["segment"]) == 2 or len(selected_old) == 2
    if len(selected_old) > 0:
        assert int(selected_old[0]["segment"]) == 2
