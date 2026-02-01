import pytest
import numpy as np
import os
import json
from core.events import Event
from core.engine import SheratanEngine
from core.encoding import encode_event
from config import CONFIG

def test_structural_perception_consolidation():
    engine = SheratanEngine(CONFIG)
    
    # 1. Two events with identical data -> should consolidate into one state
    e1 = Event(1.0, "test", {"msg": "hello"})
    e2 = Event(2.0, "test", {"msg": "hello"})
    
    s1, r1 = engine.process_event(e1)
    w1 = s1.weight
    s2, r2 = engine.process_event(e2)
    
    assert len(engine.states) == 1
    assert s1.state_id == s2.state_id
    assert s2.weight > w1
    assert r2 > 0

def test_structural_perception_differentiation():
    engine = SheratanEngine(CONFIG)
    
    # 2. Two events with very different data -> should create two states
    # Using radically different keys/values
    e1 = Event(1.0, "test", {"a": 1})
    e2 = Event(2.0, "test", {"zebra": [99, 100, 101]})
    
    s1, r1 = engine.process_event(e1)
    s2, r2 = engine.process_event(e2)
    
    print(f"DEBUG: Sim between S1 and S2-vec: {s1.similarity(encode_event(e2))}")
    
    assert len(engine.states) == 2
    assert s1.state_id != s2.state_id

def test_determinism(tmp_path):
    # Running the same sequence twice should produce identical recordings
    from replay.recorder import Recorder
    import time
    
    def run_seq():
        engine = SheratanEngine(CONFIG)
        rec = Recorder()
        for i in range(5):
            e = Event(float(i), "test", {"i": i})
            s, r = engine.process_event(e)
            rec.record(e, r, s.state_id)
        return rec.events

    run1 = run_seq()
    run2 = run_seq()
    
    assert run1 == run2
