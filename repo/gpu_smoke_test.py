import numpy as np
import sys
import os

# Ensure core and gpu modules are importable
sys.path.insert(0, os.getcwd())

from gpu.primitives import segment_reduce_sum, HAS_GPU
if HAS_GPU:
    import cupy as cp
else:
    cp = None

def test_segment_reduce():
    print(f"Testing segment_reduce_sum (GPU available: {HAS_GPU})")
    
    # 1. Prepare data
    segments = np.array([1, 1, 2, 2, 1, 3], dtype=np.uint64)
    values = np.array([0.1, 0.2, 0.5, 0.5, 0.7, 1.0], dtype=np.float32)
    
    # Expected:
    # Seg 1: 0.1 + 0.2 + 0.7 = 1.0
    # Seg 2: 0.5 + 0.5 = 1.0
    # Seg 3: 1.0 = 1.0
    
    # 2. Run primitive
    u_segs, res_vals = segment_reduce_sum(segments, values)
    
    # 3. Verify
    print(f"Unique Segments: {u_segs}")
    print(f"Resonance Values: {res_vals}")
    
    assert len(u_segs) == 3
    assert np.allclose(res_vals[u_segs == 1], 1.0)
    assert np.allclose(res_vals[u_segs == 2], 1.0)
    assert np.allclose(res_vals[u_segs == 3], 1.0)
    
    print("[OK] segment_reduce_sum verification passed.")

if __name__ == "__main__":
    try:
        test_segment_reduce()
    except Exception as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
