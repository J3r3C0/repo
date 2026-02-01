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
    # Segment 2 should still be ranked #1 because value is higher
    assert int(selected_p[0]["segment"]) == 2
    assert int(selected_p[1]["segment"]) == 1

def test_identity_v3_ranking_age():
    # Both above threshold, but one is older
    states = [
        {"segment": 1, "value": 0.6, "weight": 1.0, "last_seen": 5}, # Older
        {"segment": 2, "value": 0.55, "weight": 1.0, "last_seen": 10}, # Younger but slightly lower value
    ]
    
    # Cycle is 10
    # Score for seg 1: 0.6 * (1.0 - 0.05) = 0.57
    # Score for seg 2: 0.55 * (1.0 - 0.00) = 0.55
    # Wait, ranking_score uses 0.01 per cycle.
    # Seg 1 age = 5 -> score = 0.6 * 0.95 = 0.57
    # Seg 2 age = 0 -> score = 0.55 * 1.0 = 0.55
    # Seg 1 still wins.
    
    selected = select_top_states(states, threshold=0.1, current_cycle=10)
    assert int(selected[0]["segment"]) == 1
    
    # If cycle is 20:
    # Seg 1 age = 15 -> score = 0.6 * 0.85 = 0.51
    # Seg 2 age = 10 -> score = 0.55 * 0.90 = 0.495
    # Seg 1 still wins.
    
    # If cycle is 50:
    # Seg 1 age = 45 -> score = 0.6 * 0.55 = 0.33
    # Seg 2 age = 40 -> score = 0.55 * 0.60 = 0.33
    # Tie.
    
    # Let's make one VERY old
    states_old = [
        {"segment": 1, "value": 0.9, "weight": 1.0, "last_seen": 0}, # Very old (age 100)
        {"segment": 2, "value": 0.2, "weight": 1.0, "last_seen": 100}, # New
    ]
    selected_old = select_top_states(states_old, threshold=0.1, current_cycle=100)
    # Seg 1 score: 0.9 * (1.0 - 1.0) = 0.0
    # Seg 2 score: 0.2 * 1.0 = 0.2
    assert int(selected_old[0]["segment"]) == 2

if __name__ == "__main__":
    test_identity_v3_persistence()
    test_identity_v3_ranking_age()
    print("Identity v3 tests passed!")
