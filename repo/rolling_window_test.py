import numpy as np
import pytest
from core.events import create_event_buffer

def test_rolling_window_mapping():
    # window_size = 1000, window_stride = 500 (50% overlap)
    # Event at 700ms should be in:
    # Window 0: 0-1000ms
    # Window 1: 500-1500ms
    events = [(1, 1.0, 700, 0)]
    buf = create_event_buffer(events, window_size=1000, window_stride=500)
    
    assert len(buf) == 2
    windows = buf["window"].tolist()
    assert 0 in windows
    assert 1 in windows

    # Event at 400ms should only be in Window 0
    events_low = [(1, 1.0, 400, 0)]
    buf_low = create_event_buffer(events_low, window_size=1000, window_stride=500)
    assert len(buf_low) == 1
    assert buf_low[0]["window"] == 0

    # Event at 1200ms should be in:
    # Window 1: 500-1500ms
    # Window 2: 1000-2000ms
    events_mid = [(1, 1.0, 1200, 0)]
    buf_mid = create_event_buffer(events_mid, window_size=1000, window_stride=500)
    assert len(buf_mid) == 2
    windows_mid = buf_mid["window"].tolist()
    assert 1 in windows_mid
    assert 2 in windows_mid

if __name__ == "__main__":
    test_rolling_window_mapping()
    print("Rolling window tests passed!")
