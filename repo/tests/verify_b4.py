import numpy as np
import hashlib
from core.encoding import encode_event
from core.states import State
from core.resonance import compute_resonance
from core.identity import identity_modifier
from core.engine import SheratanEngine

class MockEvent:
    def __init__(self, data):
        self.data = data

def test_b4_alignment():
    print("--- Running B4 Alignment Verification ---")
    
    # 1. Test Deterministic Encoding
    data = {"key": "value"}
    event = MockEvent(data)
    vec1 = encode_event(event)
    vec2 = encode_event(event)
    
    assert np.allclose(vec1, vec2), "Encoding must be deterministic"
    assert vec1.shape == (16,), f"Vector dimension should be 16, got {vec1.shape}"
    assert np.all(vec1 >= 0) and np.all(vec1 <= 1.0), "Vector values must be normalized [0, 1]"
    print("[OK] Deterministic Encoding")

    # 2. Test State Update & Hash
    state = State(vec1)
    original_id = state.state_id
    state.update(vec1)
    assert state.weight == 1.1, f"Weight should be 1.1 after one update, got {state.weight}"
    assert state.state_id != original_id, "State ID should change after vector update (since it is based on vector bytes)"
    print("[OK] State Update & Hashing")

    # 3. Test Similarity
    sim = state.similarity(vec1)
    assert 0.99 <= sim <= 1.01, f"Similarity with itself should be ~1.0, got {sim}"
    print("[OK] Similarity")

    # 4. Test Resonance & Identity
    res = compute_resonance(1.0, 1.0, 1.0)
    assert res == 1.0, f"Resonance calculation error, got {res}"
    
    state.weight = 4.0
    assert identity_modifier(state) == 1.2, "Identity modifier for weight > 3.0 should be 1.2"
    
    state.weight = 0.5
    assert identity_modifier(state) == 0.8, "Identity modifier for weight < 1.0 should be 0.8"
    print("[OK] Resonance & Identity")

    # 5. Engine Integration
    class MockConfig:
        max_active_states = 5
        vector_dim = 16
        
    engine = SheratanEngine(MockConfig())
    s1, r1 = engine.process_event(event)
    s2, r2 = engine.process_event(event)
    
    assert len(engine.states) == 1, "Should have 1 state for identical events"
    assert s2.weight == 1.1, "State weight should have increased"
    print("[OK] Engine Integration")

    print("\n[SUCCESS] B4 Core Logic Verified.")

if __name__ == "__main__":
    try:
        test_b4_alignment()
    except AssertionError as e:
        print(f"[FAIL] {e}")
    except Exception as e:
        print(f"[ERROR] {e}")
