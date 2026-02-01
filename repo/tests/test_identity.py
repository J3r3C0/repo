import pytest
import numpy as np
from core.memory import init_memory
from core.identity import select_relevant_states

def test_identity_filtering():
    memory = init_memory(3)
    memory[0] = (0, 0.8, 1.0, 1.0, 100) # Signifikant, Frisch
    memory[1] = (1, 0.1, 1.0, 1.0, 100) # Unbedeutend (Filtered by threshold)
    memory[2] = (2, 0.9, 1.0, 1.0, 80)  # Signifikant, aber Alt (Filtered by age)
    
    current_cycle = 100
    config = {
        "min_value": 0.5,
        "max_age": 10,
        "top_k": 5
    }
    
    selected = select_relevant_states(memory, current_cycle, config)
    
    assert len(selected) == 1
    assert selected[0]["state_id"] == 0
    assert selected[0]["value"] == pytest.approx(0.8)

def test_identity_top_k():
    memory = init_memory(5)
    for i in range(5):
        # Alle signifikant und frisch, unterschiedliche Werte
        memory[i] = (i, 0.1 * (i+1), 1.0, 1.0, 100)
    
    current_cycle = 100
    config = {
        "min_value": 0.0,
        "max_age": 10,
        "top_k": 2
    }
    
    selected = select_relevant_states(memory, current_cycle, config)
    
    assert len(selected) == 2
    # Top 2 sollten state_id 4 (0.5) und 3 (0.4) sein
    assert selected[0]["state_id"] == 4
    assert selected[1]["state_id"] == 3
