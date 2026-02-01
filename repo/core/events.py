import numpy as np

from dataclasses import dataclass
from typing import Any

@dataclass
class Event:
    data: Any
    t: float = 0.0
    source: str = "system"

# Sheratan Phase 2: Structured Array Event Format
# Maxwell/Maxwell-compatible SoA layout
EVENT_DTYPE = np.dtype([
    ("id", np.uint32),
    ("value", np.float32),
    ("timestamp", np.uint32),
    ("channel", np.uint16),
    ("window", np.uint32),
    ("segment", np.uint64), # (channel << 32) | window
])

def create_event_buffer(events, window_size: int = 1000, window_stride: int = None):
    """
    Converts list of raw events to a structured numpy array with rolling support.
    
    events: list of tuples (id, value, timestamp, channel)
    window_size: granularity of resonance windows (ms)
    window_stride: overlap stride (ms). If None, defaults to window_size (no overlap).
    """
    if window_stride is None:
        window_stride = window_size
        
    processed = []
    for eid, val, ts, ch in events:
        # Determine all windows this event belongs to
        # k such that: k*stride <= ts < k*stride + window_size
        
        # First possible window k: k*stride <= ts  => k_max = ts // stride
        # Last possible window k: k*stride + window_size > ts => k*stride > ts - window_size
        k_min = max(0, (ts - window_size + window_stride) // window_stride)
        k_max = ts // window_stride
        
        for k in range(k_min, k_max + 1):
            window = k
            segment = (np.uint64(ch) << 32) | np.uint64(window)
            processed.append((eid, val, ts, ch, window, segment))

    return np.array(processed, dtype=EVENT_DTYPE)

