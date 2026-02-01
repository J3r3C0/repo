import pytest
import numpy as np
from core.events import create_event_buffer
from core.memory import init_memory
from core.cycle import run_cycle

def test_resonance_deterministic_aggregation():
    # Setup events
    events = create_event_buffer([
        (1, 0.1, 100, 1),
        (2, 0.2, 101, 1),
    ])
    
    memory = init_memory(1)
    memory["weight"] = 1.0
    memory["decay"] = 1.0 # No decay for simple testing
    
    # Run cycle
    # resonance = 0.1 + 0.2 = 0.3
    # 0.3 <= 0.5 (threshold) -> no update
    r = run_cycle(events, memory)
    
    assert r == pytest.approx(0.3)
    assert memory["aggregated_value"][0] == 0.0

def test_resonance_trigger_and_decay():
    events = create_event_buffer([
        (1, 0.4, 100, 1),
        (2, 0.4, 101, 1),
    ])
    
    memory = init_memory(1)
    memory["weight"] = 1.0
    memory["decay"] = 0.5
    
    # Cycle 1: resonance = 0.8
    # Aggregated = (0 + 0.8 * 1) * 0.5 = 0.4
    run_cycle(events, memory)
    assert memory["aggregated_value"][0] == pytest.approx(0.4)
    
    # Cycle 2: resonance = 0.8
    # Aggregated = (0.4 + 0.8 * 1) * 0.5 = 1.2 * 0.5 = 0.6
    run_cycle(events, memory)
    assert memory["aggregated_value"][0] == pytest.approx(0.6)

def test_empty_events():
    events = create_event_buffer([])
    memory = init_memory(1)
    memory["decay"] = 1.0
    
    r = run_cycle(events, memory)
    assert r == 0.0
    assert memory["aggregated_value"][0] == 0.0
