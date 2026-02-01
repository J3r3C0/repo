import pytest
from config import defaults
from core.cycle import run_cycle
from core.events import create_event_buffer
from core.memory import init_memory
import io
from contextlib import redirect_stdout

def test_mode_analysis_verbose(monkeypatch):
    monkeypatch.setattr(defaults, "SHERATAN_MODE", "analysis")
    
    events = create_event_buffer([(1, 0.8, 0, 1)])
    memory = init_memory(1)
    memory["weight"] = 1.0
    memory["decay"] = 1.0
    
    f = io.StringIO()
    with redirect_stdout(f):
        run_cycle(events, memory, current_cycle=1)
    
    output = f.getvalue()
    assert "[CYCLE 1] Resonance" in output
    assert "[CYCLE 1] Memory Updated" in output

def test_mode_agent_silent(monkeypatch):
    monkeypatch.setattr(defaults, "SHERATAN_MODE", "agent")
    
    events = create_event_buffer([(1, 0.8, 0, 1)])
    memory = init_memory(1)
    
    f = io.StringIO()
    with redirect_stdout(f):
        run_cycle(events, memory, current_cycle=1)
    
    output = f.getvalue()
    assert "[CYCLE 1] Resonance" not in output
